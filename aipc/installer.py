"""Installer: самоустановка exe в Program Files + PATH + MCP во все IDE.

Логика: exe при первом запуске сам копирует себя в Program Files.
Если нет прав админа — сам просит UAC (runas) и продолжает работу.
Настройка MCP для IDE прав админа не требует — делается всегда.
"""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import sys
import time
from pathlib import Path


from . import __version__ as _APP_VERSION


def is_admin() -> bool:
    try:
        if os.name == "nt":
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def current_exe() -> Path:
    if is_frozen():
        return Path(sys.executable)
    return Path(sys.argv[0]).resolve()


def install_dir() -> str:
    return r"C:\Program Files\AiPC"


def exe_filename() -> str:
    """Каноническое имя файла: AiPC_Win_<версия>.exe. По нему ориентируемся везде."""
    return f"AiPC_Win_{_APP_VERSION}.exe"


def shim_name() -> str:
    """Короткая команда: aipc.bat рядом, чтобы `aipc` работало при любом релизе."""
    return "aipc.bat"


def installed_exe() -> Path:
    return Path(install_dir()) / exe_filename()


def is_installed() -> bool:
    """Exe уже лежит в Program Files (с учетом регистра и симлинков)?"""
    if not is_frozen():
        return False
    try:
        cur = current_exe().resolve()
        target = installed_exe().resolve()
    except Exception:
        return False
    try:
        return cur == target and target.exists()
    except Exception:
        return False


def relaunch_as_admin(args: str = "") -> None:
    """Перезапустить себя от админа (Windows UAC) и завершить текущий процесс."""
    if os.name != "nt":
        print("Запусти с sudo.")
        sys.exit(1)
    if not is_frozen():
        # dev-режим: python -m aipc ...
        script = f"-m aipc {args}".strip()
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, script, str(Path.cwd()), 1)
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", str(current_exe()), args, None, 1)
    sys.exit(0)


def add_to_system_path(path: str) -> tuple[bool, str]:
    """Добавить в системный PATH (HKLM). Требует админа."""
    if os.name != "nt":
        return False, "только Windows"
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE)
        try:
            cur, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            cur = ""
        if path.lower() in cur.lower():
            winreg.CloseKey(key)
            return True, "уже в PATH"
        new = cur.rstrip(";") + ";" + path
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new)
        winreg.CloseKey(key)
        # разослать WM_SETTINGCHANGE чтобы новый cmd увидел сразу
        try:
            HWND_BROADCAST, WM_SETTINGCHANGE = 0xFFFF, 0x1A
            ctypes.windll.user32.SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", 0, 5000, None)
        except Exception:
            pass
        return True, f"добавлено: {path}"
    except PermissionError:
        return False, "нужны права админа — перезапусти Setup от админа"
    except Exception as e:
        return False, str(e)


def install_self_to_program_files() -> tuple[bool, str]:
    """Копирует exe в Program Files под каноническим именем + шим aipc.bat. Требует админа."""
    if os.name != "nt":
        return False, "Program Files — только Windows (на macOS/Linux: pip install aipc-sysik)"
    dst = Path(install_dir())
    try:
        dst.mkdir(parents=True, exist_ok=True)
        if is_frozen():
            src = current_exe()
            target = dst / exe_filename()
            # Не копировать самого себя
            try:
                if src.resolve() == target.resolve() and target.exists():
                    _write_shim(dst)
                    return True, f"уже на месте: {target}"
            except Exception:
                pass
            shutil.copy2(src, target)
            _clean_legacy(dst, keep=target.name)
            _write_shim(dst)
            # Рядом кладем пресеты чтобы menu их находило и в frozen-режиме
            try:
                (dst / "mcp_presets").mkdir(exist_ok=True)
            except Exception:
                pass
            return True, f"скопировано {src.name} -> {target}"
        return True, f"папка готова: {dst} (dev-режим: добавь проект в PATH вручную или собери exe)"
    except PermissionError:
        return False, "нужны права админа"
    except Exception as e:
        return False, str(e)


