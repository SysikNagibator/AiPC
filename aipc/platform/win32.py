"""Реализация швов для Windows 10/11 (полная)."""
from __future__ import annotations

import os
import subprocess
import sys

from .base import AppBackend, InputBackend, ScreenBackend


class WinScreen(ScreenBackend):
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


class WinInput(InputBackend):
    def move_click(self, x: int, y: int, button: str = "left") -> None:
        import pyautogui  # type: ignore

        pyautogui.click(x, y, button=button)

    def type_text(self, text: str) -> None:
        import pyautogui  # type: ignore

        pyautogui.typewrite(text)


class WinApps(AppBackend):
    def open(self, target: str) -> None:
        if os.path.exists(target):
            os.startfile(target)  # type: ignore[attr-defined]
            return
        subprocess.Popen(f'start "" "{target}"', shell=True)

    def active_title(self) -> str:
        try:
            from ..vision import get_active_window

            res = get_active_window()
            return str(res.get("title", "") or "") if isinstance(res, dict) else ""
        except Exception:
            return ""


def backend(kind: str):
    return {"screen": WinScreen, "input": WinInput, "apps": WinApps}[kind]()
