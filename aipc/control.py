"""Control: мышь, клавиатура, запуск приложений."""
from __future__ import annotations

import os
import subprocess
import sys
import time


def _rel_to_abs(x: int, y: int) -> tuple[int, int]:
    """Модель шлет 0-1000 относительные. Конвертим в пиксели.

    Нижняя граница 2px: ровно (0,0) у pyautogui включает FAILSAFE-аварийку.
    """
    def clamp(v: int, limit: int) -> int:
        try:
            v = int(v)
        except (TypeError, ValueError):
            v = 0
        return max(2, min(v, limit))

    if 0 <= x <= 1000 and 0 <= y <= 1000:
        try:
            import pyautogui  # type: ignore
            sw, sh = pyautogui.size()
            return clamp(int(x / 1000 * sw), sw), clamp(int(y / 1000 * sh), sh)
        except Exception:
            pass
    return x, y


def mouse_move(x: int, y: int) -> dict:
    try:
        import pyautogui  # type: ignore
    except Exception:
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
    except Exception:
        return {"ok": False, "error": "нет pyautogui"}
    btn = str(button or "left").lower()
    if btn not in ("left", "middle", "right"):
        return {"ok": False, "reason": "bad_arg", "error": f"button только left/middle/right, дали: {button!r}"}
    try:
        ax, ay = _rel_to_abs(x, y)
        pyautogui.click(ax, ay, button=btn)
        time.sleep(0.3)
        return {"ok": True, "x": ax, "y": ay, "button": btn}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mouse_drag(x1: int, y1: int, x2: int, y2: int, modifier: str = "") -> dict:
    """Драг 0-1000. modifier: ctrl/shift/alt — держать во время драга."""
    try:
        import pyautogui  # type: ignore
    except Exception:
        return {"ok": False, "error": "нет pyautogui"}
    try:
        ax1, ay1 = _rel_to_abs(x1, y1)
        ax2, ay2 = _rel_to_abs(x2, y2)
        mod = _KEY_ALIASES.get(modifier.lower(), modifier.lower()) if modifier else ""
        if mod:
            pyautogui.keyDown(mod)
        try:
            pyautogui.moveTo(ax1, ay1, duration=0.1)
            pyautogui.dragTo(ax2, ay2, duration=0.4, button="left")
        finally:
            if mod:
                try:
                    pyautogui.keyUp(mod)
                except Exception:
                    pass
        return {"ok": True, "modifier": mod or None}
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
    kernel32.GlobalSize.argtypes = [ctypes.c_void_p]
    kernel32.GlobalSize.restype = ctypes.c_size_t
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    user32.GetClipboardData.restype = ctypes.c_void_p
    return kernel32, user32


def _keyboard_layout() -> int:
    """LANGID активной раскладки (0x409 = US English). 0 = не определили."""
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        tid = user32.GetWindowThreadProcessId(hwnd, None)
        return user32.GetKeyboardLayout(tid) & 0xFFFF
    except Exception:
        return 0


def _posix_clipboard_cmds():
    """Команды буфера обмена на macOS/Linux: (запись, чтение) или (None, None)."""
    import shutil
    import sys as _sys

    if _sys.platform == "darwin":
        return (["pbcopy"], ["pbpaste"])
    if shutil.which("xclip"):
        return (["xclip", "-selection", "clipboard"],
                ["xclip", "-selection", "clipboard", "-o"])
    if shutil.which("xsel"):
        return (["xsel", "--clipboard", "--input"],
                ["xsel", "--clipboard", "--output"])
    return (None, None)


def _set_clipboard(text: str, retries: int = 5) -> bool:
    """Положить юникод-текст в буфер обмена Windows. С ретраями (буфер часто занят)."""
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
        import time as _time

        for _ in range(max(1, retries)):
            if user32.OpenClipboard(None):
                break
            _time.sleep(0.12)
        else:
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


