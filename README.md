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
  <img src="https://img.shields.io/badge/tools-63-brightgreen" alt="tools">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="license">
</p>

<p align="center">
  <b>Русская версия — основная: <a href="README.md">README.md</a></b> · Skills: <a href="SKILL.md">SKILL.md</a> · IDE matrix: <a href="docs/IDES.md">docs/IDES.md</a>
</p>

---

## Contents

- [What it is](#what-it-is)
- [Why AiPC](#why-aipc)
- [Quick start](#quick-start)
- [The `aipc` menu](#the-aipc-menu)
- [63 tools](#63-tools-for-the-model)
- [Token efficiency](#token-efficiency)
- [MCP connection](#mcp-connection)
- [Self-update](#self-update)
- [Safety](#safety)
- [Troubleshooting](#troubleshooting)
- [Project structure](#project-structure)
- [Build from source](#build-from-source)
- [License](#license)

---

## What it is

**AiPC** is a local service + console utility that gives any AI agent full access
to your computer over the open **MCP** (Model Context Protocol) standard.

```
[ Agent in any IDE ] --MCP/stdio--> [ AiPC-Core: one local service ]
                                            |
        +------------------+----------------+------------------+
        |                  |                |                  |
      Vision            Control          Browser           System/Net
   screenshots,      mouse+keyboard,  your Chrome via    files, terminal,
   UI tree,           apps,            CDP + history,     processes, SSH,
   windows            clipboard        JS eval           search, sysinfo
```

The agent stops being "text in a chat" and starts working like a human at the PC:
it looks at the monitor, clicks, types, opens apps, googles in **your** browser,
runs commands, uses SSH — and verifies every step with a new screenshot.

If a model says "I have no computer access", the built-in system prompt
(`aipc/server.py:SYSTEM_PROMPT`, also served as the `aipc_instructions` MCP prompt)
forbids that answer and requires acting through AiPC tools.

## Why AiPC

| Usual agent limits | With AiPC |
|--------------------|-----------|
| Blind: no screen | `screen_see` — screenshot as a native image block, cursor marked |
| Clicks by guessing | `ui_snapshot` / `ui_find` — ready-made x/y coordinates (0–1000) |
| Typing into the void | `focus_type` — verified focus + atomic typing; refuses to type blind |
| Sleeps and hopes | `wait_for_window` / `wait_for_ui_element` / `wait_for_change` |
| "Did it work?" unknown | `screenshot_diff`, `assert_ui`, `logs_tail`, `audit.log` |
| No machine access | Files, terminal, processes, SSH/SFTP, browser, clipboard |
| Token burn on screenshots | Native image blocks (~65 chars + image vs 55K chars of base64) |

---

## Quick start

| Step | What to do |
|------|------------|
| 1 | Download **`aipc.exe`** from [Releases](https://github.com/S1sTeam/AiPC/releases) and double-click it |
| 2 | On first run it **sets everything up itself**: asks for admin once (UAC) → copies itself to `C:\Program Files\AiPC\` → adds the `aipc` command to PATH → registers itself in the MCP configs of all detected IDEs (`.bak` backup first) → opens the menu |
| 3 | In your IDE refresh MCP servers (Refresh / restart) and give the agent a plain-language task |

Example tasks:

```
look at my screen, what is this error?
open YouTube and find a review of ...
connect via SSH to 192.168.1.10 and fetch yesterday's log
```

Works with any tool-capable 2026 model: `claude-opus-5-5`, `gpt-6-astra`,
`gpt-6-sol` / `luna`, `gemini-3.8-flash`, `claude-fable-5-1`.

---

## The `aipc` menu

Open a regular `cmd` and type `aipc`. Green theme, no flicker (single-threaded
`rich.Live` in an alternate buffer), gradient title, pulsing selection marker,
danger items in red, status bar (`mode • version • tools`), quick splash on entry.
Controls: **W** up, **S** down, arrows **↑/↓**, **Enter** select, digits 1–9,
**Q** back/exit. Russian layout works by key position. No emoji, ASCII fallback included.

| Item | What it does |
|------|--------------|
| Launch AiPC-Core | Handshake-check as an IDE would, then background Core (stdio detached) |
| Stop | Stops Core (never touches foreign PIDs) |
| Status / Self-test | Screen, mouse, terminal, config, MCP, browser |
| Diagnostics (doctor) | Install, PATH, every IDE config, Chrome, disk — flags stale installs |
| Check updates | Looks at GitHub releases; asks before downloading + installing |
| Setup | Mode `ask/auto/read-only`, IDE, browser (CDP flag), SSH hosts |
| Service | Reinstall + PATH, reconfigure MCP, kill Core, where-am-I info |
| Logs | Last 20 lines of `audit.log` |
| Exit | — |

No menu at hand? Same actions as commands:
`aipc update`, `aipc doctor`, `aipc kill`, `aipc keys` (keyboard diagnostics),
`aipc status`, `aipc selftest`, `aipc setup`, `aipc install`, `aipc mcp`.

---

## 63 tools for the model

**Vision (15):** `screen_see`, `screen_region`, `ui_snapshot` (active window by default:
0.69s / 17 nodes vs 1.7s / 200 desktop), `ui_find`, `assert_ui`, `windows_list`,
`window_focus` (verified), `window_manage`, `window_find`, `get_active_window`,
`wait_for_window`, `wait_for_ui_element`, `wait_for_change`, `screenshot_diff`, `screen_info`.

**Mouse & keyboard (17):** `mouse_move/click/drag/double_click/right_click/middle_click`
(drag with ctrl/shift/alt), `scroll`, `type_text` (auto-chunked, Cyrillic-safe),
`press_key`, `key_down/up`, `clipboard_set/get` (+images), `sleep`, `open_app`,
`focus_type` (verified focus + atomic type — the only correct way to type).

**Browser (6):** `browser_tabs`, `browser_goto`, `browser_eval` (JS via CDP —
more reliable than coordinate clicks), `browser_active_tab`, `browser_close_tab`,
`browser_history_search` (read-only copy of the History DB).

**Files & system (13):** `fs_list/read/write/find/stat/mkdir/delete/move`
(atomic writes + `.bak`, binary guard, pagination, deny-lists),
`run_cmd` (split stdout/stderr, Russian OEM decoding, deny-list),
`process_list/find`, `wait_for_process`, `download_file` (streamed, no size cap).

**Network & machine (5):** `web_search_pc`, `ssh_exec`, `ssh_sftp_get/put`
(200 MB+ friendly streaming), `sys_info` (battery/memory/CPU/disks),
`net_check`, `env_get` (refuses secret-like names).

**Human & debug (4):** `notify_user` (popup, non-blocking), `ask_user` (Yes/No,
blocks for a human decision), `aipc_status`, `logs_tail`.

Agent loop: **see (`screen_see`) → do → re-see to verify**.
Errors are structural: `{"ok": false, "reason": "not_found|timeout|denied|..."}`.
Every call runs exactly once, serialized; every call lands in `~/.aipc/audit.log`
(2 MB rotation).

## Token efficiency

- Screenshots travel as **native MCP image blocks**: ~65 chars of JSON + image
  instead of ~55K chars of base64 text (~10x cheaper per screenshot).
  `raw=true` returns legacy base64 if a client can't render images.
- UI nodes are compact: `{"t","n","x","y"}` instead of long keys.
- `ui_snapshot` defaults to the active window; role/name filters cut tokens further.
- Prefer search over listing: `ui_find` / `window_find` / `fs_find` / `process_find`.
- All tool descriptions fit in one short line.

---

## MCP connection

AiPC registers itself on every menu launch (19 configs across 14 IDE families).
Manual reference format:

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

Full 40-IDE matrix (auto / preset / bridge): [docs/IDES.md](docs/IDES.md).
Ready-made files: [mcp_presets/](mcp_presets/). Skill-style install: [SKILL.md](SKILL.md).

Cloud IDEs without localhost access (Claude.ai, Manus, Devin, Bolt, v0, Lovable,
Replit…) can't reach `127.0.0.1` — see the "Bridge" section in `docs/IDES.md`.

## Self-update

Menu → "Check updates" (or `aipc update`): compares with the latest GitHub release,
shows the changelog, and only with your explicit **Yes** downloads and reinstalls
itself (UAC). Version is always visible in the menu title; `aipc doctor` flags
a stale install in Program Files.

---

## Safety

- Modes: `ask` (default — the model must confirm via `ask_user`), `auto`,
  `read-only` (all mutating tools blocked **server-side**, not just by prompt).
- Admin rights needed **once** — copying into Program Files + writing PATH.
- Deny-lists for commands (mimikatz, ransomware patterns, encoded PowerShell,
  `^`-obfuscation normalized) and paths (browser secrets, private keys,
  hives, `System32`) live in `~/.aipc/config.yaml` and **auto-upgrade**
  (`safety.version`) without wiping your additions.
- Typing goes only into a **verified** foreground window (`focus_type`).
- Secrets guard: `env_get` refuses `*KEY/*TOKEN/*SECRET/*PASSWORD*` names.
- Emergency stop: menu → Stop, or `aipc kill` (verifies the PID is ours first).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Model says "no PC access" | Reconnect MCP (Refresh / restart IDE), remind: "you have aipc.* tools, start with screen_see" |
| Menu doesn't respond to keys | Run `aipc keys`, press W/S/arrows/Enter/Esc — paste the 5 lines to us |
| `aipc` command unknown | Open a **new** cmd (PATH applies to new shells); reinstall via `dist\aipc.exe` |
| Right wall of the menu drifts | Update: frames render only via fixed-width `rich.Panel` since 1.0.4.4 |
| Chrome tabs invisible | Menu → Setup → Browser (adds `--remote-debugging-port=9222`), restart Chrome |
| Old version in Program Files | `aipc doctor` tells you; run fresh `dist\aipc.exe` → UAC → updated |
| GitHub page/API 404s | Our repo was once throttled by GitHub abuse heuristics; mirror + support appeal process in issues |

---

## Project structure

```
AiPC/
  aipc/            # server.py (MCP) · vision/control/os_ops/browser/net/sysinfo
                   # notify · installer (self-install + 19 IDE configs)
                   # maintenance (update/doctor/kill) · menu · policy/audit
  mcp_presets/     # ready-made MCP configs (16 files)
  assets/          # logo + exe icon (visible on light and dark themes)
  tools/           # build_exe.bat · build_icon.py · sign.bat · version_info.txt
  tests/           # pytest: policy, installer merge, server (19 tests)
  docs/            # IDES.md (40 IDEs) · SIGNING.md (SmartScreen)
  SKILL.md         # one-file skill install · CHANGELOG.md · LICENSE (MIT)
```

---

## Build from source

```bat
python -m pip install -r requirements.txt
python -m pytest tests -q
python -m aipc selftest
tools\build_exe.bat
```

Output: `dist\aipc.exe` (~36 MB, icon + publisher version-info) and `dist\AiPC-Setup.exe`.
Signing away the blue SmartScreen: see [docs/SIGNING.md](docs/SIGNING.md) (needs
a code-signing certificate: Certum Open Source ~€25/yr is the cheapest start).

---

## License

MIT. Author — Sysik. See [LICENSE](LICENSE).
