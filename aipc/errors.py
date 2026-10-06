"""Единый формат ошибок: {"ok": false, "reason": ..., "error": ..., "hint"?}.

reason — машинный код (denied, denied_timeout, not_found, bad_arg, error,
rate_limited, loop_guard, missing_dep, ...). hint — что делать дальше.
"""
from __future__ import annotations


def err(reason: str, error: str, hint: str = "") -> dict:
    d: dict = {"ok": False, "reason": reason, "error": error}
    if hint:
        d["hint"] = hint
    return d


def denied(error: str, hint: str = "") -> dict:
    """Короткий конструктор запретов: reason=denied."""
    return err("denied", error, hint)
