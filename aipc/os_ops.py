"""OS: файлы, терминал, процессы. С джейлом через policy."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .policy import check_cmd_allowed, check_path_allowed


def fs_list(path: str) -> dict:
    ok, err = check_path_allowed(path)
    if not ok:
        return {"ok": False, "error": err}
    try:
        p = Path(path).expanduser()
        items = [{"name": x.name, "is_dir": x.is_dir()} for x in p.iterdir()]
        return {"ok": True, "path": str(p), "items": items[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def fs_read(path: str, limit: int = 20000) -> dict:
    ok, err = check_path_allowed(path)
    if not ok:
        return {"ok": False, "error": err}
    try:
        data = Path(path).expanduser().read_text(encoding="utf-8", errors="replace")
        return {"ok": True, "text": data[:limit]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def fs_write(path: str, text: str) -> dict:
    ok, err = check_path_allowed(path)
    if not ok:
        return {"ok": False, "error": err}
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return {"ok": True, "path": str(p)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _decode_output(data: bytes) -> str:
    """Каскад кодировок: cmd.exe пишет в OEM (cp866), PowerShell в utf-8/cp1251."""
    for enc in ("utf-8", "cp866", "cp1251"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def run_cmd(cmd: str, cwd: str | None = None, timeout: int = 60) -> dict:
    ok, err = check_cmd_allowed(cmd)
    if not ok:
        return {"ok": False, "error": err}
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd or None, capture_output=True, text=False, timeout=timeout)
        out = _decode_output(r.stdout or b"")
        err_text = _decode_output(r.stderr or b"")
        if err_text:
            out += "\n" + err_text
        return {"ok": r.returncode == 0, "code": r.returncode, "output": out[-20000:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout {timeout}s"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def process_list(limit: int = 50) -> dict:
    try:
        import psutil  # type: ignore
    except ImportError:
        return {"ok": False, "error": "нет psutil. pip install psutil"}
    try:
        procs = [{"pid": p.info.get("pid"), "name": p.info.get("name")} for p in psutil.process_iter(["pid", "name"])]
        return {"ok": True, "processes": procs[:limit]}
    except Exception as e:
        return {"ok": False, "error": str(e)}
