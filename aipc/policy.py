"""Политика безопасности: режимы ask/auto/read-only, deny-листы,
классификация рисков и серверные подтверждения (этап 1.1)."""
from __future__ import annotations

import hashlib
import os
import re
import time as _time
from fnmatch import fnmatch
from .config import config_dir, load_config

# Разделители цепочек команд: каждая часть проверяется отдельно.
_CHAIN_SPLIT = re.compile(r"&&|\|\||[;&|\n]")
# $env:NAME в PowerShell (регистр не важен).
_ENV_PWSH = re.compile(r"\$env:([A-Za-z_][\w]*)")
# Подсказки «секретного» имени переменной (общие с sysinfo.env_get).
SECRET_NAME_HINTS = ("key", "token", "secret", "password", "passwd", "pwd",
                     "auth", "credential")

# Кандидаты в пути внутри команды: C:\..., \\host\..., ~/...
_PATH_TOKEN = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\[^\s\"']+|~[\\/])[^\s\"'\],;)]*")
# Файловые глаголы целыми словами (\b): сабстринги давали ложные срабатывания
# на именах каталогов (`computing` содержит `cat`, `tools` — нет, но риск был).
_FILE_VERBS = (r"type|cat|gc|get-content|more|less|head|tail|strings|copy|cp"
               r"|xcopy|robocopy|move|mv|ren|del|erase|rm|remove-item|dir|ls"
               r"|gci|get-childitem|set-content|out-file|tee"
               r"|readalltext|readallbytes|downloadfile|downloadstring")
_FILE_HINT = re.compile(r"\b(?:" + _FILE_VERBS + r")\b|>")

# Паттерны приватных ключей/сертификатов: для opt-in safety.allow_ssh_keys
# (сравнение по нормализованной форме с прямыми слэшами).
SSH_KEY_PATTERNS = frozenset({
    "**/id_rsa", "**/id_ed25519", "**/*.pem", "**/*.pfx", "**/*.p12",
    "id_rsa", "id_ed25519", "*.pem", "*.pfx", "*.p12",
})

_ENV_REF = re.compile(r"\$env:([A-Za-z_][\w]*)|%([A-Za-z_][\w]*)%")


def is_secret_name(name: str) -> bool:
    """Имя похоже на секрет (значение в руки модели не даём)."""
    low = (name or "").strip().lower()
    return bool(low) and any(h in low for h in SECRET_NAME_HINTS)


def ssh_keys_allowed() -> bool:
    """Явный opt-in на чтение приватных ключей/сертификатов."""
    try:
        return bool(safety_cfg().get("allow_ssh_keys", False))
    except Exception:
        return False


def _expand_env(text: str) -> str:
    """Раскрыть %VAR% (expandvars), $env:VAR, ~ — чтобы обходы через
    переменные сверялись уже раскрытыми."""
    try:
        env_low = {k.lower(): v for k, v in os.environ.items()}

        def _pct(m):
            return env_low.get(m.group(1).lower(), m.group(0))

        text = re.sub(r"%([A-Za-z_][\w]*)%", _pct, text)
        text = os.path.expandvars(text)
        text = _ENV_PWSH.sub(lambda m: env_low.get(m.group(1).lower(), ""), text)
    except Exception:
        pass
    try:
        if text.startswith("~"):
            text = os.path.expanduser(text)
    except Exception:
        pass
    return text


def normalize_cmd(cmd: str) -> list[str]:
    """Команда -> список нормализованных сегментов.

    lower, разбиение цепочек && || & ; | на части СНАЧАЛА, потом в каждом
    сегменте: раскрытие переменных, снятие кавычек/^/тиков (де-обфускация),
    схлопывание пробелов. Порядок важен: иначе `;` внутри раскрытого %PATH%
    рвёт одну команду на «выполнения путей». Проверяется КАЖДЫЙ сегмент.
    """
    raw = str(cmd).lower()
    segs: list[str] = []
    for part in _CHAIN_SPLIT.split(raw):
        low = _expand_env(part)
        for ch in ("^", "`", '"', "'"):
            low = low.replace(ch, "")
        low = " ".join(low.split()).strip()
        if low:
            segs.append(low)
    return segs or [""]


