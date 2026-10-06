"""Платформенный слой AiPC (этап 5): швы под win32/macos/linux.

Статус: Windows 10/11 — полная поддержка. macOS/Linux — каркас:
часть чтения (скриншоты через mss) работает везде, ввод/окна/UIA —
только Windows (см. docs/PLATFORM.md). Бейдж платформ не меняем,
пока не заработает реально.
"""
from __future__ import annotations

import os
import sys


def name() -> str:
    """win32 | darwin | linux | ..."""
    if os.name == "nt":
        return "win32"
    return sys.platform


def is_windows() -> bool:
    return os.name == "nt"


# Матрица возможностей: tool-группа -> платформы.
# read-only и vision-чтение — первые кандидаты на posix.
CAPABILITIES: dict[str, dict[str, str]] = {
    "screen_capture": {"win32": "ok", "darwin": "ok", "linux": "ok-x11"},
    "files_terminal": {"win32": "ok", "darwin": "partial", "linux": "partial"},
    "mouse_keyboard": {"win32": "ok", "darwin": "blocked-permissions", "linux": "blocked-wayland"},
    "windows_uia": {"win32": "ok", "darwin": "no", "linux": "no"},
    "browser_cdp": {"win32": "ok", "darwin": "ok", "linux": "ok"},
    "audio_loopback": {"win32": "ok", "darwin": "no", "linux": "no"},
    "installer_path": {"win32": "ok", "darwin": "no", "linux": "no"},
}


def capability(group: str) -> str:
    """Статус группы на текущей платформе: ok/partial/ok-x11/.../no."""
    return CAPABILITIES.get(group, {}).get(name(), "no")


def require(group: str) -> tuple[bool, str]:
    """Гейт для платформенно-зависимых tools. Возвращает (ok, reason)."""
    st = capability(group)
    if st in ("ok", "ok-x11", "partial"):
        return True, ""
    why = {"no": "только Windows", "blocked-wayland": "нужен X11",
           "blocked-permissions": "нужны права доступности"}.get(st, st)
    return False, f"не поддерживается на {name()}: {why} (см. docs/PLATFORM.md)"


def backend(kind: str):
    """Бэкенд шва (screen/input/apps) под текущую ОС."""
    if is_windows():
        from . import win32 as _b
    else:
        from . import posix as _b
    return _b.backend(kind)
