"""Этап 1.2: попытки обхода deny-листов обязаны ловиться."""
import pytest

from aipc.config import load_config, save_config
from aipc.policy import (check_cmd_allowed as C, check_path_allowed as P,
                         cmd_allowlisted, cmd_needs_confirm, normalize_cmd,
                         run_cmd_policy)


BYPASS_DENY = [
    "echo ok && mimikatz",
    "dir; ntdsutil",
    "echo a | sekurlsa",
    "ping 1.1.1.1 & vssadmin delete shadows",
    "echo x || bcdedit",
    '"mimikatz"',
    "'sekurlsa'",
    '"mi"mikatz',
    "po^wershell -enc xxx",
    "powershell -e aGVsbG8=",
    'powershell /e "x"',
    "pwsh -enc xxx",
    "pwsh -e xxx",
    "IEX (New-Object Net.WebClient)",
    "iex $x",
    "[Convert]::FromBase64String('xx')",
    "Invoke-Expression $cmd",
    "type C:\\Users\\x\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Login Data",
    "Get-Content C:\\Users\\x\\.ssh\\id_rsa",
    "gc C:\\keys\\vault.pfx",
    "cat C:\\Windows\\System32\\cmd.exe",
    "set",
    "set PATH",
    "Get-ChildItem Env:",
    "gci env:",
    "dir env:",
    "[Environment]::GetEnvironmentVariables()",
]

ALLOW_STILL = [
    "echo hello",
    "dir C:\\Users",
    "python script.py",
    "set FOO=bar",
    "git status",
]


def test_bypass_chains_quotes_encoded_denied():
    for c in BYPASS_DENY:
        ok, err = C(c)
        assert not ok, f"ОБХОД ПРОПУЩЕН: {c} ({err})"


def test_legit_still_allowed():
    for c in ALLOW_STILL:
        ok, err = C(c)
        assert ok, f"ложное срабатывание: {c} ({err})"


def test_env_var_expansion_caught(monkeypatch):
    monkeypatch.setenv("AIPC_TEST_SYS", "C:\\Windows\\System32")
    ok, _ = C("%AIPC_TEST_SYS%\\cmd.exe")
    assert not ok
    monkeypatch.setenv("AIPC_TEST_HOME", "C:\\Users\\x\\.ssh")
    ok, _ = C("type $env:AIPC_TEST_HOME\\id_rsa")
    assert not ok


def test_normalize_splits_segments():
    segs = normalize_cmd("echo a && dir; ls | sort")
    assert "echo a" in segs and "dir" in segs and "sort" in segs


def test_allowlist_mode():
    cfg = load_config()
    old = dict(cfg)
    try:
        cfg.setdefault("safety", {})["run_cmd_policy"] = "allowlist"
        cfg["safety"]["cmd_allowlist"] = ["dir", "echo"]
        save_config(cfg)
        assert run_cmd_policy() == "allowlist"
        assert cmd_allowlisted("dir C:\\x") is True
        assert cmd_allowlisted("echo hi && dir") is True
        assert cmd_allowlisted("del C:\\x") is False
        assert cmd_needs_confirm("del C:\\x") is True
        assert cmd_needs_confirm("dir C:\\x") is False
        # deny-лист всё равно работает поверх allowlist
        ok, _ = C("dir C:\\Windows\\System32\\x")
        assert not ok
    finally:
        save_config(old)


def test_allowlist_default_off():
    assert run_cmd_policy() == "deny"
    assert cmd_needs_confirm("anything at all") is False


def test_ssh_exec_denied_without_network():
    from aipc.net import ssh_exec

    res = ssh_exec("h", "u", "mimikatz sekurlsa")
    assert res["reason"] == "denied"


def test_sftp_put_secret_path_blocked():
    from aipc.net import ssh_sftp_put

    try:
        import paramiko  # noqa
    except ImportError:
        pytest.skip("нет paramiko")
    res = ssh_sftp_put("h", "u", "C:\\Users\\x\\.ssh\\id_rsa", "/tmp/x")
    assert res["reason"] == "denied"
