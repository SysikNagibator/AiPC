"""Аудит каждого вызова tool. С ротацией чтобы лог не рос бесконечно."""
from __future__ import annotations

import datetime
from .config import config_dir

MAX_LOG_BYTES = 2 * 1024 * 1024


def _rotate(p) -> None:
    try:
        if p.exists() and p.stat().st_size > MAX_LOG_BYTES:
            bak = p.with_suffix(".log.bak")
            if bak.exists():
                bak.unlink()
            p.rename(bak)
    except Exception:
        pass


def tail_log(n: int = 20, max_bytes: int = 65536) -> list[str]:
    """Хвост audit.log для отладки агента."""
    try:
        p = config_dir() / "audit.log"
        if not p.exists():
            return []
        with p.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            tail = f.read().decode("utf-8", errors="replace")
        return tail.splitlines()[-max(1, n):]
    except Exception:
        return []


def log_event(tool: str, params: dict, ok: bool = True, note: str = "") -> None:
    try:
        p = config_dir() / "audit.log"
        _rotate(p)
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        with p.open("a", encoding="utf-8") as f:
            f.write(f"{ts} | {tool} | ok={ok} | {params} | {note}\n")
    except Exception:
        pass
