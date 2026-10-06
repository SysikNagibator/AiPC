"""macOS/Linux: clipboard, пути IDE, ассеты обновлений, confirm без GUI."""
import sys


def test_posix_clipboard_cmds(monkeypatch):
    from aipc import control as C

    import shutil

    monkeypatch.setattr(sys, "platform", "darwin")
    assert C._posix_clipboard_cmds() == (["pbcopy"], ["pbpaste"])
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(shutil, "which", lambda x: "/usr/bin/xclip" if x == "xclip" else None)
    set_cmd, get_cmd = C._posix_clipboard_cmds()
    assert "xclip" in set_cmd[0] and "-o" in get_cmd
    monkeypatch.setattr(shutil, "which", lambda x: "/usr/bin/xsel" if x == "xsel" else None)
    set_cmd, get_cmd = C._posix_clipboard_cmds()
    assert "xsel" in set_cmd[0] and "--output" in get_cmd
    monkeypatch.setattr(shutil, "which", lambda x: None)
    assert C._posix_clipboard_cmds() == (None, None)


def test_base_dirs_linux(tmp_path):
    from aipc import installer as I

    env = {"XDG_CONFIG_HOME": str(tmp_path / ".cfg")}
    appdata, userprofile = I._base_dirs("posix", "linux", str(tmp_path), env)
    assert str(appdata).endswith(".cfg")
    assert str(userprofile) == str(tmp_path)


def test_base_dirs_macos(tmp_path):
    from aipc import installer as I

    appdata, userprofile = I._base_dirs("posix", "darwin", str(tmp_path), {})
    assert str(appdata).endswith("Application Support")
    assert str(userprofile) == str(tmp_path)


def test_base_dirs_windows(tmp_path):
    from aipc import installer as I

    env = {"APPDATA": str(tmp_path / "Roam"), "USERPROFILE": str(tmp_path)}
    appdata, userprofile = I._base_dirs("nt", "win32", str(tmp_path), env)
    assert str(appdata).endswith("Roam")
    assert str(userprofile) == str(tmp_path)


def test_wanted_asset():
    from aipc.maintenance import _wanted_asset

    names = ["AiPC_Win_1.2.exe", "AiPC_Linux_1.2.tar.gz", "SHA256SUMS.txt"]
    if sys.platform == "win32":
        assert _wanted_asset(names) == "AiPC_Win_1.2.exe"
    elif sys.platform == "darwin":
        assert _wanted_asset(names + ["AiPC.dmg"]) in ("AiPC.dmg", None)
    else:
        assert _wanted_asset(names) == "AiPC_Linux_1.2.tar.gz"
    assert _wanted_asset([]) is None
    assert _wanted_asset(["README.md"]) is None


def test_confirm_posix_console(monkeypatch):
    import os

    from aipc import notify as NT

    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(NT, "_console_pick", lambda *a, **k: "once")
    assert NT.confirm_action("run_cmd", "dir") == "once"
    monkeypatch.setattr(NT, "_console_pick", lambda *a, **k: (_ for _ in ()).throw(Exception("x")))
    assert NT.confirm_action("run_cmd", "dir") == "deny"


def test_build_sums(tmp_path):
    import sys as _sys

    _sys.path.insert(0, "tools")
    import build_all

    f = tmp_path / "a.bin"
    f.write_bytes(b"abc" * 100)
    out = build_all.sums([f])
    text = out.read_text(encoding="utf-8")
    assert "a.bin" in text and len(text.split()[0]) == 64
