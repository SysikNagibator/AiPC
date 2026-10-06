# AiPC Architecture

Russian version: [ARCHITECTURE_RU.md](ARCHITECTURE_RU.md).

## Processes

```
IDE (MCP client, stdio JSON-RPC)
  │  tools/list, tools/call
  ▼
aipc.exe mcp  →  aipc/server.py create_server()
  │  1. _check_limits (rate, loop_guard)
  │  2. panic gate (kill switch file)
  │  3. read-only gate
  │  4. risk class + ask/auto/taint confirmation (native dialog)
  │  5. impl call: vision/control/os_ops/browser/net/...
  │  6. untrusted tagging, taint note, JSON audit
  ▼
Windows OS (WinAPI, UIA, WASAPI, CDP :9222, SSH)
```

One OS process per IDE connection. No network listener: stdio only,
`127.0.0.1:18789` in config is legacy/unused by default.

## Call path of one tool (example: `run_cmd`)

1. Model sends `tools/call run_cmd {cmd}` over the MCP stdio pipe.
2. `_wrap("run_cmd", ...)` runs the gates in order (see diagram).
3. `os_ops.run_cmd` → `policy.check_cmd_allowed` (normalize → deny substrings
   → env-secret refs → in-command paths) → `subprocess.run` → truncated
   `{ok, stdout, stderr}` (+ `untrusted`? no — command output is the model's
   own action result; remote outputs like `ssh_exec` are tagged).
4. `audit.log_event` writes one JSON line (masked args, mode, decision).

## Modules

| Module | Owns |
|---|---|
| `server.py` | MCP surface, gates, prompts, profiles, taint |
| `policy.py` | modes, risk classes, deny/allow, timed allows, secrets predicate |
| `audit.py` | JSON-lines log, secret masking, tail/filters |
| `notify.py` | human dialogs (ask_user, confirm_action with timeout) |
| `panic.py` | kill-switch file + hotkey watcher |
| `vision.py` / `control.py` | screen/UIA, mouse/keyboard |
| `os_ops.py` / `net.py` / `sysinfo.py` | files/proc, SSH/net/download, host info |
| `browser.py` | Chrome CDP (tabs, JS eval) |
| `audio.py` / `video.py` | WASAPI capture, ffmpeg frames |
| `installer.py` / `maintenance.py` | IDE configs, self-install/update, doctor |
| `menu.py` / `__main__.py` / `setup_wizard.py` / `actions.py` | CLI, animated menu |
| `platform/` | OS seams (win32 full, posix partial) |
| `config.py` / `i18n.py` / `errors.py` | config+migrations, EN/RU strings, error format |

## State on disk (`~/.aipc/`)

`config.yaml` (modes, deny-lists, safety), `audit.log` (+`.bak` rotation),
`allow.json` (timed confirmations), `panic` (kill switch, if set),
`aipc.pid` (Core process), `menu.log` (menu diagnostics).