def _seg_touches_files(seg: str) -> bool:
    """Сегмент работает с файлами: файловый глагол целым словом / редирект
    ИЛИ голое выполнение пути (`C:\\...\\cmd.exe` без глагола — это запуск)."""
    if _FILE_HINT.search(seg):
        return True
    return bool(re.match(r"(?:[A-Za-z]:[\\/]|\\\\|~[\\/])", seg))


def check_cmd_allowed(cmd: str) -> tuple[bool, str]:
    cfg = load_config()
    if cfg.get("mode") == "read-only":
        return False, "read-only режим: выполнение команд запрещено"
    deny = cfg.get("safety", {}).get("deny_cmd", [])
    # Ссылки на секреты окружения проверяем по СЫРОЙ команде: нормализация
    # раскрывает значения, и имя переменной уже не найти.
    raw_low = str(cmd).lower()
    for m in _ENV_REF.finditer(raw_low):
        var = m.group(1) or m.group(2) or ""
        if is_secret_name(var):
            return False, f"запрещено: чтение секрета окружения {var}"
    segs = normalize_cmd(cmd)
    for seg in segs:
        # Голый `set` / `set XXX` без `=` — дамп окружения (секреты).
        s = seg.strip()
        if s == "set" or (s.startswith("set ") and "=" not in s):
            return False, "запрещено: чтение окружения через set (секреты)"
        # `printenv` без аргументов — дамп всего окружения.
        if s == "printenv" or (s.startswith("printenv ") and
                               any(is_secret_name(w) for w in s.split()[1:])):
            return False, "запрещено: чтение окружения через printenv (секреты)"
        for d in deny:
            if str(d).lower() in seg:
                return False, f"запрещенная команда: {d}"
    # Пути внутри команды сверяем с deny_paths — но только если в сегменте есть
    # файловый глагол/редирект/чтение (.NET): голый `echo %PATH%` (в PATH есть
    # системные каталоги) блокировать нельзя — ложные срабатывания.
    # Закрывает `type ...\Login Data`, `Get-Content id_rsa` в обход fs_read.
    deny_paths = cfg.get("safety", {}).get("deny_paths", [])
    for seg in segs:
        if not _seg_touches_files(seg):
            continue
        for tok in _PATH_TOKEN.findall(seg):
            tok = tok.rstrip(".,:)")
            if not tok:
                continue
            ok, err = check_path_allowed(tok)
            if not ok:
                return False, f"запрещенный путь в команде: {err}"
        # Многокомпонентные паттерны (`**/Login Data**`, `C:\Windows\System32\*`)
        # ищем буквальным ядром — ловит пути с пробелами, которые рвут токены.
        # Однословные без пути (`id_rsa`, `*.pem`, `cookies`) пропускаем: их ловят
        # токены через basename, а подстрока дала бы ложные срабатывания.
        for pat in deny_paths:
            try:
                pnorm = os.path.normcase(str(pat)).replace("/", "\\")
                core = pnorm.replace("*", "").strip("\\")
                if len(core) >= 6 and ("\\" in core or " " in core) and core in seg:
                    return False, f"запрещенный путь в команде: {pat}"
            except Exception:
                continue
    return True, ""
def check_path_allowed(path: str) -> tuple[bool, str]:
    import os

    cfg = load_config()
    deny = cfg.get("safety", {}).get("deny_paths", [])
    keys_ok = ssh_keys_allowed()
    expanded = os.path.expanduser(path)
    norm = os.path.normcase(expanded).replace("/", "\\")
    base = os.path.normcase(os.path.basename(expanded))
    for pat in deny:
        try:
            pnorm = os.path.normcase(str(pat)).replace("/", "\\")
            # Opt-in: чтения приватных ключей/сертификатов разрешены только при
            # safety.allow_ssh_keys=true. Остальные секреты запрещены всегда.
            if keys_ok and pnorm.replace("\\", "/") in SSH_KEY_PATTERNS:
                continue
            if fnmatch(norm, pnorm):
                return False, f"запрещенный путь: {pat}"
            # Паттерны-имени (без сепаратора: *.pfx, id_rsa) сверяем с basename,
            # чтобы ловить и относительные пути. Паттерны-пути — только целиком:
            # иначе basename '*' из '...\*' заблокировал бы вообще всё.
            if "\\" not in pnorm and fnmatch(base, pnorm):
                return False, f"запрещенный путь: {pat}"
        except Exception:
            continue
    return True, ""


