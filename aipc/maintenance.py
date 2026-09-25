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


def check_update(repo: str = "S1sTeam/AiPC") -> dict:
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
        exe = next((a for a in assets if a["name"] and a["name"].lower().endswith(".exe")), None)
        if parse_version(tag) > parse_version(cur):
            return {"ok": True, "update": True, "current": cur, "latest": tag,
                    "url": data.get("html_url"), "exe_url": exe["url"] if exe else None,
                    "notes": str(data.get("body", ""))[:2000]}
        return {"ok": True, "update": False, "current": cur, "latest": tag or cur}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def self_update(repo: str = "S1sTeam/AiPC") -> int:
    """Скачать свежий exe и запустить его самоустановку (с UAC). Текущий процесс выходит."""
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
    print(f"Качаю {info.get('latest')} ...")
    tmp = Path(tempfile.gettempdir()) / f"aipc-update-{info.get('latest', 'new')}.exe"
    try:
        req = Request(url, headers={"User-Agent": "AiPC-updater"})
        with urlopen(req, timeout=600) as r, tmp.open("wb") as f:
            while True:
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
        print(f"Скачано: {tmp} ({tmp.stat().st_size // 1048576} МБ)")
    except Exception as e:
        print(f"Не скачать: {e}")
        return 1
    # Новый файл сам себя ставит (с UAC) — текущий процесс больше не нужен
    try:
        if os.name == "nt":
            subprocess.Popen([str(tmp), "--self-install"])
        else:
            subprocess.Popen([sys.executable, str(tmp), "--self-install"])
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

    pid_file = config_dir() / "aipc.pid"
    try:
        if not pid_file.exists():
            return {"ok": True, "note": "Core не запущен (нет PID-файла)"}
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
        except ValueError:
            pid_file.unlink(missing_ok=True)
            return {"ok": True, "note": "Битый PID-файл удален"}
        if not _pid_is_ours(pid):
            pid_file.unlink(missing_ok=True)
            return {"ok": True, "note": f"PID {pid} уже не наш (файл очищен), чужое не тронуто"}
        if sys.platform == "win32":
            subprocess.run(f"taskkill /PID {pid} /F", shell=True, capture_output=True)
        else:
            try:
                os.kill(pid, 15)
            except ProcessLookupError:
                pass
        pid_file.unlink(missing_ok=True)
        return {"ok": True, "note": f"Процесс {pid} остановлен"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


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
    from .installer import current_exe, install_dir, installed_exe, is_admin, is_frozen, is_installed

    out: list[tuple[str, bool, str]] = []
    out.append(("python", True, sys.version.split()[0]))
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

        for name, path, only_if in ide_config_paths():
            if only_if is not None and not only_if.exists():
                continue
            if not path.exists():
                out.append((f"IDE {name}", False, "конфиг не найден"))
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8") or "{}")
                entry = (data.get("mcpServers") or {}).get("aipc")
                if not entry:
                    out.append((f"IDE {name}", False, "нет записи aipc"))
                elif not Path(str(entry.get("command", ""))).exists() and str(entry.get("command", "")).lower() != "aipc":
                    out.append((f"IDE {name}", False, f"exe не найден: {entry.get('command')}"))
                else:
                    out.append((f"IDE {name}", True, "aipc прописан"))
            except Exception as e:
                out.append((f"IDE {name}", False, f"битый JSON: {e}"))
    except Exception as e:
        out.append(("IDE", False, str(e)))
    try:
        from .browser import browser_tabs

        b = browser_tabs()
        out.append(("Chrome CDP", bool(b.get("ok")), f"вкладок: {len(b.get('tabs', []))}" if b.get("ok") else "нет флага --remote-debugging-port=9222"))
    except Exception as e:
        out.append(("Chrome CDP", False, str(e)))
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
