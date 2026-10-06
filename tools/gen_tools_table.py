"""Сверка tools.json с сервером и README: число и имена инструментов.

Использование:
  python tools/gen_tools_table.py --check      # проверки для CI
  python tools/gen_tools_table.py --gen-table  # markdown-таблица групп в stdout
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Группы README: имя -> ожидаемые tools (проверяем покрытие всех 70).
GROUPS_EN = {
    "Vision": ["screen_see", "screen_region", "screen_burst", "window_shot",
               "pixel_color", "ui_snapshot", "ui_find", "assert_ui",
               "windows_list", "window_focus", "window_manage", "window_find",
               "get_active_window", "wait_for_window", "wait_for_ui_element",
               "wait_for_change", "screenshot_diff", "screen_info"],
    "Mouse & keyboard": ["mouse_move", "mouse_click", "mouse_drag",
                         "mouse_double_click", "mouse_right_click",
                         "mouse_middle_click", "mouse_position", "scroll",
                         "type_text", "press_key", "key_down", "key_up",
                         "clipboard_set", "clipboard_get", "clipboard_set_image",
                         "clipboard_get_image", "sleep", "open_app", "focus_type"],
    "Browser": ["browser_tabs", "browser_goto", "browser_eval",
                "browser_active_tab", "browser_close_tab", "browser_history_search"],
    "Files & system": ["fs_list", "fs_read", "fs_write", "fs_find", "fs_stat",
                       "fs_mkdir", "fs_delete", "fs_move", "run_cmd",
                       "process_list", "process_find", "wait_for_process",
                       "download_file"],
    "Network & machine": ["web_search_pc", "ssh_exec", "ssh_sftp_get",
                          "ssh_sftp_put", "sys_info", "net_check", "env_get"],
    "Human & debug": ["notify_user", "ask_user", "aipc_status", "logs_tail"],
    "Audio": ["audio_listen"],
    "Video": ["video_info", "video_frames"],
}


def server_tools() -> list[str]:
    src = (ROOT / "aipc" / "server.py").read_text(encoding="utf-8")
    return re.findall(r"@_tool\(\)\s*\n\s*def (\w+)", src)


def json_tools() -> list[str]:
    d = json.loads((ROOT / "tools.json").read_text(encoding="utf-8"))
    return [t["name"] for t in d["tools"]]


def main() -> int:
    srv, js = server_tools(), json_tools()
    errs = []
    if len(srv) != len(js):
        errs.append(f"число: server={len(srv)} tools.json={len(js)}")
    missing_js = sorted(set(srv) - set(js))
    missing_srv = sorted(set(js) - set(srv))
    if missing_js:
        errs.append(f"нет в tools.json: {missing_js}")
    if missing_srv:
        errs.append(f"нет в server.py: {missing_srv}")
    # Группы покрывают все tools без пересечений и пропусков.
    covered = [t for g in GROUPS_EN.values() for t in g]
    if sorted(covered) != sorted(srv):
        errs.append(f"группы != tools: лишние={sorted(set(covered) - set(srv))} "
                    f"пропущены={sorted(set(srv) - set(covered))}")
    if "--gen-table" in sys.argv:
        print("| Group | N | Tools |")
        print("|---|---|---|")
        for g, tools in GROUPS_EN.items():
            print(f"| {g} | {len(tools)} | " + ", ".join(f"`{t}`" for t in tools) + " |")
        return 0
    # Сверка с README: бейдж, заголовок, суммы групп.
    for readme in ("README.md", "README_RU.md"):
        text = (ROOT / readme).read_text(encoding="utf-8")
        n = len(srv)
        if f"tools-{n}-brightgreen" not in text and f"tools-{n}-" not in text:
            errs.append(f"{readme}: бейдж не {n}")
        counts = [int(x) for x in re.findall(r"\((\d+)\):", text)
                  if 0 < int(x) <= n]
        # суммы групп tools-секции должны давать n
        if sum(counts) != n:
            errs.append(f"{readme}: сумма групп {sum(counts)} != {n} {counts}")
    if errs:
        print("РАСХОЖДЕНИЕ:")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"OK: {len(srv)} tools совпадают")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
