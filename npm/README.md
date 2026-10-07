# aipc-sysik (npm)

AiPC by SYSIK — локальный MCP-сервер + терминальное меню: даёт Claude и другим
ИИ-ассистентам глаза и руки на твоём ПК. Этот npm-пакет — тонкая обёртка:
при установке скачивает готовый бинарь под твою ОС со страницы
[Releases](https://github.com/SysikNagibator/AiPC/releases) и кладёт команду `aipc`.

```sh
npm i -g aipc-sysik
aipc            # меню (первый запуск всё настроит сам)
aipc mcp        # MCP-команда для IDE
```

Полная документация (EN/RU), риски и матрица платформ — в
[основном репозитории](https://github.com/SysikNagibator/AiPC#readme).

## Как это работает

`postinstall` (`install.js`) определяет `process.platform`/`process.arch`,
качает нужный файл релиза `v1.1` (`AiPC_Win_*.exe`, `AiPC_macOS_*`,
`AiPC_Linux_*`) в `bin/` и делает его исполняемым. Шим `bin/aipc.js`
пробрасывает аргументы в бинарь один в один.

Поддерживаются: Windows x64, macOS ARM64, Linux x64. Остальным —
`pip install git+https://github.com/SysikNagibator/AiPC.git` или бинарь
из Releases вручную. Офлайн-установка: `AIPC_SYSIK_SKIP_DOWNLOAD=1`.

## Версии

Версия npm-пакета следует за релизами AiPC (`1.1.0` = релиз `v1.1`).
Карта «ОС → файл» лежит в `platforms.js` и обновляется с каждым релизом.

License: MIT. Author — SYSIK.
