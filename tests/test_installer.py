"""MCP-мерж конфигов IDE: аккуратность, идемпотентность, JSONC/TOML/YAML."""
import json
from pathlib import Path

from aipc import installer as I


def test_merge_new_file(tmp_path):
    p = tmp_path / "mcp.json"
    ok, _ = I.merge_mcp_file(p, "C:\\Tools\\aipc.exe", ["mcp"])
    assert ok
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["mcpServers"]["aipc"] == {"command": "C:\\Tools\\aipc.exe", "args": ["mcp"]}


def test_merge_preserves_and_idempotent(tmp_path):
    p = tmp_path / "mcp.json"
    p.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}), encoding="utf-8")
    I.merge_mcp_file(p, "C:\\Tools\\aipc.exe", ["mcp"])
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["mcpServers"]["other"] == {"command": "x"}
    assert "aipc" in d["mcpServers"]
    ok, msg = I.merge_mcp_file(p, "C:\\Tools\\aipc.exe", ["mcp"])
    assert ok and "уже настроено" in msg


def test_merge_broken_json(tmp_path):
    p = tmp_path / "mcp.json"
    p.write_text("{broken", encoding="utf-8")
    ok, _ = I.merge_mcp_file(p, "C:\\Tools\\aipc.exe", ["mcp"])
    assert ok


def test_jsonc_with_comments(tmp_path):
    from aipc.installer import _strip_jsonc

    t = '{\n// comment\n"a": 1, /* block */\n"b": [1, 2,],\n"u": "https://x.com/a//b"\n}'
    d = json.loads(_strip_jsonc(t))
    assert d == {"a": 1, "b": [1, 2], "u": "https://x.com/a//b"}


def test_writers_opencode_zed_vscode(tmp_path):
    oc = tmp_path / "opencode.json"
    oc.write_text('{"theme": "dark"}', encoding="utf-8")
    ok, _ = I.merge_mcp_file(oc, "C:\\T\\aipc.exe", ["mcp"], "opencode")
    assert ok
    d = json.loads(oc.read_text(encoding="utf-8"))
    assert d["mcp"]["aipc"]["command"] == ["C:\\T\\aipc.exe", "mcp"] and d["theme"] == "dark"

    zed = tmp_path / "z.json"
    zed.write_text('{"tab_size": 2}', encoding="utf-8")
    I.merge_mcp_file(zed, "C:\\T\\aipc.exe", ["mcp"], "zed")
    d = json.loads(zed.read_text(encoding="utf-8"))
    assert d["context_servers"]["aipc"]["args"] == ["mcp"] and d["tab_size"] == 2

    vs = tmp_path / "v.json"
    vs.write_text("{}", encoding="utf-8")
    I.merge_mcp_file(vs, "C:\\T\\aipc.exe", ["mcp"], "vscode-mcp")
    d = json.loads(vs.read_text(encoding="utf-8"))
    assert d["mcp"]["servers"]["aipc"]["command"] == "C:\\T\\aipc.exe"


def test_codex_toml_and_continue(tmp_path):
    toml = tmp_path / "config.toml"
    toml.write_text('model = "x"\n', encoding="utf-8")
    ok, _ = I._append_codex_toml(toml, "C:\\T\\aipc.exe", ["mcp"])
    assert ok
    text = toml.read_text(encoding="utf-8")
    assert "[mcp_servers.aipc]" in text and 'model = "x"' in text
    ok, msg = I._append_codex_toml(toml, "C:\\T\\aipc.exe", ["mcp"])
    assert "уже настроено" in msg

    y = tmp_path / "aipc.yaml"
    ok, _ = I._write_continue_yaml(y, "C:\\T\\aipc.exe", ["mcp"])
    assert ok and "command: C:\\T\\aipc.exe" in y.read_text(encoding="utf-8")


def test_only_if_snapshot(isolated_home):
    # main пишется всегда, alt — только если main был ДО запуска
    rep = I.configure_all_ides("C:\\Tools\\aipc.exe", ["mcp"])
    names = [n for n, _, _ in rep]
    assert "Antigravity" in names and "Cursor" in names
    assert "Antigravity-alt" not in names and "Cursor-alt" not in names
    rep2 = I.configure_all_ides("C:\\Tools\\aipc.exe", ["mcp"])
    assert "Antigravity-alt" in [n for n, _, _ in rep2]
    rep3 = I.configure_all_ides("C:\\Tools\\aipc.exe", ["mcp"])
    assert all(("уже настроено" in m or "проверь вручную" in m) for _, _, m in rep3)


def test_safety_upgrade(isolated_home):
    from aipc.config import SAFETY_VERSION, load_config

    cfg = load_config()
    assert cfg["safety"].get("version") == SAFETY_VERSION
    assert "mimikatz" in " ".join(cfg["safety"]["deny_cmd"])