def clipboard_set(text: str) -> dict:
    """Положить текст в буфер обмена."""
    import os as _os

    if _os.name != "nt":
        import subprocess as _sp

        set_cmd, _ = _posix_clipboard_cmds()
        if not set_cmd:
            from .errors import err
            return err("not_supported", "нет xclip/xsel (Linux) для буфера обмена",
                       hint="установи: sudo apt install xclip")
        try:
            _sp.run(set_cmd, input=str(text).encode("utf-8"),
                    timeout=10, check=True)
            return {"ok": True, "len": len(text)}
        except Exception as e:
            from .errors import err
            return err("error", f"буфер недоступен: {e}")
    if _set_clipboard(text):
        return {"ok": True, "len": len(text)}
    return {"ok": False, "error": "буфер недоступен (только Windows)"}


def clipboard_get() -> dict:
    """Прочитать текст из буфера обмена."""
    import os as _os

    if _os.name != "nt":
        import subprocess as _sp

        _, get_cmd = _posix_clipboard_cmds()
        if not get_cmd:
            from .errors import err
            return err("not_supported", "нет xclip/xsel (Linux) для буфера обмена",
                       hint="установи: sudo apt install xclip")
        try:
            r = _sp.run(get_cmd, capture_output=True, timeout=10, check=True)
            return {"ok": True,
                    "text": r.stdout.decode("utf-8", errors="replace")}
        except Exception as e:
            from .errors import err
            return err("error", f"буфер недоступен: {e}")
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
            return {"ok": True, "text": text or ""}
        finally:
            user32.CloseClipboard()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def clipboard_set_image(image_b64: str) -> dict:
    """Положить картинку (PNG base64) в буфер обмена."""
    import os as _os

    if _os.name != "nt":
        return {"ok": False, "reason": "error", "error": "только Windows"}
    try:
        import base64
        import ctypes
        import io

        from PIL import Image  # type: ignore

        kernel32, user32 = _clipboard_procs()
        img = Image.open(io.BytesIO(base64.b64decode(image_b64))).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="BMP")
        dib = buf.getvalue()[14:]  # DIB без BMP-заголовка
        hmem = kernel32.GlobalAlloc(0x0002, len(dib))
        if not hmem:
            return {"ok": False, "reason": "error", "error": "нет памяти"}
        lock = kernel32.GlobalLock(hmem)
        if not lock:
            kernel32.GlobalFree(hmem)
            return {"ok": False, "reason": "error", "error": "lock failed"}
        ctypes.memmove(lock, dib, len(dib))
        kernel32.GlobalUnlock(hmem)
        if not user32.OpenClipboard(None):
            kernel32.GlobalFree(hmem)
            return {"ok": False, "reason": "error", "error": "буфер занят"}
        try:
            user32.EmptyClipboard()
            if not user32.SetClipboardData(8, hmem):  # CF_DIB
                kernel32.GlobalFree(hmem)
                return {"ok": False, "reason": "error", "error": "set failed"}
        finally:
            user32.CloseClipboard()
        return {"ok": True, "size": [img.width, img.height]}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def clipboard_get_image(max_width: int = 1280) -> dict:
    """Забрать картинку из буфера обмена -> PNG base64."""
    import os as _os

    if _os.name != "nt":
        return {"ok": False, "reason": "error", "error": "только Windows"}
    try:
        import base64
        import ctypes
        import io
        import struct

        from PIL import Image  # type: ignore

        kernel32, user32 = _clipboard_procs()
        if not user32.OpenClipboard(None):
            return {"ok": False, "reason": "error", "error": "буфер занят"}
        try:
            hmem = user32.GetClipboardData(8)  # CF_DIB
            if not hmem:
                return {"ok": True, "image_b64": None, "note": "в буфере нет картинки"}
            lock = kernel32.GlobalLock(hmem)
            if not lock:
                return {"ok": False, "reason": "error", "error": "lock failed"}
            try:
                size = kernel32.GlobalSize(hmem)
                dib = ctypes.string_at(lock, size)
            finally:
                kernel32.GlobalUnlock(hmem)
        finally:
            user32.CloseClipboard()
        # DIB -> BMP: собираем заголовок
        bf_size = 14 + len(dib)
        bmp = struct.pack("<2sIHHI", b"BM", bf_size, 0, 0, 14) + dib
        img = Image.open(io.BytesIO(bmp)).convert("RGB")
        if img.width > max_width:
            img = img.resize((max_width, int(img.height * max_width / img.width)))
        out = io.BytesIO()
        img.save(out, format="PNG")
        return {"ok": True, "image_b64": base64.b64encode(out.getvalue()).decode("ascii"),
                "size": [img.width, img.height]}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def sleep(seconds: float = 1.0) -> dict:
    """Пауза чтобы дождаться загрузки. Без верхнего лимита, но долгие паузы вешают вызов."""
    try:
        s = max(0.1, float(seconds))
    except (TypeError, ValueError):
        return {"ok": False, "error": "seconds числом"}
    import time as _time

    _time.sleep(s)
    return {"ok": True, "slept": s}


