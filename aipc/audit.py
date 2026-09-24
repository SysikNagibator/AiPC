"""Аудит каждого вызова tool."""
from __future__ import annotations

import datetime
from .config import config_dir


def log_event(tool: str, params: dict, ok: bool = True, note: str = "") -> None:
    try:
        p = config_dir() / "audit.log"
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        with p.open("a", encoding="utf-8") as f:
            f.write(f"{ts} | {tool} | ok={ok} | {params} | {note}\n")
    except Exception:
        pass
