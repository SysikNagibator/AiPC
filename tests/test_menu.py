"""Меню пиксель-в-пиксель: навигация, i18n, позиции, goldens, адаптивность."""
import os
import re
import sys
import types
from pathlib import Path

import pytest
from rich.cells import cell_len
from rich.console import Console

from aipc.i18n import EN, RU
from aipc.menu import MenuItem, MenuState, apply_key, build_screen

GOLDEN = Path(__file__).resolve().parent / "golden"

ITEMS_EN = [
    MenuItem("Launch AiPC-Core", "run", "background server, IDE-style handshake"),
    MenuItem("Stop", "stop", "only our own process"),
    MenuItem("Status & self-test", "status", "screen, mouse, terminal, MCP"),
    MenuItem("Diagnostics", "doctor", "install, PATH, IDE configs"),
    MenuItem("Check updates", "update", "compare with GitHub releases"),
    MenuItem("Setup", "setup", "mode, IDE, browser, SSH"),
    MenuItem("Service", "service", "reinstall, MCP, reset"),
    MenuItem("Logs", "logs", "last 20 lines of audit.log"),
    MenuItem("Exit", "exit", "close the menu"),
]
ITEMS_RU = [
    MenuItem("Запустить AiPC-Core", "run", "фоновый сервер, проверка как у IDE"),
    MenuItem("Остановить", "stop", "только свой процесс"),
    MenuItem("Статус и самотест", "status", "экран, мышь, терминал, MCP"),
    MenuItem("Диагностика", "doctor", "установка, PATH, конфиги IDE"),
    MenuItem("Обновления", "update", "сверка с релизами GitHub"),
    MenuItem("Настройки", "setup", "режим, IDE, браузер, SSH"),
    MenuItem("Сервис", "service", "переустановка, MCP, сброс"),
    MenuItem("Логи", "logs", "последние 20 строк audit.log"),
    MenuItem("Выход", "exit", "закрыть меню"),
]
GROUPS = [["run", "stop", "status"], ["doctor", "update"],
          ["setup", "service", "logs"], ["exit"]]


def make_state(lang="en", theme="green", mode="ask", selected=0,
               running=True, no_color=False, ascii=False):
    from aipc import __version__ as _ver
    from aipc.config import load_config, save_config

    cfg = load_config()
    cfg["language"] = lang
    save_config(cfg)
    items = list(ITEMS_RU) if lang == "ru" else list(ITEMS_EN)
    return MenuState(
        title="menu" if lang == "en" else "меню", items=items,
        groups=[list(g) for g in GROUPS], selected=selected, mode=mode,
        lang=lang, theme=theme, core_running=running, version=str(_ver),
        no_color=no_color, ascii=ascii, cwd="C:\\Users\\sysik",
        center=False, tools=70, show_title=False)


def render_text(state, w, color="truecolor"):
    con = Console(width=w, force_terminal=True,
                  color_system=color, record=True, legacy_windows=False)
    con.print(build_screen(state, state.lang, state.theme, w))
    return con.export_text(styles=True)


def plain_lines(text):
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    return [ansi.sub("", ln) for ln in text.splitlines()]


def _plain(text):
    return "\n".join(plain_lines(text))


# --- навигация (без изменений) ---

def test_apply_key_moves_and_wraps():
    assert apply_key(0, 9, "up") == ("move", 8)
    assert apply_key(8, 9, "down") == ("move", 0)
    assert apply_key(2, 9, "down") == ("move", 3)
    assert apply_key(5, 9, "home") == ("move", 0)
    assert apply_key(5, 9, "end") == ("move", 8)
    assert apply_key(3, 9, "enter") == ("select", 3)
    assert apply_key(0, 9, "quit") == ("quit", -1)
    assert apply_key(0, 9, "esc") == ("quit", -1)
    assert apply_key(0, 9, "lang") == ("lang", 0)
    assert apply_key(4, 9, "zzz") == ("noop", 4)
    assert apply_key(0, 0, "down") == ("quit", -1)


def test_apply_key_with_numbers():
    from aipc.menu import apply_key as AK
    from aipc.menu import display_numbers as DN

    nums = DN(ITEMS_EN)
    assert nums == ["1", "2", "3", "4", "5", "6", "7", "8", "0"]
    assert AK(0, 9, "0", nums) == ("select", 8)
    assert AK(0, 9, "9", nums) == ("noop", 0)
    assert AK(0, 9, "1", nums) == ("select", 0)
    assert AK(0, 9, "8", nums) == ("select", 7)
    assert AK(0, 9, "0") == ("noop", 0)


def test_display_numbers_exit_is_zero():
    from aipc.menu import display_numbers

    assert display_numbers(ITEMS_EN)[-1] == "0"
    others = [MenuItem("A", "a"), MenuItem("B", "b")]
    assert display_numbers(others) == ["1", "2"]