TYPE_FAST_LIMIT = 200
TYPE_CHUNK = 8000


def type_text(text: str) -> dict:
    """Печать текста без лимита размера. Маленький ASCII — посимвольно, всё остальное — кусками через буфер."""
    try:
        import time as _time

        import pyautogui  # type: ignore
    except Exception:
        return {"ok": False, "reason": "missing_dep", "error": "нет pyautogui. pip install pyautogui"}
    if not text:
        return {"ok": False, "reason": "bad_arg", "error": "пустой текст"}
    try:
        # Посимвольно печатаем ТОЛЬКО маленький ASCII на US-раскладке Windows:
        # typewrite шлёт символы через физические клавиши — на русской
        # раскладке "ABC" превратилось бы в "ФИС". Иначе — вставка через буфер.
        import os as _os2

        layout_us = (_os2.name != "nt") or (_keyboard_layout() in (0x409,))
        if text.isascii() and len(text) <= TYPE_FAST_LIMIT and layout_us:
            pyautogui.typewrite(text, interval=0.01)
            return {"ok": True, "len": len(text), "method": "keys"}
        # Кусками через буфер: быстро и держит любой юникод
        try:
            orig = clipboard_get().get("text", "")
        except Exception:
            orig = ""
        typed = 0
        for i in range(0, len(text), TYPE_CHUNK):
            chunk = text[i:i + TYPE_CHUNK]
            if not _set_clipboard(chunk):
                return {"ok": False, "reason": "error", "error": "буфер недоступен", "typed": typed}
            pyautogui.hotkey("ctrl", "v")
            typed += len(chunk)
            _time.sleep(0.3)
        try:
            if orig:
                _set_clipboard(orig)
        except Exception:
            pass
        return {"ok": True, "len": typed, "method": "paste", "chunks": (len(text) + TYPE_CHUNK - 1) // TYPE_CHUNK}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


_KEY_ALIASES = {"control": "ctrl", "ctl": "ctrl", "del": "delete", "esc": "escape", "return": "enter"}


def press_key(keys: list) -> dict:
    """keys напр. ['ctrl','t'] или ['enter']."""
    try:
        import pyautogui  # type: ignore
    except Exception:
        return {"ok": False, "error": "нет pyautogui. pip install pyautogui"}
    try:
        if not keys:
            return {"ok": False, "error": "пустой список клавиш"}
        norm = [_KEY_ALIASES.get(str(k).lower(), str(k).lower()) for k in keys]
        if len(norm) == 1:
            pyautogui.press(norm[0])
            return {"ok": True, "keys": norm}
        # Вручную вместо hotkey(): если средняя клавиша невалидна,
        # hotkey() роняет исключение с зажатыми модами (Ctrl залипает навсегда).
        held: list = []
        try:
            for k in norm[:-1]:
                pyautogui.keyDown(k)
                held.append(k)
            pyautogui.press(norm[-1])
        finally:
            for k in reversed(held):
                try:
                    pyautogui.keyUp(k)
                except Exception:
                    pass
        return {"ok": True, "keys": norm}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def key_down(key: str) -> dict:
    """Зажать клавишу (shift-выделение, игры, хоткеи). Пару закрывает key_up."""
    try:
        import pyautogui  # type: ignore
    except Exception:
        return {"ok": False, "reason": "missing_dep", "error": "нет pyautogui"}
    try:
        k = _KEY_ALIASES.get(key.lower(), key.lower())
        pyautogui.keyDown(k)
        return {"ok": True, "key": k, "held": True}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def key_up(key: str) -> dict:
    """Отпустить клавишу, зажатую через key_down."""
    try:
        import pyautogui  # type: ignore
    except Exception:
        return {"ok": False, "reason": "missing_dep", "error": "нет pyautogui"}
    try:
        k = _KEY_ALIASES.get(key.lower(), key.lower())
        pyautogui.keyUp(k)
        return {"ok": True, "key": k, "held": False}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def mouse_right_click(x: int, y: int) -> dict:
    """Правый клик (контекстное меню). Координаты 0-1000."""
    return mouse_click(x, y, "right")


def mouse_middle_click(x: int, y: int) -> dict:
    """Средний клик. Координаты 0-1000."""
    return mouse_click(x, y, "middle")


def mouse_double_click(x: int, y: int) -> dict:
    """Двойной клик. Координаты 0-1000."""
    try:
        import pyautogui  # type: ignore
    except Exception:
        return {"ok": False, "reason": "missing_dep", "error": "нет pyautogui. pip install pyautogui"}
    try:
        ax, ay = _rel_to_abs(x, y)
        pyautogui.doubleClick(ax, ay)
        import time as _time

        _time.sleep(0.3)
        return {"ok": True, "x": ax, "y": ay}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def focus_type(title_substr: str, text: str, timeout: float = 8.0) -> dict:
    """Атомарно: фокус + ПРОВЕРКА + печать. Фокус не встал — не печатаю вообще.

    Убирает целый класс багов «напечатал не туда»: печать идёт только
    в проверенное foreground-окно.
    """
    from .vision import get_active_window, window_focus

    f = window_focus(title_substr, timeout=timeout, verify=True)
    if not f.get("ok"):
        return {"ok": False, "reason": f.get("reason", "not_focused"),
                "error": f"не печатаю: {f.get('error')}", "focus": f}
    # Фокус мог уплыть за миллисекунды между проверкой и печатью — перепроверяем
    try:
        fg = (get_active_window().get("title") or "")
        if title_substr.lower() not in fg.lower():
            return {"ok": False, "reason": "not_focused",
                    "error": f"фокус уплыл перед печатью, впереди: {fg[:80]!r}", "focus": f}
    except Exception:
        pass
    t = type_text(text)
    t["focus_title"] = f.get("title")
    if not t.get("ok"):
        t["focus"] = f
    return t


def open_app(name_or_path: str) -> dict:
    """notepad/calc/chrome/путь к exe. Метасимволы shell вычищаем (инъекция невозможна)."""
    safe = "".join(c for c in str(name_or_path) if c not in '"`$;&|<>^%')
    if not safe.strip():
        return {"ok": False, "reason": "bad_arg", "error": "пустое имя"}
    try:
        from .platform import backend

        backend("apps").open(safe)
        return {"ok": True, "app": safe}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mouse_position() -> dict:
    """Где сейчас курсор: пиксели + 0-1000."""
    try:
        import pyautogui  # type: ignore
    except Exception:
        return {"ok": False, "reason": "missing_dep", "error": "нет pyautogui"}
    try:
        import mss  # type: ignore

        mx, my = pyautogui.position()
        sw, sh = pyautogui.size()
        return {"ok": True, "pixels": [mx, my],
                "rel": [int(mx / sw * 1000), int(my / sh * 1000)]}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}
