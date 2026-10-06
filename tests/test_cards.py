"""Карточки действий: стиль меню, темы, i18n EN/RU."""
import re

from rich.cells import cell_len
from rich.console import Console

from aipc.i18n import EN, RU
from aipc.menu import _card_panel


def render_panel(title, body, kind="info", width=76, color="truecolor"):
    con = Console(width=width, force_terminal=True, color_system=color,
                  record=True, legacy_windows=False)
    con.print(_card_panel(title, body, kind, width))
    return con.export_text(styles=True)


def plain(text):
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_card_renders_title_body():
    p = plain(render_panel("Запустить", "AiPC-Core запущен.\nPID 1"))
    assert "Запустить" in p and "AiPC-Core запущен." in p and "PID 1" in p
    assert "╭" in p and "╰" in p
    for ln in p.splitlines():
        s = ln.rstrip()
        if s and s[0] in ("╭", "│", "╰"):
            assert cell_len(s) == 76, s


def test_card_kinds_border_colors():
    assert "38;2;255;107;107" in render_panel("T", "b", "err")  # красный
    assert "38;2;61;220;132" in render_panel("T", "b", "ok")  # акцент green
    assert "249;241;165" in render_panel("T", "b", "warn")  # жёлтый
    for kind in ("info", "ok", "warn", "err"):
        assert "\x1b[48" not in render_panel("T", "b", kind)  # без заливок


def test_card_themes():
    from aipc.config import load_config, save_config

    cfg = load_config()
    old = (cfg.get("ui") or {}).get("theme", "green")
    try:
        for theme, code in (("mono", "232;232;232"), ("amber", "255;176;0")):
            ui = cfg.get("ui") or {}
            ui["theme"] = theme
            cfg["ui"] = ui
            save_config(cfg)
            assert code in render_panel("T", "b", "ok"), theme
    finally:
        ui = cfg.get("ui") or {}
        ui["theme"] = old
        cfg["ui"] = ui
        save_config(cfg)


def test_card_ascii(monkeypatch):
    monkeypatch.setenv("AIPC_ASCII", "1")
    text = render_panel("T", "b", "info")
    for ch in ("╭", "│", "─"):
        assert ch not in text
    assert "+" in text


def test_show_card_smoke(capsys):
    from aipc.menu import pause, show_card

    show_card("Hi", "body here", kind="ok")
    out = capsys.readouterr().out
    assert "Hi" in out and "body here" in out
    import builtins

    def _boom(*a, **k):
        raise EOFError

    orig = builtins.input
    builtins.input = _boom
    try:
        pause()
    finally:
        builtins.input = orig


def test_action_strings_both_langs():
    from aipc.config import load_config, save_config
    from aipc import i18n as I

    cfg = load_config()
    old_lang = cfg.get("language", "en")
    old_legacy = cfg.pop("lang", None)
    try:
        cfg["language"] = "en"
        save_config(cfg)
        assert I.t("act.start.checking") == "Checking Core like an IDE (handshake)..."
        assert I.t("setup.browser.title") == "Browser"
        cfg["language"] = "ru"
        save_config(cfg)
        assert I.t("act.start.checking") == "Проверяю Core как IDE (handshake)..."
        assert "host" in I.t("setup.ssh.host")
        assert I.t("setup.ssh.saved").format(user="u", host="h", port=22) == \
            "Сохранено: u@h:22"
    finally:
        cfg["language"] = old_lang
        if old_legacy is not None:
            cfg["lang"] = old_legacy
        save_config(cfg)


def test_kill_notes_localized():
    from aipc.config import load_config, save_config
    from aipc import maintenance as MT

    cfg = load_config()
    old_lang = cfg.get("language", "en")
    old_legacy = cfg.pop("lang", None)
    try:
        cfg["language"] = "ru"
        save_config(cfg)
        assert MT.kill_core()["note"] == "Core не запущен (нет PID-файла)"
        cfg["language"] = "en"
        save_config(cfg)
        assert MT.kill_core()["note"] == "Core is not running (no PID file)"
    finally:
        cfg["language"] = old_lang
        if old_legacy is not None:
            cfg["lang"] = old_legacy
        save_config(cfg)
