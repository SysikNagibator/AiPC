"""Движок меню AiPC: W/S + стрелки + Enter. Ровные рамки только через rich.Panel."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Callable, List, Optional

from .logo import (
    LOGO_BLOCK, LOGO_SUB, MENU_WIDTH, MARK_SELECTED,
    THEME, safe_mark,
)


def _enable_windows_ansi() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong(0)
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass
    try:
        os.system("")
    except Exception:
        pass


def _ensure_utf8() -> None:
    # Реально переключаем кодовую страницу процесса (os.system chcp влияет только на дочерний shell)
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass
        try:
            os.system("chcp 65001 >nul 2>&1")
        except Exception:
            pass


@dataclass
class MenuItem:
    label: str
    key: str  # идентификатор действия


def _console_encoding() -> str:
    """Кодовая страница ввода консоли (русская cmd обычно cp866, не cp1251)."""
    try:
        import ctypes

        cp = ctypes.windll.kernel32.GetConsoleCP()
        if cp:
            return f"cp{cp}"
    except Exception:
        pass
    return "cp866"


def _read_key_windows() -> str:
    """Возвращает символический код: up/down/enter/esc/quit/1-9/unknown."""
    import msvcrt

    ch = msvcrt.getch()
    # Стрелки: префикс 0x00 или 0xE0
    if ch in (b"\x00", b"\xe0"):
        ch2 = msvcrt.getch()
        if ch2 == b"H":
            return "up"
        if ch2 == b"P":
            return "down"
        if ch2 == b"K":
            return "up"
        if ch2 == b"M":
            return "down"
        return "unknown"
    if ch == b"\r":
        return "enter"
    if ch == b"\x1b":
        return "esc"
    if ch == b"\x03":
        return "quit"
    s = ""
    for enc in (_console_encoding(), "cp1251", "utf-8"):
        try:
            s = ch.decode(enc, errors="strict").lower()
            if s:
                break
        except Exception:
            continue
    if not s:
        return "unknown"
    if s in ("w", "ц"):
        return "up"
    if s in ("s", "ы"):
        return "down"
    if s in ("q", "й", "e", "у"):
        return "quit"
    if s.isdigit() and s != "0":
        return s
    return "unknown"


def run_menu(title: str, items: List[MenuItem], hint: Optional[str] = None) -> int | str:
    """Рисует меню шириной MENU_WIDTH через rich.Panel. Возвращает index или 'quit'.

    Никаких ручных '│' + пробелы — только Panel/Table, иначе правая стенка едет.
    """
    _ensure_utf8()
    _enable_windows_ansi()

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        from rich.align import Align
    except ImportError:
        return _fallback_numeric_menu(title, items)

    # Не TTY (перенаправление, IDE-терминал без интерактива) — цифровой fallback
    if not sys.stdin.isatty():
        return _fallback_numeric_menu(title, items)

    console = Console(highlight=False, legacy_windows=False, color_system="truecolor")
    selected = 0
    footer = hint or f"W/S + стрелки {safe_mark('•')} Enter выбор {safe_mark('•')} Q выход"
    sel_mark = safe_mark(MARK_SELECTED)

    def render():
        # Лого отдельно, без рамки — оно не влияет на ровность бокса
        logo = Text(LOGO_BLOCK, style=THEME["logo"])
        sub = Text(LOGO_SUB, style=THEME["logo_sub"])
        console.clear()
        console.print(Align.center(logo))
        console.print(Align.center(sub))
        console.print()

        table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
        table.add_column("menu", overflow="ellipsis")
        for i, it in enumerate(items):
            if i == selected:
                row = Text(f"{sel_mark} {it.label}", style=f"bold {THEME['selected_fg']} on {THEME['selected_bg']}")
            else:
                row = Text(f"  {it.label}", style=THEME["normal_fg"])
            table.add_row(row)

        panel = Panel(
            table,
            title=f" {title} ",
            subtitle=f" {footer} ",
            width=MENU_WIDTH,
            border_style=THEME["border"],
            padding=(1, 0),
        )
        console.print(Align.center(panel))
        console.print(f"[dim]Пункт {selected + 1}/{len(items)} • 1-{len(items)} быстрый выбор[/dim]", justify="center")

    if os.name != "nt":
        return _posix_menu_loop(console, render, items, footer)

    import msvcrt

    render()
    while True:
        try:
            # скрываем курсор на время навигации
            pass
        except Exception:
            pass
        key = _read_key_windows()
        if key == "up":
            selected = (selected - 1) % len(items)
            render()
        elif key == "down":
            selected = (selected + 1) % len(items)
            render()
        elif key == "enter":
            return selected
        elif key in ("esc", "quit"):
            return "quit"
        elif key.isdigit():
            n = int(key)
            if 1 <= n <= len(items):
                return n - 1
        # unknown — перерисовать не нужно


def _posix_menu_loop(console, render, items: List[MenuItem], footer: str):
    import termios
    import tty

    selected = 0
    render()

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                nxt = sys.stdin.read(1)
                if nxt == "[":
                    nxt2 = sys.stdin.read(1)
                    if nxt2 == "A":
                        selected = (selected - 1) % len(items)
                        render()
                    elif nxt2 == "B":
                        selected = (selected + 1) % len(items)
                        render()
                else:
                    return "quit"
            elif ch in ("w", "W", "k", "K"):
                selected = (selected - 1) % len(items)
                render()
            elif ch in ("s", "S", "j", "J"):
                selected = (selected + 1) % len(items)
                render()
            elif ch == "\r" or ch == "\n":
                return selected
            elif ch in ("q", "Q"):
                return "quit"
            elif ch.isdigit() and ch != "0":
                n = int(ch)
                if 1 <= n <= len(items):
                    return n - 1
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _fallback_numeric_menu(title: str, items: List[MenuItem]):
    print(f"=== {title} ===")
    print(LOGO_BLOCK)
    print(LOGO_SUB)
    print()
    for i, it in enumerate(items, 1):
        print(f"  {i}. {it.label}")
    print("  Q. Выход")
    try:
        ans = input("Введи номер> ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "quit"
    if ans in ("q", "й", "0", ""):
        return "quit"
    try:
        n = int(ans)
        if 1 <= n <= len(items):
            return n - 1
    except ValueError:
        pass
    return 0
