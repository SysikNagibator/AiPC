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


def log_event(tool: str, params: dict, ok: bool = True, note: str = "") -> None:
    try:
        p = config_dir() / "audit.log"
        _rotate(p)
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        with p.open("a", encoding="utf-8") as f:
            f.write(f"{ts} | {tool} | ok={ok} | {params} | {note}\n")
    except Exception:
        pass