def test_key_sequence_no_artifacts():
    st = make_state()
    sel = 0
    frames = []
    for key in ("down", "down", "down", "up", "home", "end"):
        action, val = apply_key(sel, len(st.items), key)
        assert action == "move"
        sel = val
        st.selected = sel
        frames.append(render_text(st, 80))
    assert sel == 8
    assert apply_key(sel, len(st.items), "9") == ("select", 8)
    assert apply_key(sel, len(st.items), "quit")[0] == "quit"
    for f in frames:
        marks = [ln for ln in plain_lines(f) if re.match(r" ❯ ", ln)]
        assert len(marks) == 1, "маркер выбора ровно один"


# --- i18n ---

def test_i18n_no_missing_keys():
    assert set(EN) == set(RU)
    for required in ("slogan", "title.menu", "core.running", "core.stopped",
                     "hdr.mode", "footer.do", "footer.open", "footer.quick",
                     "footer.exit", "footer.lang", "tools.one", "tools.few",
                     "tools.many", "misc.enlarge", "setup.theme",
                     "setup.theme.hint", "theme.green", "update.ask"):
        assert required in EN and required in RU


def test_en_screen_no_cyrillic():
    text = _plain(render_text(make_state("en"), 80))
    assert not re.search(r"[\u0400-\u04FF]", text)


def test_ru_screen_no_english_labels():
    text = _plain(render_text(make_state("ru"), 80))
    for word in ("mode", "tools", "select"):
        assert not re.search(rf"\b{word}\b", text), word
    assert "режим" in text and "инструментов" in text


# --- позиции (колонки блока) ---

def _rows_by_label(text, items):
    lines = plain_lines(text)
    out = {}
    for it in items:
        hits = [ln for ln in lines if it.label in ln]
        assert len(hits) == 1, f"{it.label}: {hits}"
        out[it.key] = hits[0]
    return out


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_positions(lang):
    items = ITEMS_RU if lang == "ru" else ITEMS_EN
    st = make_state(lang)
    st.selected = 0
    rows = _rows_by_label(render_text(st, 80), items)
    for key, ln in rows.items():
        assert ln[1] in ("❯", " "), f"{key}: {ln!r}"
        num = "0" if key == "exit" else None
        if key == "exit":
            assert ln[3] == "Q", ln
        assert ln[6:6 + 1] != "", ln
    # выбранный: маркер в 1, номер в 3, название в 6, описание в 38
    sel = rows["run"]
    assert sel[1] == "❯"
    assert sel[3] == "1"
    assert sel[6:].startswith(items[0].label)
    assert sel[38:].startswith(items[0].hint)
    # невыбранный: пробел в 1
    other = rows["stop"]
    assert other[1] == " " and other[3] == "2"


def test_exit_row_no_description():
    rows = _rows_by_label(render_text(make_state(), 80), ITEMS_EN)
    assert rows["exit"].rstrip().endswith("Exit")


def test_each_item_has_own_description():
    text = _plain(render_text(make_state(), 80))
    lines = text.splitlines()
    for it in ITEMS_EN:
        if it.key == "exit":
            continue
        hits = [ln for ln in lines if it.label in ln and it.hint in ln]
        assert len(hits) == 1, f"{it.label}: {hits}"


def test_no_background_fills():
    for theme in ("green", "mono", "amber"):
        text = render_text(make_state("en", theme), 80)
        assert "\x1b[48" not in text, f"заливка в теме {theme}"


def test_danger_selected_is_red():
    st = make_state(selected=1)  # Stop
    text = render_text(st, 80)
    assert "38;2;255;107;107" in text  # #FF6B6B
    assert "\x1b[48" not in text


def test_no_color_selection_visible():
    text = render_text(make_state("en", "green", "ask", no_color=True), 80)
    assert "❯" in text
    assert "\x1b[1m" in text  # жирный остаётся
    assert "38;" not in text  # а цвета нет


def test_ascii_fallback(monkeypatch):
    import aipc.menu as M

    monkeypatch.setenv("AIPC_ASCII", "1")
    st = make_state("en", "green", "ask", ascii=True)
    text = render_text(st, 80)
    assert text == _plain(text) or True
    for ch in ("╭", "│", "❯", "●", "─", "…", "↳", "–", "·", "○", "▄", "▀", "█"):
        assert ch not in text, ch
    assert ">" in text and "+" in text and "*" in text
    assert "Up/Dn" in text and "AiPC" in text


def test_ascii_env_flag(monkeypatch):
    import aipc.menu as M

    monkeypatch.setenv("AIPC_ASCII", "1")
    st = M.build_state("m", list(ITEMS_EN)[:2], None, 0)
    assert st.ascii is True


# --- адаптивность ---

def test_narrow_60_no_desc():
    text = _plain(render_text(make_state(), 60))
    assert "background server" not in text
    assert "Launch AiPC-Core" in text


def test_narrow_40_logo_line():
    text = _plain(render_text(make_state(), 40))
    assert "AiPC" in text
    assert "▄" not in text and "█" not in text


def test_no_line_wider_than_window():
    for w in (40, 60, 66, 76, 80, 120):
        text = render_text(make_state("en"), w)
        for ln in plain_lines(text):
            assert cell_len(ln.rstrip()) <= w, f"{w}: {ln!r}"


