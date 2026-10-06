"""Реализация швов для macOS/Linux (частичная, честная).

Работает: скриншоты (mss), открытие файлов/URL, базовый ввод через pyautogui
там, где ОС разрешает (X11; Wayland и macOS-песочница — нет, см. PLATFORM.md).
Окна/UIA (get_active_window, ui_snapshot) — только Windows.
"""
from __future__ import annotations

import subprocess
import sys

from .base import AppBackend, InputBackend, ScreenBackend


class PosixNotSupported(Exception):
    pass


class PosixScreen(ScreenBackend):
    def shot_monitor(self, monitor: int = 0):
        import mss  # type: ignore
        from PIL import Image

        with mss.mss() as sct:
            mon = sct.monitors[monitor + 1]
            shot = sct.grab(mon)
            return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    def monitors(self) -> list:
        import mss  # type: ignore

        with mss.mss() as sct:
            return [{"left": m["left"], "top": m["top"],
                     "width": m["width"], "height": m["height"]}
                    for m in sct.monitors[1:]]


class PosixInput(InputBackend):
    def move_click(self, x: int, y: int, button: str = "left") -> None:
        if sys.platform != "darwin" and not _has_x11():
            raise PosixNotSupported("ввод только под X11 (Wayland блокирует)")
        import pyautogui  # type: ignore

        pyautogui.click(x, y, button=button)

    def type_text(self, text: str) -> None:
        if sys.platform != "darwin" and not _has_x11():
            raise PosixNotSupported("ввод только под X11 (Wayland блокирует)")
        import pyautogui  # type: ignore

        pyautogui.typewrite(text)


def _has_x11() -> bool:
    import os

    return bool(os.environ.get("DISPLAY")) and not os.environ.get("WAYLAND_DISPLAY")


class PosixApps(AppBackend):
    def open(self, target: str) -> None:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.Popen([opener, target])

    def active_title(self) -> str:
        return ""  # нет кроссплатформенного способа без gros-зависимостей


def backend(kind: str):
    return {"screen": PosixScreen, "input": PosixInput, "apps": PosixApps}[kind]()
