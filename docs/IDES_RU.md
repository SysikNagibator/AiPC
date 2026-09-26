> **English version:** [docs/IDES.md](IDES.md)

# AiPC × IDE — матрица поддержки

`aipc` сам прописывает себя в конфиги IDE (пункт меню «Настроить» → «Подключить IDE»,
команда `aipc setup`, отчёт — `aipc doctor`). Чужие серверы не трогаем, перед правкой — `.bak`.
Готовые пресеты лежат в [`mcp_presets/`](../mcp_presets/).

Легенда: **Авто** — пишем сами при запуске; **Пресет** — файл + 1 действие вручную; **Мост** — localhost
недоступен, работа через связку (см. низ).

## A. Полный автомат

| IDE | Куда пишем | После |
|-----|------------|-------|
| Google Antigravity | `~/.gemini/config/mcp_config.json` | Refresh MCP |
| Cursor | `~/.cursor/mcp.json` (+ legacy `%APPDATA%\Cursor\User\mcp.json`) | Перезапуск |
| VS Code — Cline | `%APPDATA%\Code\User\mcp_settings.json` + `globalStorage/.../cline_mcp_settings.json` | Перезапуск |
| VS Code — Roo Code | `globalStorage/rooveterinaryinc.roo-cline/.../mcp_settings.json` | Перезапуск |
| VS Code — GitHub Copilot | `settings.json` → секция `mcp.servers` | Перезапуск |
| Claude Desktop App | `%APPDATA%\Claude\claude_desktop_config.json` | Перезапуск |
| Claude Code | `~/.claude.json` (секция `mcpServers`) | `/mcp` в CLI |
| Gemini CLI | `~/.gemini/settings.json` | Перезапуск |
| OpenAI Codex CLI | `~/.codex/config.toml` (дописываем `[mcp_servers.aipc]`) | Перезапуск |
| OpenCode | `~/.config/opencode/opencode.json` (секция `mcp`, `type: local`) | Перезапуск |
| Zed | `~/.config/zed/settings.json` (`context_servers`) | Перезапуск |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | Refresh MCP |
| Continue | `~/.continue/mcpServers/aipc.yaml` | Перезапуск |
| Kiro | `~/.kiro/settings/mcp.json` | Перезапуск |
| Trae | `%APPDATA%\Trae\User\mcp.json` | Перезапуск |
| Amazon Q (CLI) | `~/.aws/amazonq/mcp.json` | `q mcp list` |

## B. Пресет + одно действие

| IDE | Что сделать |
|-----|-------------|
| JetBrains (IntelliJ IDEA, PyCharm, WebStorm, GoLand, PhpStorm…) | Settings → Tools → MCP Servers → Import из `mcp_presets/jetbrains.json` |
| Aider | Положить `mcp_presets/aider.json` рядом / указать `--mcp-servers` (зависит от версии, сверься с `aider --help`) |
| Goose | Добавить блок из `mcp_presets/goose.yaml` в `~/.config/goose/config.yaml` → `extensions` |
| Neovim | Плагин mcphub.nvim + содержимое `mcp_presets/nvim.json` в его `servers.json` |
| Emacs | Пакет mcp.el + команда `C:\Program Files\AiPC\aipc.exe` с args `("mcp")` |
| OpenSumi | Импорт `mcp_presets/jetbrains.json` (формат mcpServers) в AI-настройки |
| Theia IDE / Theia AI | Импорт mcpServers-пресета в AI-настройки |
| LibreChat | Блок `mcpServers` в `librechat.yaml` (пример — `mcp_presets/cursor.json`) |
| fast-agent | Секция `mcp.servers` в `fastagent.config.yaml` (команда + args как в пресете) |
| Genkit | Подключение в коде через Genkit MCP-client (команда из пресета) |
| GenAIScript | MCP-сервер в конфиге скрипта (команда из пресета) |
| 5ire | Settings → MCP → Add server (команда из пресета) |
| Sourcegraph Cody | Через нативный MCP VS Code (см. VS Code — Copilot выше) |
| Augment Code | Через нативный MCP VS Code / JetBrains (см. выше) |
| Amp | Импорт mcpServers-пресета в настройки |

## C. Мост (облако/веб без доступа к localhost)

Claude.ai, Manus AI, Devin AI, Bolt.new, v0.dev, Lovable, Replit, Microsoft Copilot Studio,
Tabnine — эти среды не могут достучаться до `127.0.0.1` на твоём ПК. Рабочие связки:

1. **Делай в MCP-IDE, показывай там.** Основная связка: задача выполняется в Cursor/Antigravity
   с полным доступом, результат (файлы, ссылки) переносится в веб-среду.
2. **Вставь tools вручную.** Список всех 59 tools с описаниями — `tools.json` в корне репозитория;
   вывод любого вызова можно скопировать из `~/.aipc/audit.log`.
3. **SSH-туннель (продвинутые).** Если облачная IDE умеет SSH — stdio-MCP через ssh не входит
   в v1 (транспорт только локальный stdio).

## Проверка

`aipc doctor` показывает по каждой IDE: конфиг найден / запись есть / exe на месте.
Новую IDE из списка A мы добавляем сами при каждом запуске меню.
