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


def _menu_log(event: str) -> None:
    """Журнал меню для диагностики: какая клавиша пришла и что вернули."""
    try:
        import datetime
        from pathlib import Path

        p = Path.home() / ".aipc" / "menu.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()[-200:] if p.exists() else []
        lines.append(f"{ts} | {event}")
        p.write_text("\n".join(lines[-200:]) + "\n", encoding="utf-8")
    except Exception:
        pass


def _read_key_wide() -> str:
    """Блокирующее чтение клавиши через getwch (юникод сразу, без кодовых страниц).

    Тот же механизм что в старом рабочем меню: блокирующий вызов, никаких kbhit.
    """
    import msvcrt

    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):
        ch2 = msvcrt.getwch()
        return {"H": "up", "P": "down", "K": "up", "M": "down"}.get(ch2, "unknown")
    if ch == "\r":
        return "enter"
    if ch == "\x1b":
        return "esc"
    if ch == "\x03":
        return "quit"
    s = ch.lower()
    if s in ("w", "ц", "k"):
        return "up"
    if s in ("s", "ы", "j"):
        return "down"
    if s in ("q", "й"):
        return "quit"
    if s.isdigit() and s != "0":
        return s
    return "unknown"


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
    if s in ("q", "й"):
        return "quit"
    if s.isdigit() and s != "0":
        return s
    return "unknown"


DANGER_KEYS = frozenset({"stop", "exit", "kill"})
PULSE_MARKS = ["▶", "»", "›"]


def _gradient(text: str, c1=(34, 197, 94), c2=(134, 239, 172)) -> "Text":
    """Градиент посимвольно (rich из коробки градиент в Text не умеет)."""
    from rich.text import Text

    out = Text()
    n = max(1, len(text) - 1)
    for i, ch in enumerate(text):
        t = i / n
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        out.append(ch, style=f"bold #{r:02x}{g:02x}{b:02x}")
    return out


def _status_part() -> str:
    """mode • версия • число tools. Всё с защитой — никогда не роняет меню."""
    try:
        from .config import load_config

        mode = str(load_config().get("mode", "ask"))
    except Exception:
        mode = "ask"
    try:
        from . import __version__ as _ver
    except Exception:
        _ver = "?"
    tools = "59"
    try:
        import json
        from pathlib import Path

        tj = Path(__file__).resolve().parent.parent / "tools.json"
        if tj.exists():
            tools = str(len(json.loads(tj.read_text(encoding="utf-8")).get("tools", [])))
    except Exception:
        pass
    return f"{mode} • v{_ver} • {tools} tools"


def build_menu_panel(title: str, items: List[MenuItem], selected: int,
                     footer: str, frame: int = 0, flash: bool = False,
                     show_title: bool = True):
    """Чистая сборка панели (без console) — тестируемо, правая стенка всегда ровная."""
    from rich.align import Align
    from rich.console import Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    mark = PULSE_MARKS[frame % len(PULSE_MARKS)]
    table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    table.add_column("menu", overflow="ellipsis")
    for i, it in enumerate(items):
        danger = it.key in DANGER_KEYS
        if i == selected:
            if flash:
                row = Text(f"  {it.label}  ", style="bold black on white")
            elif danger:
                row = Text(f"{mark} {it.label}", style=f"bold {THEME['selected_fg']} on red")
            else:
                row = Text(f"{mark} {it.label}", style=f"bold {THEME['selected_fg']} on {THEME['selected_bg']}")
        else:
            bullet = Text("● ", style="red" if danger else THEME["accent"])
            row = Text.assemble(bullet, (it.label, THEME["normal_fg"]))
        table.add_row(row)
    rule = Text("─" * 44, style="dim")
    if show_title:
        body = Group(Align.center(_gradient(title)), Align.center(rule), table)
    else:
        body = table
    return Panel(body, subtitle=f" {footer} ", width=MENU_WIDTH,
                 border_style=THEME["border"], padding=(1, 1))


def _logo_width() -> int:
    try:
        return max(len(line) for line in LOGO_BLOCK.splitlines() if line.strip())
    except Exception:
        return 50


