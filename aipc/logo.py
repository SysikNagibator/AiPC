# AiPC от Sysik — лого и тема оформления (без эмодзи, только символы CMD)

LOGO_BLOCK = r"""
 █████╗ ██╗██████╗  ██████╗
██╔══██╗██║██╔══██╗██╔════╝
███████║██║██████╔╝██║
██╔══██║██║██╔═══╝ ██║
██║  ██║██║██║     ╚██████╗
╚═╝  ╚═╝╚═╝╚═╝      ╚═════╝
""".rstrip("\n")

LOGO_COMPACT = "[ AiPC :: от Sysik v1.0 ]"
LOGO_SUB = "от Sysik v1.0"

# Палитра (темный cmd по умолчанию)
THEME = {
    "bg": "#0B1220",
    "logo": "cyan",
    "logo_sub": "#9AA4B2",
    "accent": "cyan",
    "selected_bg": "blue",
    "selected_fg": "white",
    "normal_fg": "#9AA4B2",
    "border": "cyan",
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
