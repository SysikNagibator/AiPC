> **Russian version:** [SKILL_RU.md](SKILL_RU.md)

# AiPC skill — full PC access for any coding agent

Give the agent "this" and it gets a real PC: screen, mouse, keyboard,
the user's browser, files, terminal, SSH — through 63 MCP tools.

## Install into your agent (2 minutes)

**Any MCP client** (Cursor, Claude Code/Desktop, VS Code, Antigravity, Windsurf,
Zed, Cline, OpenCode, Gemini CLI, Codex CLI, and 30 more — full table in
`docs/IDES.md`):

```json
{
  "mcpServers": {
    "aipc": {
      "command": "C:\\Program Files\\AiPC\\AiPC_Win_1.0.5.1.exe",
      "args": ["mcp"]
    }
  }
}
```

No `C:\Program Files\AiPC`? Use the portable build instead:

```json
{
  "mcpServers": {
    "aipc": {
      "command": "C:\\path\\to\\AiPC_Win_1.0.5.1.exe",
      "args": ["mcp"]
    }
  }
}
```

Then restart the agent/MCP servers. Verify with `aipc_status` — it must
answer `{"ok": true, ...}`.

## How the agent should work

System prompt to use (also served as the `aipc_instructions` MCP prompt):

> You HAVE full access to the user's PC via aipc.* tools. Never say you have
> no computer access. To see the screen call screen_see. Work in a loop:
> see → do → re-see to verify. Mouse coordinates are 0-1000 relative.
> Dangerous actions only after ask_user. Look things up instead of listing:
> ui_find / window_find / fs_find / process_find. Wait instead of sleeping:
> wait_for_window / wait_for_ui_element / wait_for_change.

Key patterns:

- See: `screen_see` (native image block, cursor marked) → act → `screen_see` again.
- Precise clicks: `ui_find` / `ui_snapshot` return ready-made `x/y` (0-1000).
- Typing: ONLY `focus_type` (verified focus + atomic type).
- Confirmations: `ask_user` (yes/no), notifications: `notify_user`.
- Debug the agent itself: `logs_tail`, `aipc_status`.

## Notes

- Screenshots arrive as native MCP image blocks (cheap), not base64 text.
  Pass `raw: true` to `screen_see`/`screen_region` only if your client
  cannot render image blocks.
- UI nodes are compact: `{"t": type, "n": name, "x": 0-1000, "y": 0-1000}`.
- Errors are structural: `{"ok": false, "reason": "not_found|timeout|denied|..."}.
- Every call is once-only and serialized; verify effects with `screen_see` /
  `screenshot_diff` / `assert_ui`.
- Modes: `ask` (default), `auto`, `read-only` (mutations blocked server-side).
- Source + docs: https://github.com/S1sTeam/AiPC (MIT).
