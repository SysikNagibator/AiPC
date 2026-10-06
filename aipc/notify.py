"""Уведомления человеку: всплывающее окно Windows + лог. Без эмодзи."""
from __future__ import annotations

import os
import threading


def _win_popup(text: str, title: str = "AiPC от SYSIK") -> bool:
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


def _close_box_by_title(title: str) -> None:
    """Закрыть окно MessageBox по заголовку (сторожок таймаута)."""
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
    except Exception:
        pass


def _msgbox_yesno(text: str, title: str, deadline: float) -> str:
    """Один диалог Да/Нет с дедлайном. Возвращает yes/no/timeout."""
    import ctypes
    import time as _time

    answer = {"v": "timeout"}

    def _ask():
        try:
            # MB_YESNO | MB_ICONWARNING | MB_SYSTEMMODAL
            res = ctypes.windll.user32.MessageBoxW(None, text, title, 0x04 | 0x30 | 0x1000)
            answer["v"] = {6: "yes", 7: "no"}.get(res, "no")
        except Exception:
            answer["v"] = "no"

    t = threading.Thread(target=_ask, daemon=True)
    t.start()
    while True:
        left = deadline - _time.time()
        if left <= 0:
            break
        t.join(min(left, 0.2))
        if not t.is_alive():
            break
    if t.is_alive():
        _close_box_by_title(title)
        t.join(3)
        return "timeout"
    return answer["v"]


def _normalize_presets(presets=None, fallback: int = 10) -> list[int]:
    """Пресеты длительности запоминания (минуты): целые 1..1440, макс 3 кнопки."""
    try:
        from .policy import safety_cfg

        if presets is None:
            presets = safety_cfg().get("allow_presets", None)
    except Exception:
        pass
    if not presets:
        presets = [fallback]
    out: list[int] = []
    for p in presets:
        try:
            v = int(p)
        except (TypeError, ValueError):
            continue
        if 1 <= v <= 1440 and v not in out:
            out.append(v)
        if len(out) >= 3:
            break
    return out or [max(1, min(1440, int(fallback or 10)))]


def _fmt_mins(m: int) -> str:
    if m < 60:
        return f"{m} мин"
    h, rest = divmod(m, 60)
    return f"{h} ч" if not rest else f"{h} ч {rest} мин"


def _taskdialog_buttons(title: str, instruction: str, content: str,
                        labels: list[tuple[int, str]], deadline: float):
    """TaskDialog с произвольными кнопками. Возвращает id / 'timeout' / 'error'.

    labels: [(100, 'Только раз'), (101, '10 мин'), ...]. Закрытие крестиком = 2.
    """
    import ctypes
    import time as _time
    from ctypes import c_int, c_uint, c_void_p, c_wchar_p, pointer
    from ctypes.wintypes import MSG

    class _BTN(ctypes.Structure):
        _fields_ = [("nButtonID", c_int), ("pszButtonText", c_wchar_p)]

    class _CFG(ctypes.Structure):
        _fields_ = [
            ("cbSize", c_uint), ("hwndParent", c_void_p), ("hInstance", c_void_p),
            ("dwFlags", c_uint), ("dwCommonButtons", c_uint),
            ("pszWindowTitle", c_wchar_p), ("uMainIcon", c_void_p),
            ("pszMainInstruction", c_wchar_p), ("pszContent", c_wchar_p),
            ("cButtons", c_uint), ("pButtons", c_void_p),
            ("nDefaultButton", c_int), ("cRadioButtons", c_uint),
            ("pRadioButtons", c_void_p), ("nDefaultRadioButton", c_int),
            ("pszVerificationText", c_wchar_p), ("pszExpandedInformation", c_wchar_p),
            ("pszExpandedControlText", c_wchar_p), ("pszCollapsedControlText", c_wchar_p),
            ("uFooterIcon", c_void_p), ("pszFooter", c_wchar_p),
            ("pfCallback", c_void_p), ("lpCallbackData", c_void_p),
            ("cxWidth", c_uint),
        ]

    TDF_ALLOW_DIALOG_CANCELLATION = 0x08
    TD_WARNING_ICON = c_void_p(0xFFFF)
    out = {"v": "error"}
    btns = (_BTN * len(labels))()
    for i, (bid, text) in enumerate(labels):
        btns[i].nButtonID = bid
        btns[i].pszButtonText = text
    cfg = _CFG()
    cfg.cbSize = ctypes.sizeof(_CFG)
    cfg.dwFlags = TDF_ALLOW_DIALOG_CANCELLATION
    cfg.pszWindowTitle = title
    cfg.uMainIcon = TD_WARNING_ICON
    cfg.pszMainInstruction = instruction
    cfg.pszContent = content
    cfg.cButtons = len(labels)
    cfg.pButtons = ctypes.cast(btns, c_void_p)
    cfg.nDefaultButton = labels[0][0]
    nButton = c_int(0)

    def _ask():
        try:
            hr = ctypes.windll.comctl32.TaskDialogIndirect(
                ctypes.byref(cfg), ctypes.byref(nButton), None, None)
            out["v"] = nButton.value if hr == 0 else "error"
        except Exception:
            out["v"] = "error"

    import threading as _th

    t = _th.Thread(target=_ask, daemon=True)
    t.start()
    while True:
        left = deadline - _time.time()
        if left <= 0:
            break
        t.join(min(left, 0.2))
        if not t.is_alive():
            break
    if t.is_alive():
        _close_box_by_title(title)
        t.join(3)
        return "timeout"
    return out["v"]