def is_auto() -> bool:
    return load_config().get("mode") == "auto"


def load_mode() -> str:
    return str(load_config().get("mode", "ask"))


# Tools, меняющие состояние: в read-only режиме сервер их режет до вызова.
READONLY_MUTATING = frozenset({
    "mouse_move", "mouse_click", "mouse_drag", "mouse_double_click",
    "mouse_right_click", "mouse_middle_click", "scroll",
    "type_text", "press_key", "key_down", "key_up",
    "open_app", "window_focus", "window_manage",
    "fs_write", "fs_delete", "fs_move", "fs_mkdir",
    "run_cmd", "ssh_exec", "ssh_sftp_get", "ssh_sftp_put",
    "focus_type", "ask_user",
    "browser_goto", "browser_close_tab", "browser_eval",
    "clipboard_set", "clipboard_set_image", "download_file",
})

# --- Этап 1.1: классификация инструментов по рискам ---
# read: только читает, ничего не меняет.
# interact: двигает курсор/окна/буфер, но не выполняет код и не пишет файлы.
# mutate: меняет файлы/вкладки/состояние (обратимо или нет).
# exec: выполняет произвольный код (команды, JS, SSH).
# network: уходит наружу (скачивание, отправка, поиск).
TOOL_RISK: dict[str, str] = {
    # vision / чтение
    "screen_see": "read", "screen_region": "read", "screen_burst": "read",
    "window_shot": "read", "pixel_color": "read", "mouse_position": "read",
    "screen_info": "read", "screenshot_diff": "read",
    "ui_snapshot": "read", "ui_find": "read", "assert_ui": "read",
    "windows_list": "read", "window_find": "read", "get_active_window": "read",
    "wait_for_window": "read", "wait_for_ui_element": "read",
    "wait_for_change": "read", "wait_for_process": "read",
    "video_info": "read", "clipboard_get": "read", "clipboard_get_image": "read",
    "fs_list": "read", "fs_read": "read", "fs_stat": "read", "fs_find": "read",
    "process_list": "read", "process_find": "read",
    "sys_info": "read", "net_check": "read", "env_get": "read",
    "browser_tabs": "read", "browser_active_tab": "read",
    "browser_history_search": "read",
    "logs_tail": "read", "aipc_status": "read",
    "notify_user": "read", "sleep": "read",
    # взаимодействие без выполнения кода
    "mouse_move": "interact", "mouse_click": "interact", "mouse_drag": "interact",
    "mouse_double_click": "interact", "mouse_right_click": "interact",
    "mouse_middle_click": "interact", "scroll": "interact",
    "type_text": "interact", "press_key": "interact",
    "key_down": "interact", "key_up": "interact",
    "focus_type": "interact", "open_app": "interact",
    "window_focus": "interact", "window_manage": "interact",
    "clipboard_set": "interact", "clipboard_set_image": "interact",
    "browser_goto": "interact", "browser_close_tab": "interact",
    "ask_user": "interact", "audio_listen": "interact",
    "video_frames": "interact",
    # изменения состояния
    "fs_write": "mutate", "fs_delete": "mutate", "fs_move": "mutate",
    "fs_mkdir": "mutate",
    # выполнение кода
    "run_cmd": "exec", "ssh_exec": "exec", "browser_eval": "exec",
    # сеть
    "ssh_sftp_get": "network", "ssh_sftp_put": "network",
    "download_file": "network", "web_search_pc": "network",
}

# В режиме ask сервер требует подтверждения человека для этих классов.
CONFIRM_RISKS = frozenset({"mutate", "exec", "network"})

