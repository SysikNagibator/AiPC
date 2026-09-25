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


def _clipboard_procs():
    """user32/kernel32 с правильными прототипами (без argtypes хендлы режутся до 32 бит)."""
    import ctypes

    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    user32.GetClipboardData.restype = ctypes.c_void_p
    return kernel32, user32


def _set_clipboard(text: str) -> bool:
    """Положить юникод-текст в буфер обмена. Только Windows."""
    import os as _os

    if _os.name != "nt":
        return False
    try:
        import ctypes

        kernel32, user32 = _clipboard_procs()
        GMEM_MOVEABLE = 0x0002
        CF_UNICODETEXT = 13
        data = text + "\0"
        buf = ctypes.create_unicode_buffer(data)
        size = ctypes.sizeof(buf)
        hmem = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
        if not hmem:
            return False
        lock = kernel32.GlobalLock(hmem)
        if not lock:
            kernel32.GlobalFree(hmem)
            return False
        ctypes.memmove(lock, buf, size)
        kernel32.GlobalUnlock(hmem)
        if not user32.OpenClipboard(None):
            kernel32.GlobalFree(hmem)
            return False
        try:
            user32.EmptyClipboard()
            if not user32.SetClipboardData(CF_UNICODETEXT, hmem):
                kernel32.GlobalFree(hmem)
                return False
        finally:
            user32.CloseClipboard()
        return True
    except Exception:
        return False


def _type_via_clipboard(text: str) -> bool:
    """Печать любого юникода (кириллица!) через буфер обмена + Ctrl+V. Только Windows."""
    if not _set_clipboard(text):
        return False
    try:
        import pyautogui  # type: ignore

        pyautogui.hotkey("ctrl", "v")
        return True
    except Exception:
        return False


def clipboard_set(text: str) -> dict:
    """Положить текст в буфер обмена."""
    if _set_clipboard(text):
        return {"ok": True, "len": len(text)}
    return {"ok": False, "error": "буфер недоступен (только Windows)"}


def clipboard_get() -> dict:
    """Прочитать текст из буфера обмена."""
    import os as _os

    if _os.name != "nt":
        return {"ok": False, "error": "только Windows"}
    try:
        import ctypes

        CF_UNICODETEXT = 13
        kernel32, user32 = _clipboard_procs()
        if not user32.OpenClipboard(None):
            return {"ok": False, "error": "буфер занят"}
        try:
            hmem = user32.GetClipboardData(CF_UNICODETEXT)
            if not hmem:
                return {"ok": True, "text": ""}
            lock = kernel32.GlobalLock(hmem)
            try:
                text = ctypes.wstring_at(lock)
            finally:
                kernel32.GlobalUnlock(hmem)
            return {"ok": True, "text": (text or "")[:20000]}
        finally:
            user32.CloseClipboard()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def sleep(seconds: float = 1.0) -> dict:
    """Пауза чтобы дождаться загрузки (макс 30 сек)."""
    try:
        s = max(0.5, min(30.0, float(seconds)))
    except (TypeError, ValueError):
        return {"ok": False, "error": "seconds числом 0.5-30"}
    import time as _time

    _time.sleep(s)
    return {"ok": True, "slept": s}


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


def mouse_double_click(x: int, y: int) -> dict:
    """Двойной клик. Координаты 0-1000."""
    try:
        import pyautogui  # type: ignore
    except ImportError:
        return {"ok": False, "error": "нет pyautogui. pip install pyautogui"}
    try:
        ax, ay = _rel_to_abs(x, y)
        pyautogui.doubleClick(ax, ay)
        import time as _time

        _time.sleep(0.3)
        return {"ok": True, "x": ax, "y": ay}
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
