"""Самообновление, диагностика, аварийная остановка. Без эмодзи."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen


def parse_version(s: str) -> tuple[int, ...]:
    s = s.strip().lstrip("vV")
    parts = []
    for p in s.split("."):
        digits = "".join(c for c in p if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) or (0,)


UPDATE_REPO = "SysikNagibator/AiPC"

# Кэш авто-проверки обновлений: {"latest": str, "has": bool, "ts": float}.
_update_cache: dict = {}
_update_lock = None


def _get_update_lock():
    global _update_lock
    if _update_lock is None:
        import threading

        _update_lock = threading.Lock()
    return _update_lock


def auto_check_enabled() -> bool:
    """Автопроверка обновлений при старте меню (update.auto_check)."""
    try:
        from .config import load_config

        upd = load_config().get("update", {})
        if not isinstance(upd, dict):
            return True
        return bool(upd.get("auto_check", True))
    except Exception:
        return True


def refresh_update_cache_async(timeout: int = 8) -> None:
    """Фоновая проверка релиза на НОВОМ гите. Не блокирует меню."""
    if not auto_check_enabled():
        return
    import threading
    import time as _time

    def _job():
        try:
            info = check_update(UPDATE_REPO)
            if not info.get("ok"):
                return
            with _get_update_lock():
                _update_cache.clear()
                _update_cache.update({
                    "latest": str(info.get("latest", "")),
                    "has": bool(info.get("update")),
                    "ts": _time.time(),
                })
        except Exception:
            pass

    try:
        t = threading.Thread(target=_job, daemon=True)
        t.start()
    except Exception:
        pass


def cached_update_notice(lang: str = "en") -> str:
    """Текст уведомления для меню ('' если нечего показывать)."""
    try:
        with _get_update_lock():
            has = bool(_update_cache.get("has"))
            latest = str(_update_cache.get("latest", ""))
        if not has or not latest:
            return ""
        from .i18n import t as _t

        tmpl = _t("update.available")
        return tmpl.format(ver=latest) if "{ver}" in tmpl else f"{tmpl} {latest}"
    except Exception:
        return ""


def _wanted_asset(names: list[str]) -> str | None:
    """Имя ассета под текущую ОС (первый подходящий)."""
    lows = [(n or "").lower() for n in names]
    if sys.platform == "win32":
        for n, low in zip(names, lows):
            if low.endswith(".exe"):
                return n
        return None
    if sys.platform == "darwin":
        keys = ("macos", "darwin", "apple", ".dmg", ".zip")
    else:
        keys = ("linux", ".tar.gz", ".appimage", ".zip")
    for n, low in zip(names, lows):
        if low.endswith(".exe"):
            continue
        if any(k in low for k in keys):
            return n
    return None


def check_update(repo: str = UPDATE_REPO) -> dict:
    """Проверить свежий релиз на GitHub. Возвращает статус + ссылку."""
    from . import __version__ as cur

    try:
        req = Request(
            f"https://api.github.com/repos/{repo}/releases/latest",
            headers={"Accept": "application/vnd.github+json", "User-Agent": "AiPC-updater"},
        )
        with urlopen(req, timeout=20) as r:
            data = __import__("json").loads(r.read().decode("utf-8"))
        tag = str(data.get("tag_name", ""))
        assets = [{"name": a.get("name"), "url": a.get("browser_download_url"), "size": a.get("size")}
                  for a in data.get("assets", [])]
        want = _wanted_asset([a["name"] for a in assets])
        exe = next((a for a in assets if a["name"] == want), None)
        sums = next((a for a in assets
                     if a["name"] and a["name"].lower() in ("sha256sums.txt", "sha256sum.txt",
                                                            "checksums.txt")), None)
        if parse_version(tag) > parse_version(cur):
            return {"ok": True, "update": True, "current": cur, "latest": tag,
                    "url": data.get("html_url"), "exe_url": exe["url"] if exe else None,
                    "exe_name": exe["name"] if exe else None,
                    "sums_url": sums["url"] if sums else None,
                    "notes": str(data.get("body", ""))[:2000]}
        return {"ok": True, "update": False, "current": cur, "latest": tag or cur}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _sha256_file(path) -> str:
    """SHA-256 hex файла (стримом, без загрузки в память)."""
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_expected_hash(sums_text: str, exe_name: str) -> str:
    """Ищем хеш нашего exe в SHA256SUMS. Понимаем два формата:
    certutil (`...имя-файла:\n<64hex>\n...`) и github (`<64hex>  имя`).
    Возвращает hex или ''."""
    import re as _re

    text = sums_text or ""
    if exe_name:
        # github-формат: хеш и имя на одной строке
        for line in text.splitlines():
            if exe_name in line:
                m = _re.search(r"[0-9a-fA-F]{64}", line)
                if m:
                    return m.group(0).lower()
        # certutil-формат: имя в одной строке, хеш — в следующих
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if exe_name in line:
                tail = "\n".join(lines[i:i + 4])
                m = _re.search(r"[0-9a-fA-F]{64}", tail)
                if m:
                    return m.group(0).lower()
    return ""


def self_update(repo: str = UPDATE_REPO) -> int:
    """Скачать свежий exe, сверить SHA256 с SHA256SUMS релиза, запустить
    самоустановку (с UAC). Текущий процесс выходит."""
    info = check_update(repo)
    if not info.get("ok"):
        print(f"Не проверить обновление: {info.get('error')}")
        return 1
    if not info.get("update"):
        print(f"Уже свежее: {info.get('current')}")
        return 0
    url = info.get("exe_url")
    if not url:
        print(f"В релизе {info.get('latest')} нет exe. Страница: {info.get('url')}")
        return 1
    if not info.get("sums_url"):
        # Без контрольных сумм ставить нельзя: иначе подмена бинарника
        # неотличима. Обновитесь вручную со страницы релиза.
        print(f"В релизе {info.get('latest')} нет SHA256SUMS — автообновление запрещено.")
        print(f"Скачайте вручную и сверьте хеш: {info.get('url')}")
        return 1
    print(f"Качаю {info.get('latest')} ...")
    import re as _re

    from .os_ops import check_free_space

    safe_ver = _re.sub(r"[^A-Za-z0-9._-]", "_", str(info.get("latest", "new")))[:40] or "new"
    suffix = ".exe" if os.name == "nt" else ".bin"
    tmp = Path(tempfile.gettempdir()) / f"aipc-update-{safe_ver}{suffix}"
    try:
        ok, err = check_free_space(str(tmp), 300 * 1048576)
        if not ok:
            print(f"Не качаю: {err}")
            return 1
        size = 0
        req = Request(url, headers={"User-Agent": "AiPC-updater"})
        with urlopen(req, timeout=600) as r, tmp.open("wb") as f:
            head = b""
            while len(head) < 4:
                part = r.read(4 - len(head))
                if not part:
                    break
                head += part
            if os.name == "nt":
                ok_magic = head[:2] == b"MZ"
                want = "exe (MZ)"
            elif sys.platform == "darwin":
                ok_magic = head[:4] in (b"\xcf\xfa\xed\xfe", b"\xcf\xfa\xce\xfa",
                                        b"\xca\xfe\xba\xbe", b"PK\x03\x04")
                want = "Mach-O/zip"
            else:
                ok_magic = head[:4] == b"\x7fELF" or head[:2] == b"PK"
                want = "ELF/zip"
            if not ok_magic:
                print(f"Не качаю: сервер отдал не бинарь (нет сигнатуры {want})")
                return 1
            f.write(head)
            size = len(head)
            while True:
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                size += len(chunk)
                if size > 300 * 1048576:
                    try:
                        tmp.unlink()
                    except Exception:
                        pass
                    print("Не качаю: файл больше 300 МБ")
                    return 1
                f.write(chunk)
        print(f"Скачано: {tmp} ({tmp.stat().st_size // 1048576} МБ)")
    except Exception as e:
        print(f"Не скачать: {e}")
        return 1
    # Сверка хеша с SHA256SUMS релиза — без совпадения не запускаем.
    try:
        req = Request(info["sums_url"], headers={"User-Agent": "AiPC-updater"})
        with urlopen(req, timeout=30) as r:
            sums_text = r.read().decode("utf-8", errors="replace")
        expected = _find_expected_hash(sums_text, info.get("exe_name") or "")
        if not expected:
            print("В SHA256SUMS нет хеша нашего файла — установка запрещена.")
            print(f"Проверьте вручную: {info.get('url')}")
            try:
                tmp.unlink()
            except Exception:
                pass
            return 1
        actual = _sha256_file(tmp)
        if actual != expected:
            print(f"ХЕШ НЕ СОВПАЛ: ждали {expected[:16]}…, получили {actual[:16]}…")
            print("Возможно подмена файла. Установка запрещена, файл удалён.")
            try:
                tmp.unlink()
            except Exception:
                pass
            return 1
        print(f"SHA256 сошёлся: {actual[:16]}…")
    except Exception as e:
        print(f"Не сверить хеш: {e}")
        return 1
    # Новый файл сам себя ставит (с UAC) — текущий процесс больше не нужен.
    # На macOS/Linux автоустановки нет: файл проверен, дальше руками.
    if os.name != "nt":
        print(f"Готово: {tmp}")
        print("Распакуй/запусти вручную или обновись через: pip install -U aipc-sysik")
        return 0
    try:
        subprocess.Popen([str(tmp), "--self-install"])
    except Exception as e:
        print(f"Не запустить установку: {e}. Запусти вручную: {tmp}")
        return 1
    return 0


def _pid_is_ours(pid: int) -> bool:
    """PID действительно наш Core? Иначе чужой процесс не трогаем (PID reuse)."""
    try:
        import psutil  # type: ignore

        p = psutil.Process(pid)
        cmd = " ".join(p.cmdline() or []).lower()
        return "aipc" in cmd
    except Exception:
        pass
    try:
        # Fallback без psutil
        r = subprocess.run(f'tasklist /FI "PID eq {pid}" /FO CSV /NH', shell=True, capture_output=True, text=True, timeout=10)
        out = (r.stdout or "").lower()
        if not out.strip() or "no tasks" in out or "нет задач" in out:
            return False
        r = subprocess.run(f'wmic process where "ProcessId={pid}" get CommandLine /FORMAT:LIST', shell=True, capture_output=True, text=True, timeout=10)
        return "aipc" in (r.stdout or "").lower()
    except Exception:
        return False


def kill_core() -> dict:
    """Аварийно остановить Core по PID-файлу. Чужой PID не трогаем."""
    from .config import config_dir
    from .i18n import t

    pid_file = config_dir() / "aipc.pid"
    try:
        if not pid_file.exists():
            return {"ok": True, "note": t("kill.none")}
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
        except ValueError:
            pid_file.unlink(missing_ok=True)
            return {"ok": True, "note": t("kill.bad")}
        if not _pid_is_ours(pid):
            pid_file.unlink(missing_ok=True)
            return {"ok": True, "note": t("kill.gone").format(pid=pid)}
        if sys.platform == "win32":
            subprocess.run(f"taskkill /PID {pid} /F", shell=True, capture_output=True)
        else:
            try:
                os.kill(pid, 15)
            except ProcessLookupError:
                pass
        pid_file.unlink(missing_ok=True)
        return {"ok": True, "note": t("kill.done").format(pid=pid)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def core_running() -> bool:
    """Запущен ли Core (для статуса в меню). Только чтение, чужое не трогаем.

    Результат кэшируется на 10 с: проверка идёт через psutil/ tasklist+wmic,
    дёргать её на каждое открытие подменю — лаговать.
    """
    from .config import config_dir

    global _core_cache
    try:
        import time as _time

        now = _time.monotonic()
        ts, val = _core_cache
        if now - ts < 10.0:
            return val
    except Exception:
        now, val = 0.0, False
    try:
        pid_file = config_dir() / "aipc.pid"
        if not pid_file.exists():
            out = False
        else:
            try:
                out = _pid_is_ours(int(pid_file.read_text(encoding="utf-8").strip()))
            except (ValueError, OSError):
                out = False
    except Exception:
        out = False
    try:
        import time as _time2

        _core_cache = (_time2.monotonic(), out)
    except Exception:
        pass
    return out


_core_cache: tuple = (0.0, False)


def _exe_version(path: str) -> str:
    """Версия exe через --version (без падений)."""
    try:
        r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=30)
        v = (r.stdout or "").strip().split()[0]
        return v if v else "?"
    except Exception:
        return "?"


def doctor() -> list[tuple[str, bool, str]]:
    """Полная диагностика: установка, PATH, конфиги IDE, Chrome, Core."""
    from .config import config_dir, load_config
    from .installer import current_exe, exe_filename, install_dir, installed_exe, is_admin, is_frozen, is_installed

    out: list[tuple[str, bool, str]] = []
    py_ok = sys.version_info >= (3, 10)
    out.append(("python", py_ok, f"{sys.version.split()[0]} (нужен 3.10+)"))
    out.append(("права админа", True, f"admin={is_admin()}"))
    if is_frozen():
        cur = str(current_exe())
        inst = str(installed_exe())
        mine = _exe_version(cur)
        theirs = _exe_version(inst) if Path(inst).exists() else "нет"
        out.append(("установка", True, f"запущен {mine} из {cur}"))
        if Path(inst).exists():
            flag = mine == theirs
            out.append(("Program Files", flag, f"там {theirs}" + ("" if flag else " — УСТАРЕЛ, запусти свежий exe для обновления")))
        else:
            out.append(("Program Files", False, "не установлен — запусти exe для установки"))
        paths = os.environ.get("PATH", "")
        out.append(("PATH", install_dir().lower() in paths.lower(), install_dir()))
    else:
        out.append(("режим", True, "dev (python -m aipc)"))
    try:
        cfg = load_config()
        out.append(("конфиг", True, f"mode={cfg.get('mode')} | {config_dir() / 'config.yaml'}"))
    except Exception as e:
        out.append(("конфиг", False, str(e)))
    try:
        from .installer import ide_config_paths

        import json

        for name, path, only_if, writer in ide_config_paths():
            if only_if is not None and not only_if.exists():
                continue
            if not path.exists():
                out.append((f"IDE {name}", False, "конфиг не найден"))
                continue
            try:
                from .installer import _strip_jsonc

                text = path.read_text(encoding="utf-8") or ""
                if writer == "codex-toml":
                    out.append((f"IDE {name}", "[mcp_servers.aipc]" in text,
                                "aipc прописан" if "[mcp_servers.aipc]" in text else "нет секции aipc"))
                    continue
                if writer == "continue-yaml":
                    out.append((f"IDE {name}", "AiPC" in text,
                                "aipc прописан" if "AiPC" in text else "нет записи aipc"))
                    continue
                data = json.loads(_strip_jsonc(text))
                if writer == "opencode":
                    entry = (data.get("mcp") or {}).get("aipc")
                elif writer == "zed":
                    entry = (data.get("context_servers") or {}).get("aipc")
                elif writer == "vscode-mcp":
                    entry = ((data.get("mcp") or {}).get("servers") or {}).get("aipc")
                else:
                    entry = (data.get("mcpServers") or {}).get("aipc")
                if not entry:
                    out.append((f"IDE {name}", False, "нет записи aipc"))
                elif not Path(str(entry.get("command", ""))).exists() and str(entry.get("command", "")).lower() != "aipc":
                    out.append((f"IDE {name}", False, f"exe не найден: {entry.get('command')}"))
                else:
                    out.append((f"IDE {name}", True, "aipc прописан"))
            except Exception as e:
                out.append((f"IDE {name}", False, f"битый конфиг: {e}"))
    except Exception as e:
        out.append(("IDE", False, str(e)))
    try:
        from .browser import browser_tabs

        b = browser_tabs()
        out.append(("Chrome CDP", bool(b.get("ok")), f"вкладок: {len(b.get('tabs', []))}" if b.get("ok") else "нет флага --remote-debugging-port=9222"))
    except Exception as e:
        out.append(("Chrome CDP", False, str(e)))
    try:
        from .config import SAFETY_VERSION

        cfg = load_config()
        safety = cfg.get("safety", {}) or {}
        ver_ok = safety.get("version") == SAFETY_VERSION
        n_cmd = len(safety.get("deny_cmd", []))
        n_path = len(safety.get("deny_paths", []))
        fresh = ver_ok and n_cmd >= 30 and n_path >= 20
        out.append(("deny-листы", fresh,
                    f"safety.version={safety.get('version')} cmd={n_cmd} paths={n_path}"
                    + ("" if fresh else " — устарели, удали safety из конфига для обновления")))
    except Exception as e:
        out.append(("deny-листы", False, str(e)))
    try:
        if is_frozen():
            dst = Path(install_dir())
            legacy = sorted(p.name for p in dst.iterdir() if p.is_file() and (
                p.name.lower() == "aipc.exe"
                or (p.name.startswith("AiPC_Win_") and p.name.lower().endswith(".exe")
                    and p.name != exe_filename())))
            if legacy:
                out.append(("старые копии", False, f"конфликт: {', '.join(legacy)}"))
            else:
                out.append(("старые копии", True, "конфликтов нет"))
    except Exception:
        pass
    try:
        log = config_dir() / "audit.log"
        out.append(("audit.log", True, f"{log.stat().st_size // 1024} КБ" if log.exists() else "пусто"))
    except Exception:
        pass
    try:
        import shutil

        free = shutil.disk_usage(str(Path.home()))[2] // 1073741824
        out.append(("диск", free > 1, f"свободно {free} ГБ"))
    except Exception:
        pass
    return out
