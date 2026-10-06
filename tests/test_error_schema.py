"""Этап 4.3: единый формат ошибок {"ok": false, "reason": ..., "hint"?}."""
from aipc.errors import denied, err


def _check(result, want_reason=None):
    assert isinstance(result, dict), result
    assert result.get("ok") is False
    assert isinstance(result.get("reason"), str) and result["reason"]
    assert isinstance(result.get("error"), str) and result["error"]
    if want_reason:
        assert result["reason"] == want_reason, result
    return result


def test_err_helper_shape():
    d = err("not_found", "нет такого", "создай сначала")
    assert d == {"ok": False, "reason": "not_found", "error": "нет такого",
                 "hint": "создай сначала"}
    d = denied("запрет")
    assert d == {"ok": False, "reason": "denied", "error": "запрет"}


def test_fs_denials_schema(tmp_path):
    from aipc import os_ops as O

    _check(O.fs_read("C:\\Users\\x\\.ssh\\id_rsa"), "denied")
    r = _check(O.fs_read(str(tmp_path / "нет-такого.txt")), "not_found")
    assert "hint" not in r  # hint только у запретов/подсказываемых
    _check(O.fs_write("C:\\Windows\\System32\\x.txt", "t"), "denied")
    _check(O.fs_delete("C:\\", recursive=True), "denied")


def test_denied_have_hints(tmp_path):
    from aipc import os_ops as O

    r = _check(O.fs_read("C:\\Users\\x\\.ssh\\id_rsa"), "denied")
    assert r["hint"]
    r = _check(O.fs_write("C:\\Windows\\System32\\x.txt", "t"), "denied")
    assert r["hint"]


def test_cmd_denied_schema():
    from aipc import os_ops as O

    r = _check(O.run_cmd("mimikatz sekurlsa"), "denied")
    assert r.get("hint")


def test_net_denied_schema():
    from aipc.net import ssh_exec, ssh_sftp_put

    try:
        import paramiko  # noqa
    except ImportError:
        return
    _check(ssh_exec("h", "u", "mimikatz"), "denied")
    r = _check(ssh_sftp_put("h", "u", "C:\\Users\\x\\.ssh\\id_rsa", "/tmp/x"),
               "denied")
    assert r.get("hint")


def test_env_denied_schema():
    from aipc.sysinfo import env_get

    r = _check(env_get("MY_API_TOKEN"), "denied")
    assert r.get("hint")


def test_wrap_denials_schema(monkeypatch):
    from aipc.config import load_config, save_config
    from aipc import server as S

    cfg = load_config()
    old = cfg.get("mode")
    try:
        cfg["mode"] = "read-only"
        save_config(cfg)
        r = _check(S._wrap("run_cmd", lambda *a, **k: {"ok": True}, cmd="dir"),
                   "denied")
        assert r.get("hint")
    finally:
        cfg["mode"] = old
        save_config(cfg)
