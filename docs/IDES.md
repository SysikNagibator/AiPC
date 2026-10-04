> **Russian version:** [IDES_RU.md](IDES_RU.md)

# AiPC × IDE — support matrix

`aipc` registers itself in IDE configs (menu item “Setup” → “Connect IDE”, command `aipc setup`, report — `aipc doctor`). We don’t touch other servers, and create a `.bak` before editing. Ready-made presets are in [`mcp_presets/`](../mcp_presets/).

Legend: **Auto** — we write it ourselves on launch; **Preset** — file + 1 manual action; **Bridge** — localhost unavailable, work via a workaround (see below).

## A. Fully automatic

| IDE | Where we write | After |
|-----|----------------|-------|
| Google Antigravity | `~/.gemini/config/mcp_config.json` | Refresh MCP |
| Cursor | `~/.cursor/mcp.json` (+ legacy `%APPDATA%\Cursor\User\mcp.json`) | Restart |
| VS Code — Cline | `%APPDATA%\Code\User\mcp_settings.json` + `globalStorage/.../cline_mcp_settings.json` | Restart |
| VS Code — Roo Code | `globalStorage/rooveterinaryinc.roo-cline/.../mcp_settings.json` | Restart |
| VS Code — GitHub Copilot | `settings.json` → section `mcp.servers` | Restart |
| Claude Desktop App | `%APPDATA%\Claude\claude_desktop_config.json` | Restart |
| Claude Code | `~/.claude.json` (section `mcpServers`) | `/mcp` in CLI |
| Gemini CLI | `~/.gemini/settings.json` | Restart |
| OpenAI Codex CLI | `~/.codex/config.toml` (append `[mcp_servers.aipc]`) | Restart |
| OpenCode | `~/.config/opencode/opencode.json` (section `mcp`, `type: local`) | Restart |
| Zed | `~/.config/zed/settings.json` (`context_servers`) | Restart |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | Refresh MCP |
| Continue | `~/.continue/mcpServers/aipc.yaml` | Restart |
| Kiro | `~/.kiro/settings/mcp.json` | Restart |
| Trae | `%APPDATA%\Trae\User\mcp.json` | Restart |
| Amazon Q (CLI) | `~/.aws/amazonq/mcp.json` | `q mcp list` |

## B. Preset + one action

| IDE | What to do |
|-----|------------|
| JetBrains (IntelliJ IDEA, PyCharm, WebStorm, GoLand, PhpStorm…) | Settings → Tools → MCP Servers → Import from `mcp_presets/jetbrains.json` |
| Aider | Place `mcp_presets/aider.json` nearby / specify `--mcp-servers` (depends on version, check `aider --help`) |
| Goose | Add the block from `mcp_presets/goose.yaml` into `~/.config/goose/config.yaml` → `extensions` |
| Neovim | Plugin mcphub.nvim + contents of `mcp_presets/nvim.json` into its `servers.json` |
| Emacs | Package mcp.el + command `C:\Program Files\AiPC\AiPC_Win_1.0.5.1.exe` with args `("mcp")` |
| OpenSumi | Import `mcp_presets/jetbrains.json` (mcpServers format) into AI settings |
| Theia IDE / Theia AI | Import the mcpServers preset into AI settings |
| LibreChat | `mcpServers` block in `librechat.yaml` (example — `mcp_presets/cursor.json`) |
| fast-agent | Section `mcp.servers` in `fastagent.config.yaml` (command + args as in the preset) |
| Genkit | Connect in code via Genkit MCP-client (command from the preset) |
| GenAIScript | MCP server in the script config (command from the preset) |
| 5ire | Settings → MCP → Add server (command from the preset) |
| Sourcegraph Cody | Via native MCP in VS Code (see VS Code — Copilot above) |
| Augment Code | Via native MCP in VS Code / JetBrains (see above) |
| Amp | Import the mcpServers preset into settings |

## C. Bridge (cloud/web without localhost access)

Claude.ai, Manus AI, Devin AI, Bolt.new, v0.dev, Lovable, Replit, Microsoft Copilot Studio, Tabnine — these environments cannot reach `127.0.0.1` on your PC. Working workarounds:

1. **Do it in an MCP-IDE, show it there.** Main workaround: the task is performed in Cursor/Antigravity with full access, and the result (files, links) is transferred to the web environment.
2. **Paste tools manually.** The list of all 59 tools with descriptions is in `tools.json` at the repository root; the output of any call can be copied from `~/.aipc/audit.log`.
3. **SSH tunnel (advanced).** If the cloud IDE supports SSH — stdio-MCP over ssh is not part of v1 (transport is local stdio only).

## Verification

`aipc doctor` shows for each IDE: config found / entry exists / exe present. We add new IDEs from list A ourselves on every menu launch.
