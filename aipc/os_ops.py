"""OS: файлы, терминал, процессы. С джейлом через policy."""
from __future__ import annotations
from .errors import denied

import subprocess
from pathlib import Path

from .policy import check_cmd_allowed, check_path_allowed, load_mode


def check_free_space(path: str, need_bytes: int = 0, reserve_mb: int = 500) -> tuple[bool, str]:
    """Есть ли место на диске (need + резерв). Не смогли проверить — не блокируем."""
    try:
        import shutil

        anchor = Path(path).expanduser()
        while not anchor.exists():
            parent = anchor.parent
            if parent == anchor:
                break
            anchor = parent
        free = shutil.disk_usage(str(anchor)).free
        if free < need_bytes + reserve_mb * 1048576:
            return False, f"мало места: свободно {free // 1048576} МБ, надо {(need_bytes // 1048576) + reserve_mb}"
        return True, ""
    except Exception:
        return True, ""


def fs_list(path: str) -> dict:
    ok, err = check_path_allowed(path)
    if not ok:
        return denied(err, "выбери путь вне запретных (safety.deny_paths в ~/.aipc/config.yaml)")
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return {"ok": False, "reason": "not_found", "error": f"нет пути: {path}"}
        items = [{"name": x.name, "is_dir": x.is_dir()} for x in p.iterdir()]
        return {"ok": True, "path": str(p), "items": items[:2000]}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def fs_read(path: str, limit: int = 20000, offset: int = 0) -> dict:
    ok, err = check_path_allowed(path)
    if not ok:
        return denied(err, "выбери путь вне запретных (safety.deny_paths в ~/.aipc/config.yaml)")
    try:
        raw = Path(path).expanduser().read_bytes()
        if b"\x00" in raw[:8000]:
            return {"ok": False, "reason": "binary",
                    "error": f"бинарный файл ({len(raw)} байт), текст не читаю"}
        data = raw.decode("utf-8", errors="replace")
        off = max(0, offset)
        from .audit import mask_secrets

        chunk = mask_secrets(data[off:off + max(100, limit)])
        return {"ok": True, "text": chunk, "size": len(data), "offset": off}
    except FileNotFoundError:
        return {"ok": False, "reason": "not_found", "error": f"нет файла: {path}"}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def fs_write(path: str, text: str, backup: bool = False) -> dict:
    ok, err = check_path_allowed(path)
    if not ok:
        return denied(err, "выбери путь вне запретных (safety.deny_paths в ~/.aipc/config.yaml)")
    if load_mode() == "read-only":
        return denied("read-only режим: запись запрещена", "переключи режим: меню → Настроить → Режим")
    try:
        import os as _os
        import tempfile as _tf

        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        bak = None
        if backup and p.exists():
            bak = str(p) + ".bak"
            Path(bak).write_bytes(p.read_bytes())
        # Атомарно: временный файл + replace
        fd, tmp = _tf.mkstemp(dir=str(p.parent), prefix=".aipc-")
        try:
            with _os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            Path(tmp).replace(p)
        except BaseException:
            try:
                Path(tmp).unlink(missing_ok=True)
            except Exception:
                pass
            raise
        return {"ok": True, "path": str(p), "backup": bak}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def fs_stat(path: str) -> dict:
    ok, err = check_path_allowed(path)
    if not ok:
        return denied(err, "выбери путь вне запретных (safety.deny_paths в ~/.aipc/config.yaml)")
    try:
        import datetime as _dt

        p = Path(path).expanduser()
        if not p.exists():
            return {"ok": False, "reason": "not_found", "error": f"нет пути: {path}"}
        st = p.stat()
        return {"ok": True, "path": str(p), "is_dir": p.is_dir(), "size": st.st_size,
                "mtime": _dt.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def fs_mkdir(path: str) -> dict:
    ok, err = check_path_allowed(path)
    if not ok:
        return denied(err, "выбери путь вне запретных (safety.deny_paths в ~/.aipc/config.yaml)")
    if load_mode() == "read-only":
        return denied("read-only режим: создание запрещено", "переключи режим: меню → Настроить → Режим")
    try:
        p = Path(path).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(p)}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def fs_delete(path: str, recursive: bool = False) -> dict:
    """Удалить файл/пустую папку. Непустую папку — только recursive=true."""
    ok, err = check_path_allowed(path)
    if not ok:
        return denied(err, "выбери путь вне запретных (safety.deny_paths в ~/.aipc/config.yaml)")
    if load_mode() == "read-only":
        return denied("read-only режим: удаление запрещено", "переключи режим: меню → Настроить → Режим")
    try:
        import shutil as _sh

        p = Path(path).expanduser()
        if not p.exists():
            return {"ok": False, "reason": "not_found", "error": f"нет пути: {path}"}
        try:
            rp = p.resolve()
            import os as _os2

            protected = {Path(rp.anchor), Path.home().resolve(), Path(_os2.environ.get("SystemRoot", r"C:\Windows")).resolve()}
            if rp in protected:
                return denied("корень диска / дом / Windows не удаляю", "укажи конкретный файл или папку, а не корень")
        except Exception:
            pass
        if p.is_dir():
            items = list(p.iterdir())
            if items and not recursive:
                return {"ok": False, "reason": "not_empty",
                        "error": f"папка не пуста ({len(items)}), нужен recursive=true"}
            _sh.rmtree(p) if items else p.rmdir()
        else:
            p.unlink()
        return {"ok": True, "deleted": str(p)}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def fs_move(src: str, dst: str) -> dict:
    """Переместить/переименовать."""
    for path in (src, dst):
        ok, err = check_path_allowed(path)
        if not ok:
            return denied(err, "выбери путь вне запретных (safety.deny_paths в ~/.aipc/config.yaml)")
    if load_mode() == "read-only":
        return denied("read-only режим: перемещение запрещено", "переключи режим: меню → Настроить → Режим")
    try:
        s, d = Path(src).expanduser(), Path(dst).expanduser()
        if not s.exists():
            return {"ok": False, "reason": "not_found", "error": f"нет пути: {src}"}
        d.parent.mkdir(parents=True, exist_ok=True)
        s.replace(d)
        return {"ok": True, "src": str(s), "dst": str(d)}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def fs_find(pattern: str, path: str = ".", max_results: int = 50, max_seconds: int = 60) -> dict:
    """Рекурсивный поиск файлов по glob-паттерну. max_results/max_seconds — пагинация, не запрет."""
    ok, err = check_path_allowed(path)
    if not ok:
        return denied(err, "выбери путь вне запретных (safety.deny_paths в ~/.aipc/config.yaml)")
    try:
        import fnmatch as _fn
        import os as _os
        import time as _time

        base = Path(path).expanduser()
        if not base.is_dir():
            return {"ok": False, "reason": "not_found", "error": f"нет папки: {path}"}
        skip = {"$Recycle.Bin", "System Volume Information", "node_modules", ".git",
                "__pycache__", ".venv", "venv"}
        deadline = _time.monotonic() + max(3, max_seconds)
        limit = max(1, max_results)
        out: list[str] = []
        timed_out = False
        stack = [base]
        while stack:
            if _time.monotonic() > deadline:
                timed_out = True
                break
            cur = stack.pop()
            try:
                with _os.scandir(cur) as it:
                    entries = list(it)
            except OSError:
                continue
            for e in entries:
                try:
                    if e.name in skip:
                        continue
                    if e.is_dir(follow_symlinks=False):
                        stack.append(Path(e.path))
                    elif _fn.fnmatch(e.name, pattern):
                        out.append(e.path)
                        if len(out) >= limit:
                            break
                except OSError:
                    continue
            if len(out) >= limit:
                break
        return {"ok": True, "found": out, "count": len(out),
                "truncated": len(out) >= limit or timed_out, "timed_out": timed_out}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


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
        return denied(err, "убери запрещённый фрагмент или переформулируй команду")
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd or None, capture_output=True, text=False, timeout=timeout)
        stdout = _decode_output(r.stdout or b"")
        stderr = _decode_output(r.stderr or b"")
        return {"ok": r.returncode == 0, "code": r.returncode,
                "stdout": stdout[-50000:], "stderr": stderr[-20000:],
                "output": (stdout + (("\n" + stderr) if stderr else ""))[-50000:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "timeout", "error": f"timeout {timeout}s"}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def process_list(limit: int = 50) -> dict:
    try:
        import psutil  # type: ignore
    except ImportError:
        return {"ok": False, "reason": "missing_dep", "error": "нет psutil. pip install psutil"}
    try:
        procs = [{"pid": p.info.get("pid"), "name": p.info.get("name")} for p in psutil.process_iter(["pid", "name"])]
        return {"ok": True, "processes": procs[:limit]}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def process_find(name: str, limit: int = 20) -> dict:
    """Найти процессы по подстроке имени (вместо разбора всего списка)."""
    res = process_list(500)
    if not res.get("ok"):
        return res
    found = [p for p in res["processes"] if name.lower() in str(p.get("name") or "").lower()][:max(1, limit)]
    return {"ok": True, "found": found, "count": len(found)}


def wait_for_process(name: str, timeout: float = 30.0) -> dict:
    """Ждать появления процесса по имени."""
    import time as _time

    deadline = _time.monotonic() + max(1.0, timeout)
    while True:
        res = process_find(name, 5)
        if res.get("ok") and res.get("found"):
            return {"ok": True, "processes": res["found"]}
        if _time.monotonic() >= deadline:
            return {"ok": False, "reason": "timeout",
                    "error": f"процесс не появился за {timeout}с: {name}"}
        _time.sleep(1.0)
