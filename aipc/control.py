"""Control: мышь, клавиатура, запуск приложений."""
from __future__ import annotations

import os
import subprocess
import sys
import time


def _rel_to_abs(x: int, y: int) -> tuple[int, int]:
    """Модель шлет 0-1000 относительные. Конвертим в пиксели."""
    if 0 <= x <= 1000 and 0 <= y <= 1000:
        try:
            import pyautogui  # type: ignore
            sw, sh = pyautogui.size()
            return int(x / 1000 * sw), int(y / 1000 * sh)
        except Exception:
            pass
    return x, y


def mouse_move(x: int, y: int) -> dict:
    try:
        import pyautogui  # type: ignore
    except ImportError:
        return {"ok": False, "error": "нет pyautogui. pip install pyautogui"}
    try:
        ax, ay = _rel_to_abs(x, y)
        pyautogui.moveTo(ax, ay, duration=0.15)
        return {"ok": True, "x": ax, "y": ay}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mouse_click(x: int, y: int, button: str = "left") -> dict:
    try:
        import pyautogui  # type: ignore
    except ImportError:
        return {"ok": False, "error": "нет pyautogui"}
    try:
        ax, ay = _rel_to_abs(x, y)
        pyautogui.click(ax, ay, button=button)
        time.sleep(0.3)
        return {"ok": True, "x": ax, "y": ay, "button": button}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mouse_drag(x1: int, y1: int, x2: int, y2: int) -> dict:
    try:
        import pyautogui  # type: ignore
    except ImportError:
        return {"ok": False, "error": "нет pyautogui"}
    try:
        ax1, ay1 = _rel_to_abs(x1, y1)
        ax2, ay2 = _rel_to_abs(x2, y2)
        pyautogui.moveTo(ax1, ay1, duration=0.1)
        pyautogui.dragTo(ax2, ay2, duration=0.4, button="left")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def scroll(dy: int = -500) -> dict:
    try:
        import pyautogui  # type: ignore
        pyautogui.scroll(dy)
        return {"ok": True, "dy": dy}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _type_via_clipboard(text: str) -> bool:
    """Печать любого юникода (кириллица!) через буфер обмена + Ctrl+V. Только Windows."""
    import os as _os

    if _os.name != "nt":
        return False
    try:
        import ctypes

        GMEM_MOVEABLE = 0x0002
        CF_UNICODETEXT = 13
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        data = text + "\0"
        buf = ctypes.create_unicode_buffer(data)
        size = ctypes.sizeof(buf)
        hmem = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
        if not hmem:
            return False
        lock = kernel32.GlobalLock(hmem)
        ctypes.memmove(lock, buf, size)
        kernel32.GlobalUnlock(hmem)
        if not user32.OpenClipboard(None):
            kernel32.GlobalFree(hmem)
            return False
        try:
            user32.EmptyClipboard()
            user32.SetClipboardData(CF_UNICODETEXT, hmem)
        finally:
            user32.CloseClipboard()
        import pyautogui  # type: ignore

        pyautogui.hotkey("ctrl", "v")
        return True
    except Exception:
        return False


def type_text(text: str) -> dict:
    try:
        import pyautogui  # type: ignore
    except ImportError:
        return {"ok": False, "error": "нет pyautogui. pip install pyautogui"}
    try:
        if text.isascii():
            pyautogui.typewrite(text, interval=0.01)
        else:
            # pyautogui не умеет не-ASCII (кириллицу роняет) — идем через буфер
            if not _type_via_clipboard(text):
                return {"ok": False, "error": "не получилось вставить не-ASCII текст"}
        return {"ok": True, "len": len(text)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


_KEY_ALIASES = {"control": "ctrl", "ctl": "ctrl", "del": "delete", "esc": "escape", "return": "enter"}


def press_key(keys: list) -> dict:
    """keys напр. ['ctrl','t'] или ['enter']."""
    try:
        import pyautogui  # type: ignore
    except ImportError:
        return {"ok": False, "error": "нет pyautogui. pip install pyautogui"}
    try:
        if not keys:
            return {"ok": False, "error": "пустой список клавиш"}
        norm = [_KEY_ALIASES.get(str(k).lower(), str(k).lower()) for k in keys]
        if len(norm) == 1:
            pyautogui.press(norm[0])
        else:
            pyautogui.hotkey(*norm)
        return {"ok": True, "keys": norm}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def open_app(name_or_path: str) -> dict:
    """notepad/calc/chrome/путь к exe."""
    try:
        if os.name == "nt":
            if os.path.exists(name_or_path):
                os.startfile(name_or_path)  # type: ignore[attr-defined]
                return {"ok": True, "app": name_or_path}
            # через start чтобы сработали алиасы Windows
            subprocess.Popen(f'start "" "{name_or_path}"', shell=True)
            return {"ok": True, "app": name_or_path}
        # Linux/macOS
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.Popen([opener, name_or_path])
        return {"ok": True, "app": name_or_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}
