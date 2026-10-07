# AiPC от SYSIK — лого и тема оформления (без эмодзи, только символы CMD)
from __future__ import annotations

from . import __version__

LOGO_BLOCK = r"""
 █████╗ ██╗██████╗  ██████╗
██╔══██╗██║██╔══██╗██╔════╝
███████║██║██████╔╝██║
██╔══██║██║██╔═══╝ ██║
██║  ██║██║██║     ╚██████╗
╚═╝  ╚═╝╚═╝╚═╝      ╚═════╝
""".rstrip("\n")

# Готовый массив строк логотипа (не вычисляется на лету).
LOGO_LINES = tuple(ln for ln in LOGO_BLOCK.splitlines())

# Компактный 2-строчный логотип на полублоках для шапки меню.
COMPACT_LOGO = ("▄▀█ █ █▀█ █▀▀", "█▀█ █ █▀▀ █▄▄")

# Пиксельный 2-строчный логотип полными блоками (стиль макетов).
# Просветы между буквами — ровно по 2 клетки: иначе тень шириной в клетку
# либо заливает просвет, либо вырезается, и буква остаётся без левой кромки.
PIXEL_LOGO = (
    "▄▀█  █  █▀█  █▀▀",
    "█▀█  █  █▀▀  █▄▄",
)

LOGO_COMPACT = f"[ AiPC :: SYSIK v{__version__} ]"
LOGO_SUB = "SYSIK"

# Палитра: зелёная тема (видно и на чёрном, и на белом фоне cmd)
THEME = {
    "bg": "#07130C",
    "logo": "#4ade80",
    "logo_sub": "#8fa98f",
    "accent": "#22c55e",
    "selected_bg": "#15803d",
    "selected_fg": "white",
    "normal_fg": "#9AA4B2",
    "border": "#22c55e",
    "footer_bg": "grey23",
    "footer_fg": "black",
    "ok": "green",
    "err": "red",
}

MENU_WIDTH = 64

# Маркеры без эмодзи. Юникод — если консоль умеет (UTF-8 / Windows Terminal),
# иначе ASCII-запас чтобы правая стенка не падала с UnicodeEncodeError в cp1251.
MARK_SELECTED = "▶"
MARK_NORMAL = " "
MARK_OK = "✓"
MARK_ERR = "✕"
MARK_DOT = "•"

_ASCII_FALLBACK = {
    "▶": ">",
    "✓": "OK",
    "✕": "X",
    "•": "-",
}


def safe_mark(s: str) -> str:
    """Вернуть символ или ASCII-замену если stdout не кодирует юникод."""
    try:
        import sys

        enc = (sys.stdout.encoding or "utf-8")
        s.encode(enc)
        return s
    except Exception:
        return _ASCII_FALLBACK.get(s, "?")