def _clean_legacy(dst: Path, keep: str) -> None:
    """Убрать старый aipc.exe и прошлые версии AiPC_Win_*.exe, кроме текущей."""
    try:
        for child in dst.iterdir():
            if not child.is_file():
                continue
            name = child.name
            if name == keep or name.lower() == shim_name():
                continue
            if name.lower() == "aipc.exe" or (name.startswith("AiPC_Win_") and name.lower().endswith(".exe")):
                try:
                    child.unlink()
                except Exception:
                    pass
    except Exception:
        pass


def _write_shim(dst: Path) -> None:
    """Шим `aipc.bat`: команда `aipc` работает при любом имени релиза."""
    try:
        (dst / shim_name()).write_text(f'@"%~dp0{exe_filename()}" %*\n', encoding="utf-8")
    except Exception:
        pass


# --- MCP: пути конфигов IDE на Windows ---
# only_if: писать сюда только если этот путь уже существует (не плодим мусор чужим IDE).

def _home() -> Path:
    return Path(os.path.expanduser("~"))


def _base_dirs(os_name: str | None = None, platform: str | None = None,
               home=None, env=None) -> tuple[Path, Path]:
    """(appdata, userprofile) с учётом ОС: Windows / macOS / Linux (XDG)."""
    import os as _os
    import sys as _sys

    os_name = os_name if os_name is not None else _os.name
    platform = platform if platform is not None else _sys.platform
    env = env if env is not None else _os.environ
    home = Path(home) if home is not None else _home()
    if os_name == "nt":
        appdata = Path(env.get("APPDATA", str(home / "AppData" / "Roaming")))
        userprofile = Path(env.get("USERPROFILE", str(home)))
    elif platform == "darwin":
        appdata = home / "Library" / "Application Support"
        userprofile = home
    else:
        appdata = Path(env.get("XDG_CONFIG_HOME", str(home / ".config")))
        userprofile = home
    return appdata, userprofile


def ide_config_paths() -> list[tuple[str, Path, Path | None, str]]:
    """(имя IDE, путь к конфигу, only_if, writer).

    writer: mcpServers | opencode | zed | vscode-mcp | continue-yaml | codex-toml.
    only_if: писать только если путь существует (не плодим мусор чужим IDE).
    """
    home = _home()
    appdata, userprofile = _base_dirs()
    main_antigravity = home / ".gemini" / "config" / "mcp_config.json"
    main_cursor = home / ".cursor" / "mcp.json"
    main_vscode = appdata / "Code" / "User" / "mcp_settings.json"
    gemini_settings = home / ".gemini" / "settings.json"
    claude_code_state = home / ".claude.json"
    roo_dir = appdata / "Code" / "User" / "globalStorage" / "rooveterinaryinc.roo-cline"
    cline_settings = (appdata / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev"
                      / "settings" / "cline_mcp_settings.json")
    vscode_settings = appdata / "Code" / "User" / "settings.json"
    codex_config = userprofile / ".codex" / "config.toml"
    opencode_config = home / ".config" / "opencode" / "opencode.json"
    zed_settings = home / ".config" / "zed" / "settings.json"
    windsurf_marker = userprofile / ".codeium"
    continue_dir = home / ".continue"
    kiro_marker = home / ".kiro"
    trae_marker = appdata / "Trae"
    amazonq_marker = home / ".aws" / "amazonq"
    return [
        ("Antigravity", main_antigravity, None, "mcpServers"),
        ("Antigravity-alt", home / ".gemini" / "antigravity" / "mcp_config.json", main_antigravity, "mcpServers"),
        ("Cursor", main_cursor, None, "mcpServers"),
        ("Cursor-alt", appdata / "Cursor" / "User" / "mcp.json", main_cursor, "mcpServers"),
        ("VSCode-Cline", main_vscode, None, "mcpServers"),
        ("Cline-ext", cline_settings, roo_dir.parent, "mcpServers"),
        ("VSCode-Roo", roo_dir / "settings" / "mcp_settings.json", roo_dir, "mcpServers"),
        ("VSCode-Copilot", vscode_settings, vscode_settings, "vscode-mcp"),
        ("GeminiCLI", gemini_settings, gemini_settings, "mcpServers"),
        ("ClaudeCode", claude_code_state, claude_code_state, "mcpServers"),
        ("ClaudeDesktop", appdata / "Claude" / "claude_desktop_config.json", None, "mcpServers"),
        ("OpenCode", opencode_config, opencode_config, "opencode"),
        ("CodexCLI", codex_config, codex_config, "codex-toml"),
        ("Zed", zed_settings, zed_settings, "zed"),
        ("Windsurf", userprofile / ".codeium" / "windsurf" / "mcp_config.json", windsurf_marker, "mcpServers"),
        ("Continue", continue_dir / "mcpServers" / "aipc.yaml", continue_dir, "continue-yaml"),
        ("Kiro", home / ".kiro" / "settings" / "mcp.json", kiro_marker, "mcpServers"),
        ("Trae", appdata / "Trae" / "User" / "mcp.json", trae_marker, "mcpServers"),
        ("AmazonQ", home / ".aws" / "amazonq" / "mcp.json", amazonq_marker, "mcpServers"),
    ]


