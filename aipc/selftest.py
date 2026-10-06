"""Самопроверка: экран -> мышь(pyautogui наличие) -> терминал -> конфиг -> MCP-импорт."""
from __future__ import annotations


def run_selftest() -> list[tuple[str, bool, str]]:
    from .i18n import t

    results: list[tuple[str, bool, str]] = []

    # 1. rich/меню
    try:
        import rich  # noqa

        results.append((t("st.menu"), True, "ok"))
    except ImportError as e:
        results.append((t("st.menu"), False, str(e)))

    # 2. скрин (только импорт, сам захват может не работать в RDP/headless)
    try:
        import mss  # noqa
        from PIL import Image  # noqa

        results.append((t("st.shot"), True, "ok"))
    except Exception as e:
        results.append((t("st.shot"), False, f"pip install mss pillow ({e})"))

    # 3. мышь
    try:
        import pyautogui  # noqa

        results.append((t("st.mouse"), True, "ok"))
    except Exception as e:
        results.append((t("st.mouse"), False, f"pip install pyautogui ({e})"))

    # 4. терминал
    from .os_ops import run_cmd

    r = run_cmd("echo aipc-ok")
    results.append((t("st.term"), bool(r.get("ok")), str(r.get("output", r.get("error")))[:100]))

    # 5. конфиг
    try:
        from .config import ensure_default_config

        p = ensure_default_config()
        results.append((t("st.config"), True, str(p)))
    except Exception as e:
        results.append((t("st.config"), False, str(e)))

    # 6. MCP
    try:
        import mcp  # noqa

        results.append((t("st.mcp"), True, "ok"))
    except ImportError as e:
        results.append((t("st.mcp"), False, f"pip install mcp ({e})"))

    # 7. браузер CDP (не критично если закрыт)
    from .browser import browser_tabs

    b = browser_tabs()
    if b.get("ok"):
        results.append((t("st.browser"), True, t("st.tabs").format(n=len(b.get("tabs", [])))))
    else:
        results.append((t("st.browser"), False, t("st.browser.need")))

    # 8. опциональные зависимости tools (не критично, но режут фичи)
    for mod, key in [("uiautomation", "ui_snapshot (дерево)"), ("paramiko", "ssh/sftp"),
                     ("ddgs", "web_search_pc"), ("websocket", "browser_eval")]:
        try:
            __import__(mod)
            results.append((key, True, "ok"))
        except ImportError:
            results.append((key, False, f"pip install {mod}"))

    return results


def show_selftest() -> None:
    from .i18n import t
    from .logo import MARK_ERR, MARK_OK, safe_mark
    from .menu import pause, show_card

    try:
        from .menu import _ensure_utf8

        _ensure_utf8()
    except Exception:
        pass

    ok_m, err_m = safe_mark(MARK_OK), safe_mark(MARK_ERR)
    results = run_selftest()
    lines = []
    ok_all = True
    for name, ok, note in results:
        ok_all = all_ok and ok
        mark = ok_m if ok else err_m
        lines.append(f"{mark} {name}: {note}")
    title = t("st.title.ok") if ok_all else t("st.title.issues")
    show_card(title.strip(), "\n".join(lines),
              kind="ok" if ok_all else "warn")
    pause()
