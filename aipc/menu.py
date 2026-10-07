"""Движок меню AiPC: W/S + стрелки + Enter. Ровные рамки только через rich.Panel."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Callable, List, Optional

from .logo import (
    LOGO_BLOCK, LOGO_SUB,
    THEME,
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
    hint: str = ""  # вторая строка пункта, dim-серым


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
        return {"H": "up", "P": "down", "K": "up", "M": "down",
                "G": "home", "O": "end"}.get(ch2, "unknown")
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
    if s in ("l", "д"):
        return "lang"
    if s.isdigit():
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
# === Новый движок меню: один Live, состояние в dataclass, бюджет ширины ===
from rich.cells import cell_len


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


def _logo_row(main: str, shadow_src: str, c1=(0, 200, 100), c2=(120, 255, 165),
              dim_style: str = "") -> "Text":
    """Строка пиксель-логотипа с дроп-тенью: глиф — градиент, а сдвинутая
    копия соседней строки — тусклым (как тень в pixel-арте). Направление
    сдвига задано самим shadow_src (вправо — " "+src, влево — src[1:]).
    Позиции градиента совпадают с _gradient, цвета старого лого не меняются."""
    from rich.text import Text

    out = Text()
    n = max(1, len(main) - 1)
    for i, ch in enumerate(main):
        sch = shadow_src[i] if i < len(shadow_src) else " "
        if ch != " ":
            t = i / n
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            out.append(ch, style=f"bold #{r:02x}{g:02x}{b:02x}")
        elif sch != " ":
            # Сплошной силуэт без пропусков: основной текст всегда поверх.
            out.append(sch, style=dim_style or None)
        else:
            out.append(" ", style=None)
    return out

# Палитры тем (hex, truecolor; rich сам даунгрейдит под 16 цветов).
from rich.cells import cell_len

THEMES = {
    "green": {
        "border": "#167A3C", "accent": "#3DDC84",
        "text": "#C9D1D9", "white": "#FFFFFF",
        "muted": "#96A09A", "dim": "#5B645F", "num": "#5B645F",
        "dot": "#3DDC84", "logo2": "#27A85D",
        "logo_c1": (0, 200, 100), "logo_c2": (120, 255, 165),
        "shadow": "#2f3645",
    },
    "mono": {
        "border": "#6E6E6E", "accent": "#E8E8E8",
        "text": "#C9D1D9", "white": "#FFFFFF",
        "muted": "#8A8A8A", "dim": "#5B5B5B", "num": "#5B5B5B",
        "dot": "#E8E8E8", "logo2": "#8A8A8A",
        "logo_c1": (200, 200, 200), "logo_c2": (255, 255, 255),
        "shadow": "#2f3645",
    },
    "amber": {
        "border": "#7A5200", "accent": "#FFB000",
        "text": "#E8DCC8", "white": "#FFFFFF",
        "muted": "#9A8A6A", "dim": "#5C5546", "num": "#5C5546",
        "dot": "#FFB000", "logo2": "#B07800",
        "logo_c1": (255, 176, 0), "logo_c2": (255, 220, 150),
        "shadow": "#2f3645",
    },
}

# Цвет режима по уровню риска (все темы).
MODE_COLORS = {"read-only": "#3DDC84", "ask": "#F9F1A5", "auto": "#FF9F43"}
DANGER_SEL = "#FF6B6B"

CONTENT_MAX = 76


@dataclass
class MenuState:
    """Всё состояние меню в одном месте. Отрисовка — чистая функция."""
    title: str
    items: List[MenuItem]
    groups: Optional[List[List[str]]]  # списки key по группам; None = подряд
    selected: int
    mode: str
    lang: str
    theme: str
    core_running: bool
    version: str
    no_color: bool
    ascii: bool
    cwd: str = ""
    center: bool = False
    tools: int = 0
    show_title: bool = True
    notice: str = ""


def _pal(state: MenuState, theme: str) -> dict:
    """Палитра темы с учётом NO_COLOR (цвета пустые, bold остаётся)."""
    base = dict(THEMES.get(theme or state.theme, THEMES["green"]))
    if state.no_color:
        for k in base:
            if k.startswith("logo_"):
                continue
            if isinstance(base[k], str) and base[k].startswith("#"):
                base[k] = ""
    return base


def _style(color: str, extra: str = "") -> str:
    if extra:
        return f"{extra} {color}".strip()
    return (color or "").strip()


def _glyph(state: MenuState, uni: str, ascii_alt: str) -> str:
    return ascii_alt if state.ascii else uni


def _ascii_clean(s: str) -> str:
    """Фолбэк пунктуации для ASCII-консолей."""
    for a, b in (("—", "-"), ("–", "-"), ("«", '"'), ("»", '"'),
                 ("“", '"'), ("”", '"'), ("…", "..."), ("·", "-")):
        s = s.replace(a, b)
    return s


def _cells(s: str) -> int:
    try:
        return cell_len(s)
    except Exception:
        return len(s)


def _cut(s: str, width: int, ascii_mode: bool = False) -> str:
    """Обрезать строку до ширины в клетках с … (... в ASCII) на конце."""
    if width <= 0:
        return ""
    if _cells(s) <= width:
        return s
    mark = "..." if ascii_mode else "…"
    out, w = "", 0
    for ch in s:
        cw = _cells(ch) or 1
        if w + cw > width - _cells(mark):
            break
        out += ch
        w += cw
    return out + mark


def _pad(s: str, width: int) -> str:
    w = _cells(s)
    return s if w >= width else s + " " * (width - w)


def display_numbers(items) -> list:
    """Номера пунктов: по порядку 1.., пункт exit всегда «0»."""
    out = []
    c = 1
    for it in items:
        if it.key == "exit":
            out.append("0")
        else:
            out.append(str(c))
            c += 1
    return out


def apply_key(selected: int, n: int, key: str, numbers=None):
    """Чистая навигация: (selected, n, key) -> (действие, значение).

    Возвращает ("move", idx) | ("select", idx) | ("quit", -1) | ("noop", selected).
    Цикличность через край включена. numbers — отображаемые номера (пункт exit
    обычно «0»); без него — классика 1..n.
    """
    if n <= 0:
        return ("quit", -1)
    if key == "up":
        return ("move", (selected - 1) % n)
    if key == "down":
        return ("move", (selected + 1) % n)
    if key == "home":
        return ("move", 0)
    if key == "end":
        return ("move", n - 1)
    if key == "enter":
        return ("select", selected)
    if key in ("esc", "quit"):
        return ("quit", -1)
    if key == "lang":
        return ("lang", selected)
    if len(key) == 1 and key.isdigit():
        if numbers is not None:
            for i, num in enumerate(numbers):
                if num == key and 0 <= i < n:
                    return ("select", i)
            return ("noop", selected)
        d = int(key)
        if 1 <= d <= n:
            return ("select", d - 1)
    return ("noop", selected)


def _jump_range(items) -> str:
    """Диапазон быстрого выбора: 1–8 если выход это 0, иначе 1–n."""
    nums = display_numbers(items)
    quick = [x for x in nums if x != "0"]
    if not quick:
        return ""
    return f"1–{len(quick)}"


def _tools_word(n: int, lang: str) -> str:
    """N tools с правильным склонением (EN/RU)."""
    from .i18n import EN, RU

    table = RU if lang == "ru" else EN
    if lang == "ru":
        m = abs(n) % 100
        d = m % 10
        if 11 <= m <= 14:
            w = table["tools.many"]
        elif d == 1:
            w = table["tools.one"]
        elif 2 <= d <= 4:
            w = table["tools.few"]
        else:
            w = table["tools.many"]
    else:
        w = table["tools.one"] if abs(n) == 1 else table["tools.many"]
    return f"{n} {w}"


def _mode_style(state: MenuState) -> str:
    if state.no_color:
        return ""
    return _style(f"bold {MODE_COLORS.get(state.mode, 'white')}")


def _header_card(state: MenuState, pal: dict, lang: str, inner: int):
    """Карточка шапки: лого + by SYSIK + слоган + статус. 3 строки контента."""
    from rich.console import Group
    from rich.panel import Panel
    from rich.text import Text
    import rich.box as _box

    from .i18n import t as _t
    from .logo import PIXEL_LOGO

    am = state.ascii
    nc = state.no_color
    acc = "" if nc else _style(f"bold {pal['accent']}")
    white_b = "bold" if nc else _style(f"bold {pal['white']}")
    dim = "" if nc else pal["dim"]
    muted = "" if nc else pal["muted"]
    ver = f"v{state.version}"

    lines = []
    if am:
        # ASCII: вместо логотипа одна строка «AiPC», затем слоган
        t1 = Text(no_wrap=True)
        t1.overflow = "crop"
        t1.append(_pad(_cut("AiPC", inner, am), inner), style=acc or None)
        slogan = _ascii_clean(_t("slogan", lang=lang))
        t2 = Text(_pad(_cut(slogan, inner, am), inner),
                  style=dim or None)
        lines = [t1, t2]
    else:
        l1, l2 = PIXEL_LOGO
        name = "by SYSIK"
        # строка 1: лого | 3 пробела | by SYSIK | паддинг | v1.1
        t1 = Text(no_wrap=True)
        t1.overflow = "crop"
        if nc:
            left = _cut(f"{l1}   by SYSIK", inner, am)
            room_nc = max(0, inner - _cells(ver))
            t1.append(_pad(left, room_nc), style=acc or None)
            t1.append(" " + ver if room_nc > _cells(left) else ver,
                      style=white_b or None)
        else:
            # строка 1: чистый градиент (тень от неё падает вниз-влево).
            g = _gradient(_cut(l1, inner, am), pal.get("logo_c1", (0, 200, 100)),
                          pal.get("logo_c2", (120, 255, 165)))
            t1.append(g)
            t1.append("   ", style=None)
            t1.append("by SYSIK", style=white_b or None)
            room = inner - _cells(ver)
            if _cells(t1.plain) < room:
                t1.append(" " * (room - _cells(t1.plain)))
            t1.append(ver, style=white_b or None)
        if _cells(t1.plain) > inner:
            t1 = Text(_cut(t1.plain, inner, am), no_wrap=True)
            t1.overflow = "crop"
        lines.append(t1)
        # строка 2: лого + слоган
        slogan = _t("slogan", lang=lang)
        t2 = Text(no_wrap=True)
        t2.overflow = "crop"
        if nc:
            t2.append(_pad(_cut(f"{l2}   {slogan}", inner, am), inner),
                      style=dim or None)
        else:
            # строка 2: глиф + жёсткая тень вниз-влево: тень — сдвинутая
            # на 1 клетку влево копия ПЕРВОЙ строки, лежит строго под текстом.
            main2 = _cut(l2, inner, am)
            sh1 = _cut(l1[1:] + " ", inner, am)
            t2.append(_logo_row(main2, sh1, pal.get("logo_c1", (0, 200, 100)),
                                pal.get("logo_c2", (120, 255, 165)),
                                pal.get("shadow") or pal["dim"]))
            t2.append("   ", style=None)
            t2.append(slogan, style=muted or None)
            tail = inner - _cells(t2.plain)
            if tail > 0:
                t2.append(" " * tail)
        if _cells(t2.plain) > inner:
            t2 = Text(_cut(t2.plain, inner, am), no_wrap=True)
            t2.overflow = "crop"
        lines.append(t2)
        if not nc:
            # строка 3: сплошной силуэт тени (копия второй строки, сдвиг
            # -1/+1), плоский цвет. Только в цветном режиме.
            sh2 = _cut(l2[1:] + " ", inner, am)
            t3 = Text(no_wrap=True)
            t3.overflow = "crop"
            sh_style = pal.get("shadow") or pal["dim"]
            for ch in sh2:
                t3.append(ch, style=sh_style if ch != " " else None)
            tail3 = inner - _cells(t3.plain)
            if tail3 > 0:
                t3.append(" " * tail3)
            if _cells(t3.plain) > inner:
                t3 = Text(_cut(t3.plain, inner, am), no_wrap=True)
                t3.overflow = "crop"
            lines.append(t3)
    # строка статуса
    dot = _glyph(state, "●", "*") if state.core_running else _glyph(state, "○", "o")
    word = _t("core.running", lang=lang) if state.core_running else _t("core.stopped", lang=lang)
    if nc:
        dw = ""
    elif state.core_running:
        dw = _style(f"bold {pal['dot']}")
    else:
        dw = muted
    st = Text(no_wrap=True)
    st.overflow = "crop"
    st.append("core ", style=dim or None)
    st.append(dot + " " + word, style=dw or None)
    st.append("   ", style=None)
    st.append(_t("hdr.mode", lang=lang), style=dim or None)
    st.append(" ", style=None)
    st.append(state.mode, style=_mode_style(state) or None)
    st.append("   ", style=None)
    st.append(_tools_word(state.tools, lang), style=None)
    if not nc:
        plain = st.plain
        tw = _tools_word(state.tools, lang)
        pos = plain.find(tw)
        if pos >= 0:
            num = str(state.tools)
            st.stylize(pal["text"], pos, pos + len(num))
            st.stylize(muted or None, pos + len(num), pos + len(tw))
    if _cells(st.plain) > inner:
        st = Text(_cut(st.plain, inner, am), no_wrap=True)
        st.overflow = "crop"
    else:
        _pad_text(st, inner)
    lines.append(st)
    panel = Panel(Group(*lines), box=_box.ROUNDED if not am else _box.ASCII,
                  border_style=pal["border"] if not nc else "",
                  width=inner + 4, padding=(0, 1))
    return panel


def _pad_text(t: "Text", width: int) -> "Text":
    """Добить Text пробелами до точной ширины (спаны сохраняются)."""
    w = _cells(t.plain)
    if w < width:
        t = t.copy()
        t.append(" " * (width - w))
    return t


def _item_rows(state: MenuState, pal: dict, lang: str, content_w: int,
               show_desc: bool, reveal=None):
    """Строки пунктов: Text точной ширины content_w. Группы — пустой строкой."""
    from rich.text import Text

    shown = state.items if reveal is None else state.items[: max(0, reveal)]
    nums = display_numbers(shown)
    rows = []
    bounds: set = set()
    if state.groups:
        idx, first = 0, True
        for g in state.groups:
            size = len([k for k in g if any(it.key == k for it in shown)])
            if size and not first:
                bounds.add(idx)
            idx += size
            first = False
    acc_bold = "bold" if state.no_color else _style(f"bold {pal['accent']}")
    txt = None if state.no_color else pal["text"]
    white_b = "bold" if state.no_color else _style(f"bold {pal['white']}")
    dim = "" if state.no_color else pal["dim"]
    muted = "" if state.no_color else pal["muted"]
    nm = "" if state.no_color else pal["dim"]
    for i, it in enumerate(shown):
        if i in bounds:
            rows.append(Text(""))
        label = _ascii_clean(it.label) if state.ascii else it.label
        hint = _ascii_clean(it.hint) if state.ascii else it.hint
        danger = it.key in DANGER_KEYS
        selected = (i == state.selected)
        num = nums[i] if i < len(nums) else str(i + 1)
        shown_num = "Q" if num == "0" else num
        no_hint = it.key == "exit"  # у Выхода описания нет никогда
        if no_hint or not show_desc:
            name_field = _cut(label, 32, state.ascii)
        else:
            name_field = _pad(_cut(label, 32, state.ascii), 32)
        if selected:
            if danger:
                st = "bold" if state.no_color else _style(f"bold {DANGER_SEL}")
                name_st = st
            else:
                st = acc_bold
                name_st = white_b
            t = Text(no_wrap=True)
            t.overflow = "crop"
            t.append(" ", style=None)
            t.append("❯" if not state.ascii else ">", style=st or None)
            t.append(" ", style=None)
            t.append(shown_num, style=st or None)
            t.append("  ", style=None)
            t.append(name_field, style=name_st or None)
            if show_desc and not no_hint:
                t.append(hint, style=muted or None)
            rows.append(t)
        else:
            t = Text(no_wrap=True)
            t.overflow = "crop"
            t.append(" ", style=None)
            t.append(" ", style=None)
            t.append(" ", style=None)
            t.append(shown_num, style=nm or None)
            t.append("  ", style=None)
            t.append(name_field, style=txt)
            if show_desc and not no_hint:
                t.append(hint, style=dim or None)
            rows.append(t)
        # точная ширина строки
        if _cells(rows[-1].plain) > content_w:
            rows[-1] = Text(_cut(rows[-1].plain, content_w, state.ascii),
                            no_wrap=True)
    return rows


def _footer_line(state: MenuState, pal: dict, lang: str, width: int):
    """Одна строка подсказок: пары через три пробела. Не шире width."""
    from rich.text import Text

    from .i18n import t as _t

    nav = "Up/Dn W S" if state.ascii else _t("footer.nav", lang=lang)
    jr = _jump_range(state.items)
    if state.ascii:
        jr = jr.replace("–", "-")
    pairs = [(nav, _t("footer.do", lang=lang)),
             (_t("footer.enter", lang=lang), _t("footer.open", lang=lang)),
             (jr, _t("footer.quick", lang=lang)),
             ("Q", _t("footer.exit", lang=lang)),
             ("L", _t("footer.lang", lang=lang))]
    sep = "   "
    use = []
    total = ""
    for key, hint in pairs:
        if not key:
            continue
        cand = key + " " + hint
        trial = cand if not use else total + sep + cand
        if _cells(trial) > width and use:
            break
        use.append((key, hint))
        total = trial
    t = Text(no_wrap=True)
    t.overflow = "crop"
    for k, (key, hint) in enumerate(use):
        if k:
            t.append(sep, style="" if state.no_color else pal["dim"])
        t.append(key, style="bold" if state.no_color else _style(f"bold {pal['muted']}"))
        t.append(" " + hint, style="" if state.no_color else pal["dim"])
    # ведущий пробел (колонка 0), текст с колонки 1
    out = Text(no_wrap=True)
    out.overflow = "crop"
    out.append(" ", style=None)
    out.append(t)
    if _cells(out.plain) > width:
        out = Text(_cut(out.plain, width, state.ascii), no_wrap=True)
        out.overflow = "crop"
    return out


def build_screen(state: MenuState, lang: str, theme: str, width: int,
                 reveal=None):
    """ВЕСЬ экран одним объектом. width — ширина терминала.

    Шапка шириной min(76, width); список и футер — по левому краю.
    """
    from rich.console import Group
    from rich.text import Text

    from .i18n import t as _t

    w = max(20, int(width))
    pal = _pal(state, theme)
    n = len(state.items)
    show_desc = w >= 66
    card_w = min(CONTENT_MAX, w)
    inner = card_w - 4
    parts = []
    # шапка
    if w < 46:
        name = "AiPC"
        ver = f"v{state.version}"
        t1 = Text(no_wrap=True)
        t1.overflow = "crop"
        acc = "bold" if state.no_color else _style(f"bold {pal['accent']}")
        txt = "bold" if state.no_color else _style(f"bold {pal['text']}")
        t1.append(name, style=acc or None)
        t1.append(f" {ver}", style=txt or None)
        parts.append(t1)
    else:
        parts.append(_header_card(state, pal, lang, inner))
    parts.append(Text(""))
    grid_rows = _item_rows(state, pal, lang, min(CONTENT_MAX, w), show_desc,
                           reveal)
    parts.extend(grid_rows)
    parts.append(Text(""))
    parts.append(_footer_line(state, pal, lang, min(CONTENT_MAX, w)))
    return Group(*parts)
def _tools_count() -> int:
    """Число tools из tools.json (для шапки)."""
    try:
        import json
        from pathlib import Path

        tj = Path(__file__).resolve().parent.parent / "tools.json"
        if tj.exists():
            return len(json.loads(tj.read_text(encoding="utf-8")).get("tools", []))
    except Exception:
        pass
    return 0


def build_state(title: str, items: List[MenuItem], groups: Optional[List[List[str]]],
                selected: int, box=None, show_title: bool = True) -> MenuState:
    """Собрать состояние из конфига/окружения (единственное место чтения)."""
    import os as _os

    from . import __version__ as _ver
    from .config import load_config

    try:
        cfg = load_config()
    except Exception:
        cfg = {}
    ui = cfg.get("ui") or {}
    if not isinstance(ui, dict):
        ui = {}
    theme = str(ui.get("theme", "green"))
    if theme not in THEMES:
        theme = "green"
    try:
        cwd = _os.getcwd()
    except Exception:
        cwd = ""
    try:
        from .maintenance import core_running
        running = bool(core_running())
    except Exception:
        running = False
    no_color = "NO_COLOR" in _os.environ
    ascii_mode = _os.environ.get("AIPC_ASCII", "") == "1"
    if not ascii_mode:
        try:
            import sys as _sys

            enc = (_sys.stdout.encoding or "utf-8")
            "❯●↑↓─│╭╮╰╯…↳–".encode(enc)
        except Exception:
            ascii_mode = True
    from .i18n import current_lang

    try:
        from .maintenance import cached_update_notice
        notice = cached_update_notice(current_lang())
    except Exception:
        notice = ""
    return MenuState(
        title=title, items=items, groups=groups, selected=selected,
        mode=str(cfg.get("mode", "ask")), lang=current_lang(), theme=theme,
        core_running=running, version=str(_ver),
        no_color=no_color, ascii=ascii_mode, cwd=cwd,
        center=bool(ui.get("center", False)), tools=_tools_count(),
        show_title=show_title, notice=notice)


def toggle_language() -> str:
    """Переключить язык меню en<->ru (клавиша L). Возвращает новый язык."""
    from .config import load_config, save_config
    from .i18n import current_lang

    cur = current_lang()
    new = "ru" if cur != "ru" else "en"
    try:
        cfg = load_config()
        cfg["language"] = new
        cfg.pop("lang", None)
        save_config(cfg)
    except Exception:
        pass
    return new


def state_slogan(state: MenuState) -> str:
    from .i18n import t as _t

    return _t("slogan")
def clear_screen() -> None:
    """Жёсткая очистка экрана incl. scrollback.

    rich console.clear() шлёт ANSI \\x1b[2J — в ряде консолей он молча
    глотается и история копится. cls идёт через WinAPI и чистит всегда.
    """
    try:
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
    except Exception:
        try:
            from rich.console import Console

            Console().clear()
        except Exception:
            pass


def _key_waiting() -> bool:
    """True — в буфере ввода уже лежит клавиша (для пропуска анимации)."""
    if os.name != "nt":
        try:
            import select

            return bool(select.select([sys.stdin], [], [], 0)[0])
        except Exception:
            return False
    try:
        import msvcrt

        return bool(msvcrt.kbhit())
    except Exception:
        return False


def splash(console, duration: float = 1.0) -> None:
    """Стартовая заставка: лого проявляется построчно, подпись, плавный прогресс.

    Весь экран одним Live (screen=True) — без мерцания. Любая нажатая клавиша
    пропускает анимацию и остаётся в буфере для меню.
    """
    import time as _time

    from rich.align import Align
    from rich.console import Group
    from rich.live import Live
    from rich.text import Text

    if not sys.stdin.isatty():
        return

    lines = [ln for ln in LOGO_BLOCK.splitlines()]
    n = len(lines)
    prog_steps = 12
    total = n + 2 + prog_steps  # строки лого + подпись + прогресс
    per = max(0.03, duration / max(1, total))

    def frame(k: int):
        parts = [Align.center(_gradient(ln)) for ln in lines[: min(k, n)]]
        if k > n:
            parts.append(Align.center(Text(LOGO_SUB, style=f"bold {THEME['logo_sub']}")))
        if k > n + 1:
            frac = min(1.0, (k - n - 1) / prog_steps)
            filled = int(frac * 26)
            bar = "█" * filled + "░" * (26 - filled)
            parts.append(Align.center(Text(f" {bar} {int(frac * 100):>3}%",
                                           style=f"bold {THEME['accent']}")))
        return Group(*parts) if parts else Group(Text(" "))

    try:
        with Live(frame(0), console=console, screen=True, auto_refresh=False) as live:
            for k in range(1, total + 3):
                if _key_waiting():
                    break
                live.update(frame(k), refresh=True)
                _time.sleep(per)
    except Exception:
        pass
    try:
        clear_screen()
    except Exception:
        pass


def _animations_on() -> bool:
    """Анимации разрешены (ui.animations)? Заставка — всегда на первом запуске."""
    try:
        from .config import load_config

        ui = load_config().get("ui") or {}
        return bool(ui.get("animations", False))
    except Exception:
        return False


def _term_size(console) -> tuple:
    """Размер терминала (колонки, строки)."""
    try:
        s = console.size
        w, h = int(s.width or 0), int(s.height or 0)
        if w > 0 and h > 0:
            return (w, h)
    except Exception:
        pass
    try:
        import shutil

        c = shutil.get_terminal_size((80, 24))
        return (int(c.columns), int(c.lines))
    except Exception:
        return (80, 24)


def _alt_buffer(enter: bool) -> None:
    """Альтернативный буфер терминала (истинный fullscreen без мусора)."""
    try:
        if not sys.stdin.isatty():
            return
        sys.stdout.write("\x1b[?1049h" if enter else "\x1b[?1049l")
        sys.stdout.flush()
    except Exception:
        pass


def _render(state: MenuState, width: int, reveal=None):
    """Кадр под ширину терминала (высота не нужна: скролл, не падение)."""
    return build_screen(state, state.lang, state.theme, width, reveal=reveal)


def intro_reveal(live, state: MenuState, size) -> None:
    """Каскад появления кнопок: кадры reveal=1..n в уже открытом Live."""
    import time as _time

    n = len(state.items)
    if n <= 1:
        return
    try:
        for k in range(1, n + 1):
            if _key_waiting():
                break
            live.update(_render(state, size[0], reveal=k), refresh=True)
            _time.sleep(0.055)
    except Exception:
        pass


def run_menu(title: str, items: List[MenuItem], hint: Optional[str] = None,
             splash_first: bool = False, show_title: bool = True, box=None,
             groups: Optional[List[List[str]]] = None) -> int | str:
    """Меню новым движком: один Live в альт-буфере, кадр только по событию.

    show_title/box оставлены для совместимости (рамка всегда ROUNDED-стиля).
    hint — зарезервировано (футер строится из i18n). Возвращает index/'quit'.
    """
    _ensure_utf8()
    _enable_windows_ansi()

    try:
        from rich.console import Console
    except ImportError:
        return _fallback_numeric_menu(title, items)

    if not sys.stdin.isatty():
        return _fallback_numeric_menu(title, items)

    import os as _os

    no_color = "NO_COLOR" in _os.environ
    console = Console(highlight=False, legacy_windows=False,
                      color_system="auto", no_color=no_color)
    state = build_state(title, items, groups, 0, show_title=show_title)
    numbers = display_numbers(items)

    if splash_first and _animations_on():
        splash(console)

    if os.name != "nt":
        return _posix_menu_loop(console, state)

    from rich.live import Live

    def _refresh(live, size):
        try:
            live.update(_render(state, size[0]), refresh=True)
        except Exception:
            pass

    size = _term_size(console)
    _alt_buffer(True)
    try:
        with Live(_render(state, size[0]), console=console,
                  screen=True, auto_refresh=False) as live:
            if splash_first and _animations_on():
                intro_reveal(live, state, size)
                live.update(_render(state, size[0]), refresh=True)
            while True:
                try:
                    key = _read_key_wide()
                except (OSError, EOFError, KeyboardInterrupt) as e:
                    _menu_log(f"input-error {type(e).__name__}")
                    return _fallback_numeric_menu(title, items)
                _menu_log(f"key={key!r} selected={state.selected}")
                if key == "lang":
                    # L: смена языка на лету, выбор и размеры сохраняем
                    sel, size = state.selected, _term_size(console)
                    toggle_language()
                    state = build_state(title, items, groups, sel,
                                        show_title=show_title)
                    numbers = display_numbers(items)
                    _refresh(live, size)
                    continue
                action, val = apply_key(state.selected, len(state.items), key,
                                        numbers)
                if action == "quit":
                    _menu_log("return quit")
                    return "quit"
                if action == "select":
                    _menu_log(f"return idx={val}")
                    return val
                if action == "move" and val != state.selected:
                    state.selected = val
                    size = _term_size(console)
                    _refresh(live, size)
                # noop/unknown — кадр не трогаем (нечего перерисовывать)
    finally:
        try:
            _alt_buffer(False)
        except Exception:
            pass


def _posix_menu_loop(console, state: MenuState):
    """Запасной цикл для POSIX: та же навигация, перерисовка через clear."""
    import termios
    import tty

    def show():
        try:
            console.clear()
        except Exception:
            pass
        console.print(_render(state, _term_size(console)[0]))

    show()

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    numbers = display_numbers(state.items)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            key = "unknown"
            if ch == "\x1b":
                nxt = sys.stdin.read(1)
                if nxt == "[":
                    nxt2 = sys.stdin.read(1)
                    key = {"A": "up", "B": "down", "H": "home", "F": "end"}.get(nxt2, "unknown")
                    if key == "unknown" and nxt2 in ("1", "4"):
                        # ESC[1~ (Home), ESC[4~ (End)
                        sys.stdin.read(1)
                        key = "home" if nxt2 == "1" else "end"
                else:
                    return "quit"
            elif ch in ("w", "W", "k", "K", "ц", "Ц"):
                key = "up"
            elif ch in ("s", "S", "j", "J", "ы", "Ы"):
                key = "down"
            elif ch in ("l", "L", "д", "Д"):
                key = "lang"
            elif ch == "\r" or ch == "\n":
                key = "enter"
            elif ch in ("q", "Q", "й", "Й"):
                key = "quit"
            elif ch.isdigit():
                key = ch
            if key == "lang":
                sel = state.selected
                toggle_language()
                state = build_state(state.title, state.items, state.groups,
                                    sel, show_title=state.show_title)
                numbers = display_numbers(state.items)
                show()
                continue
            action, val = apply_key(state.selected, len(state.items), key,
                                    numbers)
            if action == "quit":
                return "quit"
            if action == "select":
                return val
            if action == "move" and val != state.selected:
                state.selected = val
                show()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _ui_opts():
    """Тема/режим консоли из конфига и окружения (для карточек действий)."""
    from .config import load_config

    try:
        cfg = load_config()
    except Exception:
        cfg = {}
    ui = cfg.get("ui") or {}
    if not isinstance(ui, dict):
        ui = {}
    theme = str(ui.get("theme", "green"))
    if theme not in THEMES:
        theme = "green"
    import os as _os

    no_color = "NO_COLOR" in _os.environ
    ascii_mode = _os.environ.get("AIPC_ASCII", "") == "1"
    if not ascii_mode:
        try:
            import sys as _sys

            "─│╭╮╰╯".encode(_sys.stdout.encoding or "utf-8")
        except Exception:
            ascii_mode = True
    return theme, no_color, ascii_mode


def _card_border(kind: str, pal: dict, no_color: bool) -> str:
    """Цвет рамки карточки: info/ok — акцент, warn — жёлтый, err — красный."""
    if no_color:
        return ""
    if kind == "err":
        return _style(f"{DANGER_SEL}")
    if kind == "warn":
        return _style("#F9F1A5")
    return _style(f"{pal['accent']}")


def _card_panel(title: str, body: str, kind: str = "info", width: int = 76):
    """Панель карточки (для тестов и show_card)."""
    from rich.panel import Panel
    from rich.text import Text
    import rich.box as _box

    theme, no_color, ascii_mode = _ui_opts()
    pal = dict(THEMES.get(theme, THEMES["green"]))
    if no_color:
        for k in pal:
            if isinstance(pal.get(k), str) and pal[k].startswith("#"):
                pal[k] = ""
    return Panel(Text(body or "", style="" if no_color else pal["text"]),
                 box=_box.ASCII if ascii_mode else _box.ROUNDED,
                 border_style=_card_border(kind, pal, no_color),
                 width=max(20, min(width, 76)), padding=(0, 1),
                 title=Text(f" {title} " if title else "",
                            style="" if no_color else pal["dim"]),
                 title_align="left")


def show_card(title: str, body: str, kind: str = "info", width: int = 76) -> None:
    """Карточка результата в стиле меню: ROUNDED, акцентная рамка, тема,
    EN/RU снаружи (title/body уже локализованы вызывателем)."""
    from rich.console import Console

    try:
        clear_screen()
    except Exception:
        pass
    console = Console(highlight=False, legacy_windows=False)
    console.print(_card_panel(title, body, kind, width))


def pause(key: str = "common.pause") -> None:
    """Пауза «Enter чтобы вернуться» (локализовано)."""
    from .i18n import t as _t

    try:
        input(_t(key))
    except (EOFError, KeyboardInterrupt):
        pass


def _fallback_numeric_menu(title: str, items: List[MenuItem]):
    from .i18n import t as _t

    print(f"=== {title} ===")
    print(LOGO_BLOCK)
    print(LOGO_SUB)
    print()
    for i, it in enumerate(items, 1):
        print(f"  {i}. {it.label}")
    print(f"  Q. {_t('menu.exit')}")
    try:
        ans = input(f"{_t('misc.enter_number')}> ").strip().lower()
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