def mcp_server_entry() -> tuple[str, list[str]]:
    """Правильная пара (command, args) для MCP-конфигов.

    ВАЖНО: command — только путь к исполняемому файлу, без аргументов одной строкой,
    иначе MCP-клиенты (Cursor/VS Code/Claude) не смогут запустить сервер.
    """
    if is_frozen():
        exe = str(installed_exe() if is_installed() else current_exe())
        return exe, ["mcp"]
    return sys.executable, ["-m", "aipc", "mcp"]


def _strip_jsonc(text: str) -> str:
    """Убрать // и /* */ комментарии + висячие запятые (VS Code/Zed/Cursor пишут JSONC)."""
    out, i, n = [], 0, len(text)
    in_str, esc = False, False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(c)
        i += 1
    import re as _re

    return _re.sub(r",\s*([}\]])", r"\1", "".join(out))


def _load_json(path: Path) -> tuple[dict, bool]:
    """Прочитать JSON/JSONC-конфиг. Возвращает (data, existed)."""
    if path.exists():
        try:
            bak = path.with_suffix(path.suffix + ".bak")
            if not bak.exists():
                shutil.copy2(path, bak)
            return json.loads(_strip_jsonc(path.read_text(encoding="utf-8")) or "{}"), True
        except Exception:
            return {}, True
    return {}, False


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_mcp_file(path: Path, command: str, args: list[str], writer: str = "mcpServers") -> tuple[bool, str]:
    """Аккуратно дописать aipc в конфиг IDE. Бэкап .bak. Возвращает (ok, msg)."""
    try:
        data, existed = _load_json(path)
        if writer == "mcpServers":
            entry = {"command": command, "args": args}
            servers = data.get("mcpServers")
            if not isinstance(servers, dict):
                servers = {}
                data["mcpServers"] = servers
            if servers.get("aipc") == entry:
                return True, f"{path}: уже настроено"
            servers["aipc"] = entry
        elif writer == "opencode":
            # opencode.json: {"mcp": {"aipc": {"type": "local", "command": [...], "enabled": true}}}
            entry = {"type": "local", "command": [command] + args, "enabled": True}
            mcp = data.get("mcp")
            if not isinstance(mcp, dict):
                mcp = {}
                data["mcp"] = mcp
            if mcp.get("aipc") == entry:
                return True, f"{path}: уже настроено"
            mcp["aipc"] = entry
        elif writer == "zed":
            # Zed settings.json: {"context_servers": {"aipc": {"command": ..., "args": [...]}}}
            entry = {"command": command, "args": args}
            cs = data.get("context_servers")
            if not isinstance(cs, dict):
                cs = {}
                data["context_servers"] = cs
            if cs.get("aipc") == entry:
                return True, f"{path}: уже настроено"
            cs["aipc"] = entry
        elif writer == "vscode-mcp":
            # VS Code native (Copilot): {"mcp": {"servers": {"aipc": {...}}}}
            entry = {"command": command, "args": args}
            mcp = data.get("mcp")
            if not isinstance(mcp, dict):
                mcp = {}
                data["mcp"] = mcp
            servers = mcp.get("servers")
            if not isinstance(servers, dict):
                servers = {}
                mcp["servers"] = servers
            if servers.get("aipc") == entry:
                return True, f"{path}: уже настроено"
            servers["aipc"] = entry
        else:
            return False, f"неизвестный writer: {writer}"
        _save_json(path, data)
        return True, f"{path}: прописано" + ("" if existed else " (новый файл)")
    except Exception as e:
        return False, f"{path}: {e}"


