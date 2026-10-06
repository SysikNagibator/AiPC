"""Этап 1.5: JSON-аудит, aipc audit, panic, лимиты скорости и зацикливания."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from aipc import server as S
from aipc.audit import log_event, tail_events, tail_log
from aipc.config import config_dir, load_config, save_config


@pytest.fixture(autouse=True)
def clean_state():
    S._reset_limits()
    S._reset_taint()
    yield
    S._reset_limits()
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


def test_log_event_json_lines():
    log_event("t_probe", {"cmd": "dir", "secret": "ghp_deadbeef9"}, ok=True,
              note="n", mode="auto", decision="auto-allow")
    ev = tail_events(5, tool="t_probe")[-1]
    assert ev["tool"] == "t_probe" and ev["ok"] is True
    assert ev["mode"] == "auto" and ev["decision"] == "auto-allow"
    assert "ts" in ev and "args" in ev
    assert "ghp_deadbeef9" not in json.dumps(ev, ensure_ascii=False)


def test_tail_events_filters_and_skips_legacy():
    p = config_dir() / "audit.log"
    with p.open("a", encoding="utf-8") as f:
        f.write("legacy text line without json\n")
    log_event("t_filter_me", {"x": 1}, ok=True)
    evs = tail_events(50)
    assert all(isinstance(e, dict) for e in evs)
    assert any(e["tool"] == "t_filter_me" for e in evs)
    assert tail_events(50, tool="t_filter_me", since="2999-01-01") == []
    assert tail_events(50, tool="no_such_tool_xyz") == []


def test_panic_blocks_all(monkeypatch):
    from aipc import panic as PN

    assert PN.is_set() is False
    PN.set_panic("тест")
    try:
        assert PN.is_set() is True
        assert "тест" in PN.panic_reason()
        res = S._wrap("screen_see", lambda *a, **k: {"ok": True})
        assert res["reason"] == "denied" and "PANIC" in res["error"]
        # даже read-only чтение и служебные — всё стоит
        res = S._wrap("run_cmd", lambda *a, **k: {"ok": True}, cmd="dir")
        assert "PANIC" in res["error"]
    finally:
        assert PN.clear_panic() is True
        assert PN.is_set() is False
    res = S._wrap("screen_see", lambda *a, **k: {"ok": True})
    assert res == {"ok": True}


def test_rate_limit(monkeypatch):
    old = _set_safety(max_calls_per_min=3)
    try:
        fn = lambda *a, **k: {"ok": True}
        for _ in range(3):
            assert S._wrap("sys_info", fn) == {"ok": True}
        res = S._wrap("sys_info", fn)
        assert res["reason"] == "rate_limited" and "hint" in res
    finally:
        _restore_safety(old)


def test_loop_guard_and_reset():
    old = _set_safety(loop_repeat=3, max_calls_per_min=10000)
    try:
        fn = lambda *a, **k: {"ok": True}
        assert S._wrap("sys_info", fn) == {"ok": True}
        assert S._wrap("sys_info", fn) == {"ok": True}
        res = S._wrap("sys_info", fn)
        assert res["reason"] == "loop_guard" and "hint" in res
        # другой вызов сбрасывает счётчик
        assert S._wrap("net_check", fn, host="h") == {"ok": True}
        assert S._wrap("sys_info", fn) == {"ok": True}
    finally:
        _restore_safety(old)


def test_panic_cli():
    from aipc.__main__ import main

    assert main(["panic", "тест cli"]) == 0
    from aipc import panic as PN

    assert PN.is_set() is True
    assert main(["panic", "--off"]) == 0
    assert PN.is_set() is False


def test_audit_cli(capsys):
    from aipc.__main__ import main

    log_event("t_cli_probe", {"a": 1}, ok=True)
    assert main(["audit", "--tail", "5", "--tool", "t_cli_probe"]) == 0
    out = capsys.readouterr().out
    assert "t_cli_probe" in out
    assert main(["audit", "--tail", "abc"]) == 2


class _Big(BaseHTTPRequestHandler):
    SIZE = 3 * 1024 * 1024

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", str(self.SIZE))
        self.end_headers()
        self.wfile.write(b"x" * self.SIZE)

    def log_message(self, *a):
        pass


def test_download_cap(tmp_path):
    from aipc.net import download_file

    srv = HTTPServer(("127.0.0.1", 0), _Big)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        old = _set_safety(max_download_mb=1)
        try:
            url = f"http://127.0.0.1:{srv.server_port}/big.bin"
            res = download_file(url, str(tmp_path / "big.bin"))
            assert res["reason"] == "too_big"
            assert not (tmp_path / "big.bin").exists()
        finally:
            _restore_safety(old)
    finally:
        srv.shutdown()


def test_watcher_idempotent():
    from aipc.panic import start_watcher

    assert isinstance(start_watcher(), bool)
    assert start_watcher() is True
