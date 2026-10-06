"""Этап 3: dry-run/план без записи, выбор IDE, uninstall-откат, auto-register off."""
import json
import os
import sys
from pathlib import Path

from aipc import installer as I


def _home() -> Path:
    return Path(os.environ.get("USERPROFILE"))


def test_plan_no_writes(isolated_home):
    before = {p for p in _home().rglob("*")}
    plan = I.plan_install()
    assert isinstance(plan, list) and len(plan) > 10
    assert any(i["kind"] == "ide" for i in plan)
    assert {p for p in _home().rglob("*")} == before  # ничего не создано
    assert not any((p.suffix == ".bak") for p in _home().rglob("*"))


def test_plan_only_filter(isolated_home):
    plan = I.plan_install(only=["cursor"])
    kinds = {(i["kind"], i["target"].split(":")[0]) for i in plan if i["kind"] == "ide"}
    assert kinds and all("cursor" in n.lower() for _, n in kinds)


def test_plan_preview_text(isolated_home):
    p = _home() / ".cursor" / "mcp.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"mcpServers": {"other": {}}}), encoding="utf-8")
    plan = I.plan_install(only=["Cursor"])
    writes = [i for i in plan if i["action"] == "write"]
    assert writes and "mcpServers.aipc" in writes[0]["detail"]


def test_configure_only_and_create_missing(isolated_home):
    p = _home() / ".cursor" / "mcp.json"
    p.parent.mkdir(parents=True)
    p.write_text("{}", encoding="utf-8")
    rep = I.configure_all_ides("C:\\T\\a.exe", ["mcp"], only=["cursor"])
    names = [n for n, _, _ in rep]
    assert "Cursor" in names and all("cursor" in n.lower() for n in names)
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["mcpServers"]["aipc"]["command"] == "C:\\T\\a.exe"
    # create_missing=True создаёт отсутствующим
    rep = I.configure_all_ides("C:\\T\\a.exe", ["mcp"], only=["claudedesktop"],
                               create_missing=True)
    assert rep and rep[0][1] is True


def test_uninstall_removes_only_ours(isolated_home):
    p = _home() / ".cursor" / "mcp.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"mcpServers": {"other": {"x": 1},
                                            "aipc": {"command": "c", "args": []}}}),
                 encoding="utf-8")
    rep = I.uninstall_mcp(only=["cursor"])
    assert rep[0][1] is True
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["mcpServers"] == {"other": {"x": 1}}


def test_uninstall_skips_broken_json(isolated_home):
    p = _home() / ".cursor" / "mcp.json"
    p.parent.mkdir(parents=True)
    p.write_text("{broken", encoding="utf-8")
    rep = I.uninstall_mcp(only=["cursor"])
    assert rep[0][1] is False
    assert p.read_text(encoding="utf-8") == "{broken"  # не затёрли


def test_uninstall_codex_block(isolated_home):
    toml = _home() / ".codex" / "config.toml"
    toml.parent.mkdir(parents=True)
    toml.write_text('model = "x"\n\n[mcp_servers.aipc]\ncommand = "c"\nargs = []\n',
                    encoding="utf-8")
    rep = I.uninstall_mcp(only=["codexcli"])
    assert rep and rep[0][1] is True
    text = toml.read_text(encoding="utf-8")
    assert "[mcp_servers.aipc]" not in text and 'model = "x"' in text


import pytest


@pytest.mark.skipif(os.name != "nt", reason="реестр Windows: только на nt")
def test_remove_from_path_fake_winreg(monkeypatch):
    store = {"Path": "C:\\Win;C:\\Program Files\\AiPC;C:\\X"}

    class _Key:
        pass

    class _FakeReg:
        HKEY_LOCAL_MACHINE = 0
        KEY_READ = 1
        KEY_WRITE = 2
        REG_EXPAND_SZ = 3

        def OpenKey(self, *a):
            return _Key()

        def QueryValueEx(self, k, n):
            return store["Path"], 1

        def SetValueEx(self, k, n, r, t, v):
            store["Path"] = v

        def CloseKey(self, k):
            pass

    monkeypatch.setitem(sys.modules, "winreg", _FakeReg())
    ok, msg = I.remove_from_system_path("C:\\Program Files\\AiPC")
    assert ok and "C:\\Program Files\\AiPC" not in store["Path"]
    assert "C:\\Win" in store["Path"]
    ok, msg = I.remove_from_system_path("C:\\Program Files\\AiPC")
    assert ok and "нет в PATH" in msg


def test_auto_register_off_by_default(isolated_home):
    from aipc.config import load_config

    assert load_config().get("installer", {}).get("auto_register") is False
    assert I._auto_register_enabled() is False
    before = {p for p in _home().rglob("*")}
    I.ensure_installed()  # dev-режим: без auto_register ничего не пишет
    assert {p for p in _home().rglob("*")} == before


def test_cli_list_and_dryrun(isolated_home, capsys):
    from aipc.__main__ import main

    assert main(["install", "--list-ides"]) == 0
    assert "Cursor" in capsys.readouterr().out
    before = {p for p in _home().rglob("*")}
    assert main(["install", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "[skip]" in out or "[add]" in out
    assert {p for p in _home().rglob("*")} == before


def test_cli_uninstall_yes(isolated_home, capsys, monkeypatch, tmp_path):
    from aipc.__main__ import main

    monkeypatch.setattr(I, "remove_from_system_path", lambda p: (True, "mock"))
    pf = tmp_path / "pf"
    pf.mkdir()
    (pf / "AiPC_Win_9.9.exe").write_bytes(b"x")
    (pf / "aipc.bat").write_text("x", encoding="utf-8")
    monkeypatch.setattr(I, "install_dir", lambda: str(pf))
    p = _home() / ".cursor" / "mcp.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"mcpServers": {"aipc": {"command": "c"}}}), encoding="utf-8")
    assert main(["uninstall", "--yes", "--ide", "cursor"]) == 0
    d = json.loads(p.read_text(encoding="utf-8"))
    assert "aipc" not in d.get("mcpServers", {})
    assert not (pf / "AiPC_Win_9.9.exe").exists()
    assert not (pf / "aipc.bat").exists()