def _write_continue_yaml(path: Path, command: str, args: list[str]) -> tuple[bool, str]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return True, f"{path}: уже настроено (проверь вручную)"
        text = (f"name: AiPC\nversion: 1.0.0\nschema: v1\n"
                f"command: {command}\nargs:\n" + "".join(f"  - {a}\n" for a in args))
        path.write_text(text, encoding="utf-8")
        return True, f"{path}: прописано"
    except Exception as e:
        return False, f"{path}: {e}"


def _append_codex_toml(path: Path, command: str, args: list[str]) -> tuple[bool, str]:
    """Дописать секцию [mcp_servers.aipc] в config.toml Codex (только append, файл не парсим)."""
    try:
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        if "[mcp_servers.aipc]" in existing:
            return True, f"{path}: уже настроено (проверь вручную)"
        esc = command.replace("\\", "\\\\").replace('"', '\\"')
        q = chr(34)
        args_s = ", ".join(q + a.replace("\\", "\\\\").replace('"', '\\"') + q for a in args)
        block = f"\n[mcp_servers.aipc]\ncommand = \"{esc}\"\nargs = [{args_s}]\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(block)
        return True, f"{path}: прописано"
    except Exception as e:
        return False, f"{path}: {e}"


def _ide_selected(name: str, only: list[str] | None) -> bool:
    """Фильтр --ide: подстрока без учёта регистра (cursor, vscode, claude...)."""
    if not only:
        return True
    low = name.lower()
    return any(str(o).lower() in low for o in only)


def configure_all_ides(command: str | None = None, args: list[str] | None = None,
                       only: list[str] | None = None,
                       create_missing: bool = False) -> list[tuple[str, bool, str]]:
    """Прописать aipc в IDE. Прав админа не надо. Возвращает отчет.

    only — только эти IDE (подстроки имён). create_missing=False (по умолчанию):
    не создавать конфиги отсутствующих IDE — правим только существующие файлы.
    """
    if command is None or args is None:
        command, args = mcp_server_entry()
    report: list[tuple[str, bool, str]] = []
    entries = ide_config_paths()
    # Слепок ДО записи: alt-пути не должны видеть файлы, созданные нами же в этом проходе
    pre = {name: (only_if.exists() if only_if is not None else True) for name, _, only_if, _ in entries}
    for name, path, only_if, writer in entries:
        try:
            if not _ide_selected(name, only):
                continue
            if not pre.get(name, True):
                continue
            present = path.exists() or (only_if is not None and only_if.exists())
            if not present and not create_missing:
                # Молча пропускаем отсутствующие IDE; но при явном --ide
                # говорим, что такой IDE нет (иначе тишина сбивает с толку).
                if only:
                    report.append((name, True, f"{path}: IDE нет — пропущено"))
                continue
            if writer == "continue-yaml":
                ok, msg = _write_continue_yaml(path, command, args)
            elif writer == "codex-toml":
                ok, msg = _append_codex_toml(path, command, args)
            else:
                ok, msg = merge_mcp_file(path, command, args, writer)
            report.append((name, ok, msg))
        except Exception as e:
            report.append((name, False, str(e)))
    return report