def confirm_action(tool: str, summary: str, timeout: int = 120,
                   remember_minutes: int = 10, presets: list | None = None):
    """Серверное подтверждение опасного действия человеком — один диалог.

    Кнопки: «Только раз» + вариации времени из safety.allow_presets
    (по умолчанию [10, 60]) + «Запретить». Никаких «разрешить всё навсегда».
    Возвращает: "once", ("timed", minutes), "deny", "timeout".
    """
    from .audit import log_event

    title = "AiPC: разрешить действие?"
    if os.name != "nt":
        # macOS/Linux: GUI нет — спрашиваем в консоли, если она интерактивна.
        import time as _time2

        try:
            opts = _normalize_presets(presets, remember_minutes)
            return _console_pick(tool, summary,
                                 _time2.time() + max(10, timeout), opts)
        except Exception:
            log_event("confirm_action", {"tool": tool}, ok=False,
                      note="нет консоли")
            return "deny"
    try:
        import time as _time

        deadline = _time.time() + max(10, timeout)
        opts = _normalize_presets(presets, remember_minutes)
        labels = [(100, "Только раз")]
        labels += [(101 + i, _fmt_mins(m)) for i, m in enumerate(opts)]
        content = (f"Агент просит выполнить:\n\n{tool}\n{summary[:800]}\n\n"
                   "Выберите, на сколько разрешить. Тишина = запрет.")
        if _can_popup():
            try:
                picked = _taskdialog_buttons(title, "Разрешить действие?",
                                             content, labels, deadline)
            except Exception:
                picked = "error"
            if picked == "timeout":
                log_event("confirm_action", {"tool": tool}, ok=False,
                          note="decision=timeout")
                return "timeout"
            if picked == 100:
                decision = "once"
            elif isinstance(picked, int) and 101 <= picked < 101 + len(opts):
                decision = ("timed", opts[picked - 101])
            elif picked == "error":
                # TaskDialog недоступен — старый двухшаговый MessageBox
                decision = _confirm_legacy(tool, summary, title, deadline, opts)
                if decision == "timeout":
                    log_event("confirm_action", {"tool": tool}, ok=False,
                              note="decision=timeout")
                    return "timeout"
            else:
                log_event("confirm_action", {"tool": tool}, ok=False,
                          note="decision=deny")
                return "deny"
        else:
            decision = _console_pick(tool, summary, deadline, opts)
            if decision == "timeout":
                return "timeout"
            if decision == "deny":
                log_event("confirm_action", {"tool": tool}, ok=False,
                          note="decision=deny")
                return "deny"
        log_event("confirm_action", {"tool": tool}, ok=True,
                  note=f"decision={decision}")
        return decision
    except Exception as e:
        try:
            log_event("confirm_action", {"tool": tool}, ok=False, note=str(e)[:200])
        except Exception:
            pass
        return "deny"


def _confirm_legacy(tool: str, summary: str, title: str, deadline: float,
                    opts: list[int]):
    """Запасной двухшаговый MessageBox, если TaskDialog недоступен."""
    first = _msgbox_yesno(
        f"Агент просит выполнить:\n\n{tool}\n{summary[:800]}\n\n"
        "Да — выполнить один раз.\nНет — запретить.", title, deadline)
    if first != "yes":
        return "timeout" if first == "timeout" else "deny"
    mins = ", ".join(_fmt_mins(m) for m in opts)
    second = _msgbox_yesno(
        f"Запомнить это же действие ({mins})?\n\n{tool}\n{summary[:400]}\n\n"
        "Да — запомнить на первый срок, Нет — только раз.", title, deadline)
    if second == "timeout":
        return "timeout"
    return ("timed", opts[0]) if second == "yes" else "once"


