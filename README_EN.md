<p align="center">
  <img src="https://files.catbox.moe/e9o2sz.png" alt="AiPC by Sysik">
</p>

<h1 align="center">AiPC by Sysik</h1>

<p align="center">
  <b>Give the agent "this" — and it gets a real PC.</b><br>
  Screen, mouse, keyboard, your browser, files, terminal, SSH — via the model's native tools.
</p>

<p align="center">
  <a href="https://github.com/S1sTeam/AiPC/releases"><img src="https://img.shields.io/github/v/release/S1sTeam/AiPC?label=release" alt="release"></a>
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-blue" alt="platform">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="license">
</p>

> Russian version: [README.md](README.md). Русская версия — основная.

---

## What it is

**AiPC** is a local service + console utility that gives any AI agent full access to your computer
over the open **MCP** (Model Context Protocol) standard. The agent stops being "text in a chat"
and starts working like a human at the PC: looking at the monitor, clicking, typing, opening apps,
googling in your browser, running commands, using SSH.

Works with **any MCP-capable IDE** (see [docs/IDES.md](docs/IDES.md) — 40 covered) and any
tool-capable 2026 model: `claude-opus-5-5`, `gpt-6-astra`, `gpt-6-sol`, `gemini-3.8-flash`, `claude-fable-5-1`.

If a model says "I have no computer access" — the built-in system prompt
(`aipc/server.py:SYSTEM_PROMPT`) forbids that answer and requires acting via AiPC tools.

---

## Quick start (3 steps, no knowledge needed)

| Step | What to do |
|------|------------|
| 1 | Download **`aipc.exe`** from [Releases](https://github.com/S1sTeam/AiPC/releases) and double-click it |
| 2 | On first run it **sets everything up itself**: asks for admin once (UAC) → copies itself to `C:\Program Files\AiPC\` → adds the `aipc` command to PATH → registers itself in the MCP configs of all detected IDEs (with `.bak` backup) → opens the menu |
| 3 | In your IDE refresh MCP servers (Refresh / restart) and give the agent a task in plain language |

Example tasks:

```
look at my screen, what is this error?
open YouTube and find a review of ...
connect via SSH to 192.168.1.10 and fetch the log
```

---

## The `aipc` menu

Open a regular `cmd` and type `aipc`. Controls: **W** up, **S** down, arrows **↑/↓**,
**Enter** select, digits for quick select, **Q** back/exit.

Items: Launch AiPC-Core / Stop / Status-Selftest / Diagnostics (doctor) / Check updates /
Setup (mode `ask/auto/read-only`, IDE, browser, SSH) / Service (install, MCP, kill Core) /
Logs / Exit. Plus CLI commands: `aipc update`, `aipc doctor`, `aipc kill`, `aipc keys`.

Frames render only via `rich.Panel` with fixed width — the right border never drifts.
No emoji, ASCII fallback included.

---

## 63 tools for the model

**Vision:** `screen_see` (cursor marked), `screen_region`, `ui_snapshot` (active window by default),
`ui_find`, `assert_ui`, `windows_list`, `window_focus` (verified), `window_manage`,
`window_find`, `get_active_window`, `wait_for_window`, `wait_for_ui_element`,
`wait_for_change`, `screenshot_diff`, `screen_info`.

**Mouse & keyboard:** `mouse_move/click/drag/double_click/right_click/middle_click`,
`scroll`, `type_text` (chunked, Cyrillic-safe), `press_key`, `key_down/up`,
`clipboard_set/get` (+images), `sleep`, `open_app`, `focus_type` (verified focus + type).

**Browser:** `browser_tabs`, `browser_goto`, `browser_eval` (JS via CDP),
`browser_active_tab`, `browser_close_tab`, `browser_history_search`.

**Files & system:** `fs_list/read/write/find/stat/mkdir/delete/move`, `run_cmd`,
`process_list/find`, `wait_for_process`, `download_file`, `web_search_pc`,
`ssh_exec`, `ssh_sftp_get/put`, `sys_info`, `net_check`, `env_get` (no secrets).

**Human & debug:** `notify_user`, `ask_user`, `aipc_status`, `logs_tail`
+ the `aipc_instructions` MCP prompt.

Agent loop: **see (`screen_see`) → do → re-see to verify**. Every call lands in `~/.aipc/audit.log`.

---

## MCP connection

AiPC registers itself automatically; manual format reference:

```json
{
  "mcpServers": {
    "aipc": {
      "command": "C:\\Program Files\\AiPC\\aipc.exe",
      "args": ["mcp"]
    }
  }
}
```

See [docs/IDES.md](docs/IDES.md) for all 40 IDEs and [mcp_presets/](mcp_presets/) for ready-made files.

---

## Safety

Modes: `ask` (default), `auto`, `read-only` (mutating tools blocked server-side).
Admin rights needed **once** — for copying into Program Files and writing PATH.
Dangerous commands and paths are cut by `~/.aipc/config.yaml` deny-lists (auto-upgraded).
Every tool call is logged. Emergency stop: menu → Stop, or `aipc kill`.

---

## Build from source

```bat
python -m pip install -r requirements.txt
python -m pytest tests -q
python -m aipc selftest
python -m aipc mcp
tools\build_exe.bat
```

Output: `dist\aipc.exe` and `dist\AiPC-Setup.exe` with the `assets\AiPC.ico` icon.
Signing against the blue SmartScreen: see [docs/SIGNING.md](docs/SIGNING.md).

---

## License

MIT. Author — Sysik. See [LICENSE](LICENSE).