def preview_ide_entry(path: Path, writer: str, command: str,
                      args: list[str]) -> str:
    """Что изменится в конфиге IDE (без записи): короткий diff-текст."""
    try:
        if writer == "codex-toml":
            existing = path.read_text(encoding="utf-8") if path.exists() else ""
            if "[mcp_servers.aipc]" in existing:
                return "без изменений (уже настроено)"
            return "+ секция [mcp_servers.aipc]"
        if writer == "continue-yaml":
            if path.exists():
                return "без изменений (файл есть, правим вручную)"
            return "+ новый файл aipc.yaml"
        key = {"mcpServers": "mcpServers.aipc", "opencode": "mcp.aipc",
               "zed": "context_servers.aipc",
               "vscode-mcp": "mcp.servers.aipc"}.get(writer, "aipc")
        if not path.exists():
            return f"+ новый файл, {key} = {command} {args}"
        try:
            data = json.loads(_strip_jsonc(path.read_text(encoding="utf-8")) or "{}")
        except Exception:
            return "! файл битый — запись перезапишет (бэкап .bak уже снят при записи)"
        node: object = data
        for part in key.split("."):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        if isinstance(node, dict) and node.get("command") == command:
            return "без изменений (уже настроено)"
        old = json.dumps(node, ensure_ascii=False)[:120] if node else "—"
        return f"{key}: {old} -> command={command}"
    except Exception as e:
        return f"не прочитал: {e}"


def plan_install(only: list[str] | None = None,
                 create_missing: bool = False) -> list[dict]:
    """План установки БЕЗ записи: что будет изменено и как."""
    command, args = mcp_server_entry()
    plan: list[dict] = []
    if is_frozen() and not is_installed():
        plan.append({"kind": "program_files", "target": str(installed_exe()),
                     "action": "copy",
                     "detail": f"копия exe + шим {shim_name()}"})
    else:
        plan.append({"kind": "program_files", "target": install_dir(),
                     "action": "skip",
                     "detail": "dev-режим или уже на месте"})
    plan.append({"kind": "path", "target": install_dir(), "action": "add",
                 "detail": "HKLM PATH (нужен админ)"})
    entries = ide_config_paths()
    for name, path, only_if, writer in entries:
        if not _ide_selected(name, only):
            continue
        present = path.exists() or (only_if is not None and only_if.exists())
        if not present and not create_missing:
            plan.append({"kind": "ide", "target": f"{name}: {path}",
                         "action": "skip", "detail": "IDE нет"})
            continue
        plan.append({"kind": "ide", "target": f"{name}: {path}",
                     "action": "write",
                     "detail": preview_ide_entry(path, writer, command, args)})
    return plan


def _remove_json_entry(path: Path, writer: str) -> tuple[bool, str]:
    """Убрать наш ключ aipc из JSON-конфига. Возвращает (ok, msg)."""
    try:
        if not path.exists():
            return True, f"{path}: файла нет"
        try:
            data = json.loads(_strip_jsonc(path.read_text(encoding="utf-8")) or "{}")
        except Exception:
            return False, f"{path}: битый JSON — пропускаю (не трогаю)"
        holder: dict | None = None
        if writer == "mcpServers":
            holder = data.get("mcpServers") if isinstance(data.get("mcpServers"), dict) else None
        elif writer == "opencode":
            holder = data.get("mcp") if isinstance(data.get("mcp"), dict) else None
        elif writer == "zed":
            holder = data.get("context_servers") if isinstance(data.get("context_servers"), dict) else None
        elif writer == "vscode-mcp":
            mcp = data.get("mcp") if isinstance(data.get("mcp"), dict) else None
            holder = mcp.get("servers") if isinstance(mcp, dict) and isinstance(mcp.get("servers"), dict) else None
        else:
            return False, f"{path}: неизвестный writer {writer}"
        if not holder or "aipc" not in holder:
            return True, f"{path}: нас нет"
        del holder["aipc"]
        _save_json(path, data)
        return True, f"{path}: убрано"
    except Exception as e:
        return False, f"{path}: {e}"


