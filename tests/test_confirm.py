"""Этап 1.1: классификация рисков, серверные подтверждения, timed-разрешения."""
import json
import os

import pytest

from aipc.config import load_config, save_config
from aipc import policy as P
from aipc import server as S


def _set_mode(mode: str) -> dict:
    cfg = load_config()
    old = dict(cfg)
    cfg["mode"] = mode
    save_config(cfg)
    return old


@pytest.fixture()
def ask_mode():
    old = _set_mode("ask")
    yield
    save_config(old)


@pytest.fixture()
def auto_mode():
    old = _set_mode("auto")
    yield
    save_config(old)


def _all_tools():
    srv = S.create_server()
    return [t.name for t in srv._tool_manager.list_tools()]


def test_every_tool_has_risk_class():
    for name in _all_tools():
        r = P.risk_of(name)
        assert r in ("read", "interact", "mutate", "exec", "network"), name
    assert P.risk_of("no_such_tool_xyz") == "mutate"  # неизвестное — консервативно


def test_needs_confirm_matrix():
    assert S._needs_server_confirm("ask", "run_cmd", "exec", "x")[0] is True
    assert S._needs_server_confirm("ask", "fs_write", "mutate", "x")[0] is True
    assert S._needs_server_confirm("ask", "download_file", "network", "x")[0] is True
    assert S._needs_server_confirm("ask", "screen_see", "read", "x")[0] is False
    assert S._needs_server_confirm("ask", "mouse_move", "interact", "x")[0] is False
    assert S._needs_server_confirm("auto", "run_cmd", "exec", "x")[0] is False
    assert S._needs_server_confirm("read-only", "run_cmd", "exec", "x")[0] is False


def test_timed_allow_grant_check_expiry():
    key = P.allow_key("run_cmd", "команда:\ndir")
    assert P.allow_key("run_cmd", "команда:\ndir") == key  # стабилен
    assert P.allow_key("run_cmd", "команда:\ndel") != key  # другое действие
    assert P.is_allowed_timed(key) is False
    P.grant_timed(key, minutes=10)
    assert P.is_allowed_timed(key) is True
    # протухшее чистится
    data = json.loads((P._allow_path()).read_text(encoding="utf-8"))
    data[key] = 1.0
    P._allow_path().write_text(json.dumps(data), encoding="utf-8")
    assert P.is_allowed_timed(key) is False


def test_timed_allow_skips_confirm(ask_mode):
    key = P.allow_key("run_cmd", "команда:\ndir")
    P.grant_timed(key, minutes=10)
    need, why = S._needs_server_confirm("ask", "run_cmd", "exec", "команда:\ndir")
    assert need is False and why == "timed-allow"


def test_sensitive_windows():
    assert P.window_is_sensitive("KeePassXC - passwords.kdbx") is True
    assert P.window_is_sensitive("1Password") is True
    assert P.window_is_sensitive("MetaMask") is True
    assert P.window_is_sensitive("Notepad") is False
    assert P.window_is_sensitive("") is False


def test_sensitive_window_extra_config():
    cfg = load_config()
    old = dict(cfg)
    try:
        cfg.setdefault("safety", {})["sensitive_windows_extra"] = ["mybank"]
        save_config(cfg)
        assert P.window_is_sensitive("MyBank online") is True
    finally:
        save_config(old)


def test_describe_shows_exact_action():
    d = S._describe("run_cmd", (), {"cmd": "del C:\\temp\\x.txt"})
    assert "del C:\\temp\\x.txt" in d
    d = S._describe("ssh_exec", (), {"host": "h", "username": "u", "cmd": "ls"})
    assert "u@h" in d and "ls" in d
    d = S._describe("download_file", (), {"url": "http://e/x", "path": "C:\\a"})
    assert "http://e/x" in d


def _ok_fn(*a, **k):
    return {"ok": True}


def test_wrap_ask_allow_once(monkeypatch, ask_mode):
    monkeypatch.setattr("aipc.notify.confirm_action", lambda *a, **k: "once")
    res = S._wrap("run_cmd", _ok_fn, cmd="dir")
    assert res == {"ok": True}


def test_wrap_ask_deny_blocks(monkeypatch, ask_mode):
    calls = []
    monkeypatch.setattr("aipc.notify.confirm_action", lambda *a, **k: "deny")
    res = S._wrap("run_cmd", lambda *a, **k: calls.append(1) or {"ok": True}, cmd="dir")
    assert res["reason"] == "denied"
    assert calls == []


def test_wrap_ask_timeout(monkeypatch, ask_mode):
    monkeypatch.setattr("aipc.notify.confirm_action", lambda *a, **k: "timeout")
    res = S._wrap("ssh_exec", _ok_fn, host="h", username="u", cmd="ls")
    assert res["reason"] == "denied_timeout"
    assert "hint" in res


def test_wrap_ask_timed_grants(monkeypatch, ask_mode):
    monkeypatch.setattr("aipc.notify.confirm_action", lambda *a, **k: "timed")
    res = S._wrap("fs_delete", _ok_fn, path="C:\\x")
    assert res == {"ok": True}
    key = P.allow_key("fs_delete", S._describe("fs_delete", (), {"path": "C:\\x"}))
    assert P.is_allowed_timed(key) is True


def test_wrap_read_no_confirm_in_ask(monkeypatch, ask_mode):
    def _boom(*a, **k):
        raise AssertionError("confirm не должен вызываться для read")

    monkeypatch.setattr("aipc.notify.confirm_action", _boom)
    res = S._wrap("screen_see", _ok_fn)
    assert res == {"ok": True}


