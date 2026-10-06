"""Аварийный стоп (kill switch): мгновенная блокировка всех инструментов.

Механизм двухслойный:
1. Файл `~/.aipc/panic` — сервер проверяет его в `_wrap` ПЕРВЫМ делом.
   Есть файл — все tools отвечают denied. Убрать может только человек
   (`aipc panic --off`), модель — никогда.
2. Глобальная горячая клавиша Ctrl+Alt+Shift+K — создаёт panic-файл из
   любого места Windows (поток с RegisterHotKey, best-effort).
"""
from __future__ import annotations

import threading

# Ctrl+Alt+Shift+K: случайно не нажать, осознанно — легко.
HOTKEY_MOD = 0x0002 | 0x0001 | 0x0004  # CONTROL | ALT | SHIFT
HOTKEY_VK = 0x4B  # K
HOTKEY_ID = 41710

_watcher_started = False


def panic_path():
    from .config import config_dir

    return config_dir() / "panic"


def is_set() -> bool:
    try:
        return panic_path().exists()
    except Exception:
        return False


def panic_reason() -> str:
    try:
        p = panic_path()
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace").strip()[:300]
    except Exception:
        pass
    return ""


def set_panic(reason: str = "ручная остановка") -> None:
    try:
        panic_path().write_text(reason[:300], encoding="utf-8")
    except Exception:
        pass


def clear_panic() -> bool:
    try:
        p = panic_path()
        if p.exists():
            p.unlink()
            return True
        return False
    except Exception:
        return False


def _watcher_loop() -> None:
    """Поток хоткея: RegisterHotKey + GetMessage. Только Windows."""
    try:
        import ctypes

        user32 = ctypes.windll.user32
        if not user32.RegisterHotKey(None, HOTKEY_ID, HOTKEY_MOD, HOTKEY_VK):
            return  # уже занят (второй процесс) — тихо выходим
        try:
            from ctypes import wintypes

            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312:  # WM_HOTKEY
                    set_panic("горячая клавиша Ctrl+Alt+Shift+K")
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            try:
                user32.UnregisterHotKey(None, HOTKEY_ID)
            except Exception:
                pass
    except Exception:
        pass


def start_watcher() -> bool:
    """Запустить поток хоткея (однократно на процесс, best-effort)."""
    global _watcher_started
    if _watcher_started:
        return True
    _watcher_started = True
    try:
        import os

        if os.name != "nt":
            return False
        t = threading.Thread(target=_watcher_loop, daemon=True)
        t.start()
        return True
    except Exception:
        return False