def _remove_codex_block(path: Path) -> tuple[bool, str]:
    try:
        if not path.exists():
            return True, f"{path}: файла нет"
        text = path.read_text(encoding="utf-8")
        if "[mcp_servers.aipc]" not in text:
            return True, f"{path}: нас нет"
        import re as _re

        new = _re.sub(r"\n\[mcp_servers\.aipc\]\n(?:[^\[]*\n)?", "\n", text)
        if new == text:  # запасной вариант: построчно
            lines = [l for l in text.splitlines(keepends=True)
                     if "mcp_servers.aipc" not in l]
            new = "".join(lines)
        path.write_text(new, encoding="utf-8")
        return True, f"{path}: убрано"
    except Exception as e:
        return False, f"{path}: {e}"


def _remove_continue_file(path: Path) -> tuple[bool, str]:
    try:
        if not path.exists():
            return True, f"{path}: файла нет"
        text = path.read_text(encoding="utf-8")
        if "name: AiPC" not in text:
            return False, f"{path}: чужой файл — не трогаю"
        path.unlink()
        return True, f"{path}: удалён наш файл"
    except Exception as e:
        return False, f"{path}: {e}"


def uninstall_mcp(only: list[str] | None = None) -> list[tuple[str, bool, str]]:
    """Убрать наши записи из конфигов IDE (чужие ключи не трогаем)."""
    report: list[tuple[str, bool, str]] = []
    for name, path, _only_if, writer in ide_config_paths():
        if not _ide_selected(name, only):
            continue
        try:
            if writer == "continue-yaml":
                ok, msg = _remove_continue_file(path)
            elif writer == "codex-toml":
                ok, msg = _remove_codex_block(path)
            else:
                ok, msg = _remove_json_entry(path, writer)
            report.append((name, ok, msg))
        except Exception as e:
            report.append((name, False, str(e)))
    return report


def remove_from_system_path(path: str) -> tuple[bool, str]:
    """Убрать каталог из системного PATH (HKLM). Требует админа."""
    if os.name != "nt":
        return False, "только Windows"
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE)
        try:
            cur, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            winreg.CloseKey(key)
            return True, "PATH пуст"
        parts = [p for p in cur.split(";") if p and p.lower().rstrip("\\") != path.lower().rstrip("\\")]
        new = ";".join(parts)
        if new == cur:
            winreg.CloseKey(key)
            return True, "нас нет в PATH"
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new)
        winreg.CloseKey(key)
        try:
            HWND_BROADCAST, WM_SETTINGCHANGE = 0xFFFF, 0x1A
            ctypes.windll.user32.SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", 0, 5000, None)
        except Exception:
            pass
        return True, f"убрано из PATH: {path}"
    except PermissionError:
        return False, "нужны права админа"
    except Exception as e:
        return False, str(e)


def uninstall_self(only: list[str] | None = None) -> list[tuple[str, bool, str]]:
    """Полный откат: MCP-записи + PATH + наши файлы в Program Files."""
    report: list[tuple[str, bool, str]] = []
    for name, ok, msg in uninstall_mcp(only):
        report.append((name, ok, msg))
    ok, msg = remove_from_system_path(install_dir())
    report.append(("PATH", ok, msg))
    try:
        dst = Path(install_dir())
        removed = []
        if dst.is_dir():
            for child in dst.iterdir():
                if not child.is_file():
                    continue
                n = child.name
                if n == shim_name() or (n.startswith("AiPC_Win_") and n.lower().endswith(".exe")):
                    try:
                        child.unlink()
                        removed.append(n)
                    except Exception as e:
                        report.append(("Program Files", False, f"{n}: {e}"))
        report.append(("Program Files", True,
                       f"убрано: {', '.join(removed) if removed else 'наших файлов нет'}"))
    except Exception as e:
        report.append(("Program Files", False, str(e)))
    return report