def test_wrap_readonly_still_denies(monkeypatch):
    old = _set_mode("read-only")
    try:
        def _boom(*a, **k):
            raise AssertionError("confirm не должен вызываться в read-only")

        monkeypatch.setattr("aipc.notify.confirm_action", _boom)
        res = S._wrap("run_cmd", _ok_fn, cmd="dir")
        assert res["reason"] == "denied"
    finally:
        save_config(old)


def test_wrap_sensitive_window_click(monkeypatch, ask_mode):
    monkeypatch.setattr("aipc.notify.confirm_action", lambda *a, **k: "once")
    monkeypatch.setattr(S, "_active_window_title", lambda: "KeePassXC")
    res = S._wrap("mouse_click", _ok_fn, x=1, y=2)
    assert res == {"ok": True}


def test_wrap_nonsensitive_click_no_confirm(monkeypatch, ask_mode):
    def _boom(*a, **k):
        raise AssertionError("confirm не должен вызываться вне чувствительных окон")

    monkeypatch.setattr("aipc.notify.confirm_action", _boom)
    monkeypatch.setattr(S, "_active_window_title", lambda: "Notepad")
    res = S._wrap("mouse_click", _ok_fn, x=1, y=2)
    assert res == {"ok": True}


def test_console_confirm_no_tty_denies(monkeypatch):
    import io as _io
    from aipc import notify as NT

    monkeypatch.setattr("sys.stdin", _io.StringIO(""))
    assert NT._console_confirm("run_cmd", "dir", 9999999999.0) == "deny"


def test_console_confirm_eof_is_no(monkeypatch):
    import io as _io
    from aipc import notify as NT

    class _Tty(_io.StringIO):
        def isatty(self):
            return True

    monkeypatch.setattr("sys.stdin", _Tty(""))
    assert NT._console_confirm("run_cmd", "dir", 9999999999.0) == "no"


def test_normalize_presets():
    from aipc.notify import _fmt_mins, _normalize_presets

    assert _normalize_presets([10, 60], 10) == [10, 60]
    assert _normalize_presets([], 10) == [10]
    assert _normalize_presets(None, 10) == [10, 60]
    assert _normalize_presets([0, -5, 2000, "x", 10, 10, 5, 7, 9], 10) == [10, 5, 7]
    assert _normalize_presets(["30"], 10) == [30]
    assert _fmt_mins(10) == "10 мин"
    assert _fmt_mins(60) == "1 ч"
    assert _fmt_mins(90) == "1 ч 30 мин"


def test_wrap_timed_tuple_minutes(monkeypatch, ask_mode):
    import time as _time

    from aipc import policy as P

    monkeypatch.setattr("aipc.notify.confirm_action",
                        lambda *a, **k: ("timed", 60))
    res = S._wrap("fs_delete", _ok_fn, path="C:\\y")
    assert res == {"ok": True}
    key = P.allow_key("fs_delete", S._describe("fs_delete", (), {"path": "C:\\y"}))
    assert P.is_allowed_timed(key) is True
    data = P._load_allows()
    assert 55 * 60 < data[key] - _time.time() <= 60 * 60


def test_console_pick_mapping(monkeypatch):
    import io as _io
    from aipc import notify as NT

    class _Tty(_io.StringIO):
        def isatty(self):
            return True

    monkeypatch.setattr("sys.stdin", _Tty("2\n"))
    assert NT._console_pick("run_cmd", "dir", 9999999999.0, [10, 60]) == ("timed", 10)
    monkeypatch.setattr("sys.stdin", _Tty("3\n"))
    assert NT._console_pick("run_cmd", "dir", 9999999999.0, [10, 60]) == ("timed", 60)
    monkeypatch.setattr("sys.stdin", _Tty("1\n"))
    assert NT._console_pick("run_cmd", "dir", 9999999999.0, [10, 60]) == "once"
    monkeypatch.setattr("sys.stdin", _Tty("n\n"))
    assert NT._console_pick("run_cmd", "dir", 9999999999.0, [10, 60]) == "deny"


def test_confirm_dialog_variations(monkeypatch):
    from aipc import notify as NT

    # Ветка TaskDialog — только Windows: форсируем, как test_posix форсирует posix.
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(NT, "_can_popup", lambda: True)
    # выбор "1 час" (id 102) при пресетах [10, 60]
    monkeypatch.setattr(NT, "_taskdialog_buttons", lambda *a, **k: 102)
    assert NT.confirm_action("run_cmd", "dir", presets=[10, 60]) == ("timed", 60)
    # "только раз"
    monkeypatch.setattr(NT, "_taskdialog_buttons", lambda *a, **k: 100)
    assert NT.confirm_action("run_cmd", "dir", presets=[10, 60]) == "once"
    # крестик/отмена = запрет
    monkeypatch.setattr(NT, "_taskdialog_buttons", lambda *a, **k: 2)
    assert NT.confirm_action("run_cmd", "dir", presets=[10, 60]) == "deny"
    # таймаут
    monkeypatch.setattr(NT, "_taskdialog_buttons", lambda *a, **k: "timeout")
    assert NT.confirm_action("run_cmd", "dir", presets=[10, 60]) == "timeout"


def test_confirm_legacy_fallback(monkeypatch):
    from aipc import notify as NT

    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(NT, "_can_popup", lambda: True)
    monkeypatch.setattr(NT, "_taskdialog_buttons", lambda *a, **k: "error")
    answers = iter(["yes", "yes"])
    monkeypatch.setattr(NT, "_msgbox_yesno", lambda *a, **k: next(answers))
    assert NT.confirm_action("run_cmd", "dir", presets=[10, 60]) == ("timed", 10)
    answers = iter(["yes", "no"])
    monkeypatch.setattr(NT, "_msgbox_yesno", lambda *a, **k: next(answers))
    assert NT.confirm_action("run_cmd", "dir", presets=[10, 60]) == "once"
