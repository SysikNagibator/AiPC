"""Этап 5: платформенный слой — детект, матрица, швы, гейты."""
import os
import sys

from aipc import platform as PF
from aipc.platform import base as B


def test_name_matches_os():
    n = PF.name()
    if os.name == "nt":
        assert n == "win32"
    else:
        assert n == sys.platform
    assert PF.is_windows() == (os.name == "nt")


def test_capabilities_known():
    for group in ("screen_capture", "files_terminal", "mouse_keyboard",
                  "windows_uia", "browser_cdp", "audio_loopback",
                  "installer_path"):
        st = PF.capability(group)
        assert isinstance(st, str) and st
    assert PF.capability("no_such_group_xyz") == "no"


def test_require_gate():
    if os.name == "nt":
        ok, _ = PF.require("mouse_keyboard")
        assert ok is True
    else:
        ok, reason = PF.require("windows_uia")
        assert ok is False and reason


def test_backends_instantiate():
    b = PF.backend("screen")
    assert isinstance(b, B.ScreenBackend)
    assert isinstance(PF.backend("input"), B.InputBackend)
    assert isinstance(PF.backend("apps"), B.AppBackend)


def test_screen_backend_lists_monitors():
    import pytest

    try:
        mons = PF.backend("screen").monitors()
    except Exception as e:
        pytest.skip(f"no display on this machine: {e}")
    assert isinstance(mons, list) and mons
    assert {"left", "top", "width", "height"} <= set(mons[0].keys())


def test_open_app_uses_backend(monkeypatch):
    from aipc import control as C

    calls = []

    class _Apps:
        def open(self, target):
            calls.append(target)

    monkeypatch.setattr(PF, "backend", lambda kind: _Apps())
    # покроет и nt-ветку, и posix-ветку одним швом
    res = C.open_app("notepad")
    assert res == {"ok": True, "app": "notepad"} and calls == ["notepad"]
    res = C.open_app('  " ` ')
    assert res["reason"] == "bad_arg"