def privileged_self_install() -> int:
    """Шаг с правами админа: копия в Program Files + PATH. Вызывается как `aipc --self-install`."""
    if os.name != "nt":
        print("Эта установка — только Windows. На macOS/Linux: pip install aipc-sysik")
        return 1
    print("=== AiPC: установка (админ) ===")
    ok1, msg1 = install_self_to_program_files()
    print(f"[1/2] {msg1}")
    ok2, msg2 = add_to_system_path(install_dir())
    print(f"[2/2] {msg2}")
    for name, ok, msg in configure_all_ides(str(installed_exe()), ["mcp"]):
        print(f"[mcp] {name}: {msg}")
    return 0 if (ok1 and ok2) else 1


def _installed_is_fresh() -> bool:
    """Копия в Program Files существует И совпадает с нами по размеру."""
    try:
        target = installed_exe()
        return target.exists() and target.stat().st_size == current_exe().stat().st_size
    except Exception:
        return False


def _auto_register_enabled() -> bool:
    """Можно ли трогать IDE-конфиги без явной команды (по умолчанию нет)."""
    try:
        from .config import load_config

        return bool(load_config().get("installer", {}).get("auto_register", False))
    except Exception:
        return False


def ensure_installed() -> str:
    """Гарантировать что exe в Program Files + MCP настроен. Возвращает путь к exe для работы.

    - dev-режим (python): ничего не копирует, только MCP на текущий python-модуль.
    - frozen в Program Files: обновляет MCP и работает прямо здесь.
    - frozen вне Program Files: тихая установка (админ-окно скрыто, прогресс точками
      в этом окне), затем работаем ДАЛЬШЕ В ЭТОМ ЖЕ ОКНЕ — никаких новых окон,
      сворачиваний и перезапусков. При отказе UAC — тоже продолжаем в меню с предупреждением.
    """
    if not is_frozen():
        if _auto_register_enabled():
            configure_all_ides()
        return str(current_exe())

    if os.name != "nt":
        # macOS/Linux: Program Files/PATH/UAC нет — только MCP по явной команде.
        return str(current_exe())

    if is_installed():
        if _auto_register_enabled():
            configure_all_ides(*mcp_server_entry())
        return str(installed_exe())

    # Первый запуск не из Program Files
    if not is_admin():
        print("Первый запуск: кладу себя в Program Files и настраиваю MCP.")
        print("Сейчас попрошу права админа один раз, установка пойдет в этом окне...")
        time.sleep(1)
        # SW_HIDE(0): админ-консоль не мелькает отдельным окном
        ctypes.windll.shell32.ShellExecuteW(None, "runas", str(current_exe()), "--self-install", None, 0)
        ok = False
        for i in range(120):
            time.sleep(1)
            if i % 5 == 4:
                print(".", end="", flush=True)
            if _installed_is_fresh():
                ok = True
                break
        print()
        if ok:
            print("Установлено. Продолжаю в этом окне.")
            if _auto_register_enabled():
                configure_all_ides(str(installed_exe()), ["mcp"])
            return str(current_exe())
        print("Не дождался установки (UAC отклонён или ошибка).")
        print("Работаю без установки — команда `aipc` и MCP в IDE появятся после установки.")
        if _auto_register_enabled():
            configure_all_ides(*mcp_server_entry())
        return str(current_exe())

    # Уже админ, но лежим не там — ставим и продолжаем здесь же
    privileged_self_install()
    if _auto_register_enabled():
        configure_all_ides(*mcp_server_entry())
    return str(current_exe())