def _console_pick(tool: str, summary: str, deadline: float,
                  opts: list[int]):
    """Консольный выбор без GUI: 1=раз, 2..=сроки, n=нет."""
    import sys
    import time as _time

    if not sys.stdin.isatty():
        return "deny"
    variants = " / ".join(["1=раз"] + [f"{i + 2}={_fmt_mins(m)}"
                                              for i, m in enumerate(opts)] + ["n=нет"])
    print(f"\n[AiPC] {tool}\n{summary[:800]}\nРазрешить? [{variants}]: ",
          end="", flush=True)
    answer = {"v": None}

    def _ask():
        try:
            answer["v"] = (input() or "").strip().lower()
        except Exception:
            answer["v"] = ""

    import threading as _th

    t = _th.Thread(target=_ask, daemon=True)
    t.start()
    while answer["v"] is None and _time.time() < deadline:
        t.join(0.2)
    if answer["v"] is None:
        print("\n[AiPC] нет ответа — запрет.")
        return "timeout"
    v = answer["v"]
    if v in ("1", "y", "yes", "д", "да", "раз"):
        return "once"
    if v.isdigit() and 2 <= int(v) <= 1 + len(opts):
        return ("timed", opts[int(v) - 2])
    return "deny"


def _can_popup() -> bool:
    if os.name != "nt":
        return False
    try:
        import ctypes

        return bool(ctypes.windll.user32.GetSystemMetrics(0))
    except Exception:
        return False


def _console_confirm(tool: str, summary: str, deadline: float,
                     default_no: bool = False) -> str:
    """Запасной вариант без GUI: вопрос в консоль с таймаутом."""
    import sys
    import time as _time

    if not sys.stdin.isatty():
        return "deny"
    print(f"\n[AiPC] {tool}\n{summary[:800]}\nРазрешить? [y/N]: ", end="", flush=True)
    answer = {"v": None}

    def _ask():
        try:
            answer["v"] = (input() or "").strip().lower()
        except Exception:
            answer["v"] = ""

    t = threading.Thread(target=_ask, daemon=True)
    t.start()
    while answer["v"] is None and _time.time() < deadline:
        t.join(0.2)
    v = (answer["v"] or "")
    if answer["v"] is None:
        print("\n[AiPC] нет ответа — запрет.")
        return "timeout"
    return "yes" if v in ("y", "yes", "д", "да") else "no"


def ask_user(question: str, timeout: int = 0) -> dict:
    """Вопрос человеку с кнопками Да/Нет/Отмена.

    timeout=0 — ждать вечно (осторожно: агент висит пока не ответят).
    timeout>0 — секунд ожидания, потом cancel чтобы не вешать агента.
    """
    from .audit import log_event

    if os.name != "nt":
        log_event("ask_user", {"question": question[:300]}, ok=False, note="только Windows")
        return {"ok": False, "error": "ask_user работает только на Windows", "answer": "cancel"}
    try:
        import ctypes

        answer = {"v": "cancel"}

        def _ask():
            try:
                # MB_YESNOCANCEL | MB_ICONQUESTION | MB_SYSTEMMODAL
                res = ctypes.windll.user32.MessageBoxW(None, question, "AiPC: требуется решение",
                                                       0x03 | 0x20 | 0x1000)
                answer["v"] = {6: "yes", 7: "no", 2: "cancel"}.get(res, "cancel")
            except Exception:
                pass

        t = threading.Thread(target=_ask, daemon=True)
        t.start()
        if timeout and timeout > 0:
            t.join(timeout)
            if t.is_alive():
                log_event("ask_user", {"question": question[:300]}, ok=True, note="answer=cancel (timeout)")
                return {"ok": True, "answer": "cancel", "note": f"нет ответа за {timeout}с"}
        else:
            t.join()
        log_event("ask_user", {"question": question[:300]}, ok=True, note=f"answer={answer['v']}")
        return {"ok": True, "answer": answer["v"]}
    except Exception as e:
        return {"ok": False, "error": str(e), "answer": "cancel"}
