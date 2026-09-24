"""Уведомления человеку: всплывающее окно Windows + лог. Без эмодзи."""
from __future__ import annotations

import os
import threading


def _win_popup(text: str, title: str = "AiPC от Sysik") -> bool:
    if os.name != "nt":
        return False
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, title, 0x40)  # MB_ICONINFORMATION
        return True
    except Exception:
        return False


def notify_user(text: str) -> dict:
    """Показать сообщение, не блокируя агента. Всегда пишет в audit.log."""
    from .audit import log_event

    log_event("notify_user", {"text": text[:300]}, ok=True)
    t = threading.Thread(target=_win_popup, args=(text,), daemon=True)
    try:
        t.start()
    except Exception:
        pass
    return {"ok": True, "shown": text[:300], "popup": os.name == "nt"}


def ask_user(question: str, timeout: int = 0) -> dict:
    """Вопрос человеку с кнопками Да/Нет/Отмена. Блокирует пока не ответит.

    Для режима ask: модель реально ждет решения человека.
    timeout пока резерв (0 = ждать вечно).
    """
    from .audit import log_event

    if os.name != "nt":
        log_event("ask_user", {"question": question[:300]}, ok=False, note="только Windows")
        return {"ok": False, "error": "ask_user работает только на Windows", "answer": "cancel"}
    try:
        import ctypes

        # MB_YESNOCANCEL | MB_ICONQUESTION | MB_SYSTEMMODAL
        res = ctypes.windll.user32.MessageBoxW(None, question, "AiPC: требуется решение", 0x03 | 0x20 | 0x1000)
        mapping = {6: "yes", 7: "no", 2: "cancel"}
        answer = mapping.get(res, "cancel")
        log_event("ask_user", {"question": question[:300]}, ok=True, note=f"answer={answer}")
        return {"ok": True, "answer": answer}
    except Exception as e:
        return {"ok": False, "error": str(e), "answer": "cancel"}