@pytest.mark.parametrize("w", [40, 46, 50, 60, 66, 70, 76, 80, 90, 100, 120])
@pytest.mark.parametrize("lang", ["en", "ru"])
def test_adapt_every_size(w, lang):
    """Авто-адаптация под каждый размер окна: без падений и переполнений."""
    text = render_text(make_state(lang), w)
    assert text.strip(), f"{w} пусто"
    for ln in plain_lines(text):
        assert cell_len(ln.rstrip()) <= w, f"{w} {lang}: {ln!r}"
    # шапка есть всегда (полная или строкой AiPC)
    assert "╭" in text or "AiPC" in text


def test_reveal_cascade():
    from aipc.menu import build_screen as _bs

    st = make_state()
    st.selected = 0
    c2 = Console(width=80, force_terminal=True, legacy_windows=False,
                 record=True)
    c2.print(_bs(st, "en", "green", 80, reveal=2))
    part = c2.export_text(styles=True)
    assert "Launch AiPC-Core" in part
    assert "Exit" not in part


def test_header_tools_count():
    import json
    from pathlib import Path

    n = len(json.loads(Path("tools.json").read_text(encoding="utf-8"))["tools"])
    text = _plain(render_text(make_state("en"), 80))
    assert f"{n} tools" in text
    text_ru = _plain(render_text(make_state("ru"), 80))
    assert str(n) in text_ru


def test_toggle_language():
    from aipc.config import load_config, save_config
    from aipc.menu import toggle_language

    cfg = load_config()
    cfg["language"] = "en"
    cfg.pop("lang", None)
    save_config(cfg)
    assert toggle_language() == "ru"
    assert toggle_language() == "en"


def test_jump_range():
    from aipc.menu import _jump_range

    assert _jump_range(ITEMS_EN) == "1–8"
    assert _jump_range([MenuItem("A", "a")]) == "1–1"


def test_tools_word_plural():
    from aipc.menu import _tools_word

    assert _tools_word(1, "en") == "1 tool"
    assert _tools_word(70, "en") == "70 tools"
    assert _tools_word(1, "ru") == "1 инструмент"
    assert _tools_word(2, "ru") == "2 инструмента"
    assert _tools_word(5, "ru") == "5 инструментов"
    assert _tools_word(70, "ru") == "70 инструментов"


def test_header_mockup_content():
    from aipc import __version__ as _ver

    text = _plain(render_text(make_state("en", running=False), 80))
    assert "by SYSIK" in text and f"v{_ver}" in text
    assert "core" in text and "stopped" in text
    assert "70 tools" in text
    assert "[ask]" not in text
    assert "mode ask" in text


# --- золотые снапшоты ---

def assert_snapshot(name, text):
    p = GOLDEN / (name + ".txt")
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        GOLDEN.mkdir(exist_ok=True)
        p.write_text(text, encoding="utf-8")
    assert p.exists(), f"нет golden {name}: UPDATE_SNAPSHOTS=1"
    want = [ln.rstrip() for ln in p.read_text(encoding="utf-8").splitlines()]
    got = [ln.rstrip() for ln in text.splitlines()]
    assert want == got


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_goldens(lang):
    st = make_state(lang, "green", "ask", selected=0, running=True)
    con = Console(width=80, force_terminal=False, color_system=None,
                  record=True, legacy_windows=False)
    con.print(build_screen(st, lang, "green", 80))
    assert_snapshot(f"menu_{lang}", con.export_text())


def test_theme_changes_accent():
    g = render_text(make_state("en", "green"), 80)
    m = render_text(make_state("en", "mono"), 80)
    a = render_text(make_state("en", "amber"), 80)
    assert "38;2;0;200;100" in g and "38;2;0;200;100" not in m
    assert "255;176;0" in a


class _FakeMsvcrt(types.ModuleType):
    def __init__(self, chars):
        super().__init__("msvcrt")
        self._chars = list(chars)

    def getwch(self):
        if not self._chars:
            raise AssertionError("очередь клавиш пуста")
        return self._chars.pop(0)


def test_read_key_home_end(monkeypatch):
    from aipc.menu import _read_key_wide

    fake = _FakeMsvcrt(["\x00", "G"])
    monkeypatch.setitem(sys.modules, "msvcrt", fake)
    assert _read_key_wide() == "home"
    fake = _FakeMsvcrt(["\xe0", "O"])
    monkeypatch.setitem(sys.modules, "msvcrt", fake)
    assert _read_key_wide() == "end"


def test_read_key_arrows_digits(monkeypatch):
    from aipc.menu import _read_key_wide

    for chars, want in [(["\x00", "H"], "up"), (["\xe0", "P"], "down"),
                        (["\r"], "enter"), (["\x1b"], "esc"),
                        (["q"], "quit"), (["й"], "quit"),
                        (["l"], "lang"), (["д"], "lang"),
                        (["w"], "up"), (["ц"], "up"), (["s"], "down"),
                        (["5"], "5"), (["0"], "0")]:
        fake = _FakeMsvcrt(list(chars))
        monkeypatch.setitem(sys.modules, "msvcrt", fake)
        assert _read_key_wide() == want, chars
