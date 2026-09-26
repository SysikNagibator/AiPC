"""Матрица политики безопасности."""
from aipc.policy import check_cmd_allowed as C
from aipc.policy import check_path_allowed as P

DENY_CMD = [
    "format C: /q",
    "FORMAT c:",
    "po^wershell -enc xxx",
    "mimikatz sekurlsa",
    "vssadmin delete shadows",
    "net localgroup administrators x /add",
    "certutil -decode a b",
    "rd /s /q C:\\Windows\\Temp",
    "wmic shadowcopy delete",
]
ALLOW_CMD = ["echo hello", "dir C:\\Users", "python script.py"]

DENY_PATH = [
    "C:\\Users\\x\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Login Data",
    "C:\\Users\\x\\.ssh\\id_rsa",
    "C:\\Windows\\System32\\cmd.exe",
    "C:\\keys\\backup.pfx",
    "vault.pfx",
]
ALLOW_PATH = ["C:\\Users\\Developer\\Desktop\\notes.txt", "project\\app.py"]


def test_deny_cmd():
    for c in DENY_CMD:
        ok, _ = C(c)
        assert not ok, c


def test_allow_cmd():
    for c in ALLOW_CMD:
        ok, _ = C(c)
        assert ok, c


def test_deny_path():
    for p in DENY_PATH:
        ok, _ = P(p)
        assert not ok, p


def test_allow_path():
    for p in ALLOW_PATH:
        ok, _ = P(p)
        assert ok, p