def build_screen(title: str, items: List[MenuItem], selected: int, footer: str,
                 dot: str, frame: int = 0, flash: bool = False, show_title: bool = True):
    """Весь экран меню одним объектом — для Live (без мерцания) и для печати."""
    from rich.align import Align
    from rich.console import Group
    from rich.text import Text

    logo = Text(LOGO_BLOCK, style=THEME["logo"])
    # SYSIK сдвигаем вправо: стартуем чуть правее центра логотипа
    sub = Text(" " * (_logo_width() // 2 + 2) + LOGO_SUB, style=THEME["logo_sub"])
    counter = Text(f"Пункт {selected + 1}/{len(items)} {dot} 1-{len(items)} быстрый выбор", style="dim")
    return Group(Align.center(logo), Align.center(sub), Text(""),
                 Align.center(build_menu_panel(title, items, selected, footer, frame, flash, show_title)),
                 Align.center(counter))


def splash(console, duration: float = 0.45) -> None:
    """Быстрый сплэш с градиентом. Любая клавиша пропускает (байты возвращаем в буфер)."""
    import time as _time

    from rich.align import Align

    steps = 6
    t0 = _time.monotonic()
    for s in range(steps + 1):
        if os.name == "nt":
            try:
                import msvcrt

                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    if ch in (b"\x00", b"\xe0"):
                        ch2 = msvcrt.getch()
                        msvcrt.ungetch(ch2)
                    msvcrt.ungetch(ch)
                    break
            except Exception:
                pass
        frac = s / steps
        bar = "█" * int(frac * 30) + "░" * (30 - int(frac * 30))
        console.clear()
        console.print(Align.center(_gradient("AiPC от Sysik")))
        console.print(Align.center(f"[green]{bar}[/green]"))
        if _time.monotonic() - t0 >= duration:
            break
        _time.sleep(duration / steps)


def run_menu(title: str, items: List[MenuItem], hint: Optional[str] = None,
             splash_first: bool = False, show_title: bool = True) -> int | str:
    """Рисует меню шириной MENU_WIDTH через rich.Panel. Возвращает index или 'quit'.

    show_title=False убирает дубль-заголовок из панели (для главного меню с лого).
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
    dot = safe_mark("•")
    footer = hint or f"W/S + стрелки {dot} Enter выбор {dot} Q выход  |  {_status_part()}"

    def render(frame: int = 0, flash: bool = False):
        console.print(build_screen(title, items, selected, footer, dot, frame, flash, show_title))

    if splash_first:
        splash(console)

    if os.name != "nt":
        return _posix_menu_loop(console, render, items, footer)

    import time as _time

    from rich.live import Live

    def show(f: int = 0, flash: bool = False) -> None:
        try:
            # refresh=True обязателен: update() сам НЕ перерисовывает,
            # а auto_refresh выключен против мерцания
            live.update(build_screen(title, items, selected, footer, dot, f, flash, show_title), refresh=True)
        except Exception:
            pass

    def flash_select() -> None:
        show(0, flash=True)
        _time.sleep(0.12)

    # Один поток: блокирующий getwch + перерисовка только по нажатию.
    # Никаких фоновых потоков — Live дергаем только отсюда: гонок,
    # мерцания и съеденных клавиш нет. Ввод как в старом меню.
    try:
        with Live(build_screen(title, items, selected, footer, dot, 0, show_title=show_title),
                  console=console, screen=True, auto_refresh=False) as live:
            while True:
                try:
                    key = _read_key_wide()
                except (OSError, EOFError, KeyboardInterrupt) as e:
                    _menu_log(f"input-error {type(e).__name__}")
                    return _fallback_numeric_menu(title, items)
                _menu_log(f"key={key!r} selected={selected} title={title[:30]}")
                if key == "up":
                    selected = (selected - 1) % len(items)
                    show(0)
                elif key == "down":
                    selected = (selected + 1) % len(items)
                    show(0)
                elif key == "enter":
                    flash_select()
                    _menu_log(f"return idx={selected}")
                    return selected
                elif key in ("esc", "quit"):
                    _menu_log("return quit")
                    return "quit"
                elif key.isdigit():
                    n = int(key)
                    if 1 <= n <= len(items):
                        selected = n - 1
                        flash_select()
                        _menu_log(f"return digit={n - 1}")
                        return n - 1
                # unknown — игнорим
    except Exception:
        return _fallback_numeric_menu(title, items)


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