# Клавиатура/мышь, для которых в чувствительных окнах тоже нужно подтверждение.
# mouse_move/scroll осознанно вне списка: движение курсора следов не оставляет.
SENSITIVE_GATED = frozenset({
    "mouse_click", "mouse_double_click", "mouse_right_click",
    "mouse_middle_click", "mouse_drag",
    "type_text", "press_key", "key_down", "key_up",
    "focus_type", "clipboard_set", "clipboard_set_image", "open_app",
})

# Подстроки заголовков чувствительных окон (менеджеры паролей, крипто, банки).
SENSITIVE_WINDOWS = (
    "keepass", "keepassxc", "1password", "bitwarden", "lastpass",
    "dashlane", "nordpass", "passman", "password safe",
    "metamask", "ledger", "trezor", "exodus", "trust wallet",
    "seed", "wallet", "сбер", "sber", "тиньк", "t-bank", "втб",
    "альфа-банк", "банк", "bank", "private", "secret",
)


def risk_of(tool: str) -> str:
    """Класс риска инструмента. Неизвестный tool — консервативно mutate."""
    return TOOL_RISK.get(tool, "mutate")


def safety_cfg() -> dict:
    """Секция safety конфига (пустой dict при проблемах)."""
    try:
        return load_config().get("safety", {}) or {}
    except Exception:
        return {}


def confirm_timeout() -> int:
    try:
        return max(10, min(600, int(safety_cfg().get("confirm_timeout", 120))))
    except Exception:
        return 120


def allow_minutes() -> int:
    try:
        return max(1, min(120, int(safety_cfg().get("allow_minutes", 10))))
    except Exception:
        return 10


def run_cmd_policy() -> str:
    """deny (по умолчанию) или allowlist: в allowlist-режиме разрешены только
    команды из safety.cmd_allowlist, остальное требует подтверждения."""
    try:
        v = str(safety_cfg().get("run_cmd_policy", "deny")).lower()
    except Exception:
        v = "deny"
    return v if v in ("deny", "allowlist") else "deny"


def cmd_allowlisted(cmd: str) -> bool:
    """Команда начинается с одного из разрешённых префиксов (нормализованная)."""
    try:
        allowed = safety_cfg().get("cmd_allowlist", []) or []
    except Exception:
        return False
    segs = normalize_cmd(cmd)
    for pref in allowed:
        p = " ".join(str(pref).lower().split())
        if p and any(s == p or s.startswith(p + " ") or s.startswith(p) for s in segs):
            return True
    return False


def cmd_needs_confirm(cmd: str) -> bool:
    """В allowlist-режиме команда вне списка требует подтверждения
    даже в auto. В deny-режиме решает класс риска (см. server)."""
    return run_cmd_policy() == "allowlist" and not cmd_allowlisted(cmd)


def window_is_sensitive(title: str) -> bool:
    """Заголовок активного окна похож на чувствительное (пароли/банки)?"""
    low = (title or "").lower()
    if not low:
        return False
    words = list(SENSITIVE_WINDOWS)
    try:
        extra = safety_cfg().get("sensitive_windows_extra", []) or []
        words += [str(w).lower() for w in extra]
    except Exception:
        pass
    return any(w and w in low for w in words)


def _allow_path():
    return config_dir() / "allow.json"


def allow_key(tool: str, summary: str) -> str:
    """Стабильный ключ «того же действия» для временного разрешения."""
    raw = f"{tool}::{summary}".encode("utf-8", "replace")
    return hashlib.sha1(raw).hexdigest()[:24]


def _load_allows() -> dict:
    import json

    try:
        p = _allow_path()
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save_allows(data: dict) -> None:
    import json

    try:
        _allow_path().write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def is_allowed_timed(key: str) -> bool:
    """Есть ли действующее временное разрешение (с чисткой протухших)."""
    data = _load_allows()
    now = _time.time()
    fresh = {k: v for k, v in data.items()
             if isinstance(v, (int, float)) and v > now}
    if len(fresh) != len(data):
        _save_allows(fresh)
    return key in fresh


def grant_timed(key: str, minutes: int = 0) -> None:
    """Запомнить действие на N минут (по умолчанию allow_minutes)."""
    mins = minutes or allow_minutes()
    data = _load_allows()
    data[key] = _time.time() + mins * 60
    _save_allows(data)
