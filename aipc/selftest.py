"""Самопроверка: экран -> мышь(pyautogui наличие) -> терминал -> конфиг -> MCP-импорт."""
from __future__ import annotations


def run_selftest() -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    # 1. rich/меню
    try:
        import rich  # noqa

        results.append(("меню rich", True, "ok"))
    except ImportError as e:
        results.append(("меню rich", False, str(e)))

    # 2. скрин (только импорт, сам захват может не работать в RDP/headless)
    try:
        import mss  # noqa
        from PIL import Image  # noqa

        results.append(("скриншоты mss+pillow", True, "ok"))
    except ImportError as e:
        results.append(("скриншоты mss+pillow", False, f"pip install mss pillow ({e})"))

    # 3. мышь
    try:
        import pyautogui  # noqa

        results.append(("мышь/клава pyautogui", True, "ok"))
    except ImportError as e:
        results.append(("мышь/клава pyautogui", False, f"pip install pyautogui ({e})"))

    # 4. терминал
    from .os_ops import run_cmd

    r = run_cmd("echo aipc-ok")
    results.append(("терминал run_cmd", bool(r.get("ok")), str(r.get("output", r.get("error")))[:100]))

    # 5. конфиг
    try:
        from .config import ensure_default_config

        p = ensure_default_config()
        results.append(("конфиг", True, str(p)))
    except Exception as e:
        results.append(("конфиг", False, str(e)))

    # 6. MCP
    try:
        import mcp  # noqa

        results.append(("MCP-сервер", True, "ok"))
    except ImportError as e:
        results.append(("MCP-сервер", False, f"pip install mcp ({e})"))

    # 7. браузер CDP (не критично если закрыт)
    from .browser import browser_tabs

    b = browser_tabs()
    if b.get("ok"):
        results.append(("браузер CDP", True, f"вкладок: {len(b.get('tabs', []))}"))
    else:
        results.append(("браузер CDP", False, "Chrome без --remote-debugging-port=9222 (см. Настроить)"))

    return results


def show_selftest() -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.align import Align
    from .logo import MENU_WIDTH, THEME, MARK_OK, MARK_ERR, safe_mark

    try:
        from .menu import _ensure_utf8

        _ensure_utf8()
    except Exception:
        pass

    console = Console(highlight=False, legacy_windows=False)
    ok_m, err_m = safe_mark(MARK_OK), safe_mark(MARK_ERR)
    results = run_selftest()
    table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    table.add_column("check")
    table.add_column("res")
    ok_all = True
    for name, ok, note in results:
        ok_all = ok_all and ok
        mark = ok_m if ok else err_m
        style = THEME["ok"] if ok else THEME["err"]
        table.add_row(name, f"[{style}]{mark} {note}[/{style}]")
    title = " Проверка: ВСЕ ОК " if ok_all else " Проверка: есть замечания "
    console.print(Align.center(Panel(table, title=title, width=MENU_WIDTH, border_style="green" if ok_all else "yellow")))
    input("\nEnter чтобы вернуться... ")
