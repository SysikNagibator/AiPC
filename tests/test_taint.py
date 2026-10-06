"""Этап 1.3: untrusted-маркеры и taint-guard (подтверждение даже в auto)."""
import pytest

from aipc.config import load_config, save_config
from aipc import server as S


@pytest.fixture(autouse=True)
def clean_taint():
    S._reset_taint()
    yield
    S._reset_taint()


def _set_safety(**kw):
    cfg = load_config()
    old = {k: cfg.get("safety", {}).get(k) for k in kw}
    cfg.setdefault("safety", {}).update(kw)
    save_config(cfg)
    return old


def _restore_safety(old: dict):
    cfg = load_config()
    for k, v in old.items():
        if v is None:
            cfg.get("safety", {}).pop(k, None)
        else:
            cfg.setdefault("safety", {})[k] = v
    save_config(cfg)


def _set_mode(mode: str):
    cfg = load_config()
    old = cfg.get("mode")
    cfg["mode"] = mode
    save_config(cfg)
    return old


def test_wrap_marks_untrusted_dict():
    res = S._wrap("fs_read", lambda *a, **k: {"ok": True, "text": "x"},
                  _untrusted_source="fs_read")
    assert res["untrusted"] is True and res["source"] == "fs_read"


def test_wrap_no_mark_without_source():
    res = S._wrap("fs_read", lambda *a, **k: {"ok": True, "text": "x"})
    assert "untrusted" not in res


def test_wrap_failed_not_marked():
    res = S._wrap("fs_read", lambda *a, **k: {"ok": False, "reason": "not_found"},
                  _untrusted_source="fs_read")
    assert "untrusted" not in res


def test_note_and_window():
    old = _set_safety(taint_window=3, taint_guard=True)
    try:
        assert S._is_tainted() is False
        S._note_result({"ok": True})
        assert S._is_tainted() is False
        S._note_result({"ok": True, "untrusted": True, "source": "fs_read"})
        assert S._is_tainted() is True
        # окно 3: три чистых вымывают taint
        S._note_result({"ok": True})
        S._note_result({"ok": True})
        S._note_result({"ok": True})
        assert S._is_tainted() is False
    finally:
        _restore_safety(old)


def test_taint_guard_off():
    old = _set_safety(taint_guard=False)
    try:
        S._note_result({"ok": True, "untrusted": True})
        assert S._is_tainted() is False
    finally:
        _restore_safety(old)


def test_auto_tainted_exec_needs_confirm(monkeypatch):
    old_mode = _set_mode("auto")
    old = _set_safety(taint_guard=True, taint_window=10)
    try:
        S._note_result({"ok": True, "untrusted": True, "source": "web_search"})
        calls = []
        monkeypatch.setattr("aipc.notify.confirm_action",
                            lambda *a, **k: calls.append(1) or "once")
        res = S._wrap("run_cmd", lambda *a, **k: {"ok": True}, cmd="dir")
        assert res == {"ok": True} and calls == [1]
    finally:
        _set_mode(old_mode)
        _restore_safety(old)


def test_auto_tainted_deny_blocks(monkeypatch):
    old_mode = _set_mode("auto")
    old = _set_safety(taint_guard=True, taint_window=10)
    try:
        S._note_result({"ok": True, "untrusted": True, "source": "browser_eval"})
        ran = []
        monkeypatch.setattr("aipc.notify.confirm_action", lambda *a, **k: "deny")
        res = S._wrap("ssh_exec", lambda *a, **k: ran.append(1) or {"ok": True},
                      host="h", username="u", cmd="ls")
        assert res["reason"] == "denied" and ran == []
    finally:
        _set_mode(old_mode)
        _restore_safety(old)


def test_auto_clean_no_confirm(monkeypatch):
    old_mode = _set_mode("auto")
    old = _set_safety(taint_guard=True, taint_window=10)
    try:
        def _boom(*a, **k):
            raise AssertionError("confirm не должен вызываться без taint")

        monkeypatch.setattr("aipc.notify.confirm_action", _boom)
        res = S._wrap("run_cmd", lambda *a, **k: {"ok": True}, cmd="dir")
        assert res == {"ok": True}
    finally:
        _set_mode(old_mode)
        _restore_safety(old)


def test_tainted_read_needs_no_confirm(monkeypatch):
    old_mode = _set_mode("auto")
    old = _set_safety(taint_guard=True, taint_window=10)
    try:
        S._note_result({"ok": True, "untrusted": True})
        monkeypatch.setattr("aipc.notify.confirm_action",
                            lambda *a, **k: (_ for _ in ()).throw(
                                AssertionError("read не требует confirm")))
        res = S._wrap("screen_see", lambda *a, **k: {"ok": True})
        assert res == {"ok": True}
    finally:
        _set_mode(old_mode)
        _restore_safety(old)


def test_image_result_marks_meta():
    srv = S.create_server()
    assert srv is not None  # сервер собирается с маркерами
    from aipc.server import _result_is_untrusted

    assert _result_is_untrusted([{"untrusted": True}]) is True
    assert _result_is_untrusted({"ok": True}) is False
    assert _result_is_untrusted([{"ok": True}]) is False
