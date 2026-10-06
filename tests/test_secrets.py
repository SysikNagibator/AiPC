"""Этап 1.4: секреты — deny-пути, opt-in ключей, маскирование, env-обходы."""
import pytest

from aipc.audit import log_event, mask_secrets, tail_log
from aipc.config import load_config, save_config
from aipc.policy import check_cmd_allowed as C
from aipc.policy import check_path_allowed as P
from aipc.policy import is_secret_name


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


SECRET_PATHS = [
    "C:\\Users\\x\\.ssh\\config",
    "C:\\Users\\x\\.ssh\\known_hosts",
    "C:\\Users\\x\\.aws\\credentials",
    "C:\\Users\\x\\.kube\\config",
    "C:\\proj\\.env",
    "C:\\proj\\.env.local",
    "C:\\Users\\x\\wallet.dat",
    "C:\\Users\\x\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Local State",
    "C:\\Users\\x\\AppData\\Roaming\\Telegram Desktop\\tdata\\abc",
    "C:\\Users\\x\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Local Storage\\leveldb\\001.ldb",
]


def test_secret_paths_denied():
    for p in SECRET_PATHS:
        ok, err = P(p)
        assert not ok, f"секретный путь открыт: {p}"


def test_ssh_opt_in():
    old = _set_safety(allow_ssh_keys=False)
    try:
        ok, _ = P("C:\\Users\\x\\.ssh\\id_rsa")
        assert not ok
        ok, _ = P("C:\\Users\\x\\.ssh\\id_rsa")
        assert not ok
    finally:
        _restore_safety(old)
    old = _set_safety(allow_ssh_keys=True)
    try:
        ok, _ = P("C:\\Users\\x\\.ssh\\id_rsa")
        assert not ok  # каталог .ssh всё равно закрыт целиком
        ok, _ = P("C:\\deploy\\id_rsa")
        assert ok, "opt-in должен открывать ключи вне запретных каталогов"
        ok, _ = P("C:\\deploy\\vault.kdbx")
        assert not ok, "kdbx не входит в opt-in"
    finally:
        _restore_safety(old)


def test_mask_patterns():
    assert "[PRIVATE KEY REDACTED]" in mask_secrets(
        "k\n-----BEGIN RSA PRIVATE KEY-----\nABC\n-----END RSA PRIVATE KEY-----\n")
    assert "ghp_***" in mask_secrets("token ghp_deadbeef123 end")
    assert "gho_***" in mask_secrets("x gho_abc end")
    assert "sk-***" in mask_secrets("k sk-ant-abc123-xyz end")
    assert "AKIA***" in mask_secrets("id AKIAIOSFODNN7EXAMPLE end")
    assert "xox***" in mask_secrets("t xoxb-123-abc end")
    assert ":***@" in mask_secrets("u https://user:s3cret@host/x end")
    assert "password=***" in mask_secrets("login password=sup3r end")
    # обычный текст не портится
    assert mask_secrets("echo hello world") == "echo hello world"


def test_audit_log_masks():
    log_event("t_probe", {"cmd": "login password=sup3r", "tok": "ghp_deadbeef1"}, ok=True)
    lines = tail_log(5)
    blob = "\n".join(lines)
    assert "sup3r" not in blob
    assert "ghp_deadbeef1" not in blob
    assert "password=***" in blob or "ghp_***" in blob


def test_env_get_masks_value(monkeypatch):
    from aipc.sysinfo import env_get

    monkeypatch.setenv("AIPC_TEST_PLAIN", "just words here")
    r = env_get("AIPC_TEST_PLAIN")
    assert r["ok"] and r["value"] == "just words here"
    monkeypatch.setenv("AIPC_TEST_PLAIN2", "prefix ghp_deadbeef2 suffix")
    r = env_get("AIPC_TEST_PLAIN2")
    assert r["ok"] and "ghp_deadbeef2" not in r["value"] and "ghp_***" in r["value"]
    r = env_get("GH_TOKEN_XYZ")
    assert r["reason"] == "denied"


def test_fs_read_masks(tmp_path):
    from aipc.os_ops import fs_read

    f = tmp_path / "notes.txt"
    f.write_text("deploy token: ghp_deadbeef3\ndone\n", encoding="utf-8")
    r = fs_read(str(f))
    assert r["ok"] and "ghp_deadbeef3" not in r["text"]


def test_run_cmd_env_bypass_blocked():
    for c in ["echo $env:GH_TOKEN", "echo %GH_TOKEN%", "printenv",
              "printenv GH_TOKEN", "$env:AWS_SECRET"]:
        ok, err = C(c)
        assert not ok, f"обход env: {c}"
    for c in ["echo %PATH%", "echo $env:USERNAME", "printenv PATH", "set FOO=bar"]:
        ok, err = C(c)
        assert ok, f"ложное срабатывание: {c} ({err})"


def test_is_secret_name():
    assert is_secret_name("GH_TOKEN") and is_secret_name("db_password")
    assert not is_secret_name("PATH") and not is_secret_name("")
