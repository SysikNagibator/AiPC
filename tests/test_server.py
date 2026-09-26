"""MCP-сервер: создаётся, tools на месте, схемы строгие, read-only gate."""
from aipc.server import SYSTEM_PROMPT, create_server


def test_create_server():
    assert create_server() is not None


def test_tool_functions_exist():
    from aipc import browser as B
    from aipc import control as C
    from aipc import net as N
    from aipc import os_ops as O
    from aipc import sysinfo as S
    from aipc import vision as V

    for mod, names in [
        (V, ["screen_see", "screen_region", "ui_snapshot", "ui_find", "assert_ui", "windows_list",
             "window_focus", "window_manage", "window_find", "get_active_window", "wait_for_window",
             "wait_for_ui_element", "wait_for_change", "screenshot_diff", "screen_info"]),
        (C, ["mouse_move", "mouse_click", "mouse_drag", "mouse_double_click", "mouse_right_click",
             "mouse_middle_click", "scroll", "type_text", "press_key", "key_down", "key_up",
             "clipboard_set", "clipboard_get", "clipboard_set_image", "clipboard_get_image",
             "sleep", "open_app", "focus_type"]),
        (O, ["fs_list", "fs_read", "fs_write", "fs_find", "fs_stat", "fs_mkdir", "fs_delete",
             "fs_move", "run_cmd", "process_list", "process_find", "wait_for_process"]),
        (B, ["browser_tabs", "browser_goto", "browser_eval", "browser_active_tab",
             "browser_close_tab", "browser_history_search"]),
        (N, ["web_search_pc", "ssh_exec", "ssh_sftp_get", "ssh_sftp_put", "download_file"]),
        (S, ["sys_info", "net_check", "env_get"]),
    ]:
        for n in names:
            assert callable(getattr(mod, n, None)), f"{mod.__name__}.{n}"


def test_prompt_mentions_discipline():
    assert "focus_type" in SYSTEM_PROMPT
    assert "не говори" in SYSTEM_PROMPT


def test_readonly_gate():
    from aipc.config import load_config, save_config
    from aipc.server import _wrap

    cfg = load_config()
    old = cfg.get("mode")
    try:
        cfg["mode"] = "read-only"
        save_config(cfg)
        from aipc import os_ops as O

        assert _wrap("run_cmd", O.run_cmd, "echo hi").get("reason") == "denied"
        assert _wrap("fs_write", O.fs_write, "x.txt", "y").get("reason") == "denied"
        from aipc import vision as V

        assert _wrap("fs_read", O.fs_read, "pyproject.toml").get("ok") in (True, False)
        assert V.screen_see.__name__ == "screen_see"
    finally:
        cfg["mode"] = old
        save_config(cfg)


def test_audit_truncation():
    from aipc.server import _safe_params

    p = _safe_params({"text": "x" * 5000})
    assert len(p["text"]) < 600


def test_encode_bytes():
    from PIL import Image

    from aipc.vision import _encode_bytes

    img = Image.new("RGB", (32, 20), (10, 20, 30))
    raw = _encode_bytes(img)
    assert raw[:2] == b"\xff\xd8"  # JPEG magic


def test_compact_ui_shape():
    import os

    import pytest

    if os.name != "nt":
        pytest.skip("UI tree needs Windows")
    from aipc.vision import _collect_ui

    nodes, err = _collect_ui(0, "", "", 15, "active")
    assert err == "" or nodes
    if nodes:
        assert set(nodes[0].keys()) == {"t", "n", "x", "y", "o"}
