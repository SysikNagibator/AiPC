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
качает нужный файл релиза `v1.1.1` (`AiPC_Win_*.exe`, `AiPC_macOS_*`,
`AiPC_Linux_*`) в `bin/` и делает его исполняемым. Шим `bin/aipc.js`
пробрасывает аргументы в бинарь один в один.

> Новые версии npm (11+) могут блокировать postinstall-скрипты — не страшно:
> шим сам докачает бинарь при первом запуске `aipc`.

Поддерживаются: Windows x64, macOS ARM64, Linux x64. Остальным —
`pip install git+https://github.com/SysikNagibator/AiPC.git` или бинарь
из Releases вручную. Офлайн-установка: `AIPC_SYSIK_SKIP_DOWNLOAD=1`.

## Версии

Версия npm-пакета следует за релизами AiPC (`1.1.2` = релиз `v1.1.1`).
Карта «ОС → файл» лежит в `platforms.js` и обновляется с каждым релизом.

License: MIT. Author — SYSIK.

## Зеркало в GitHub Packages

Основной реестр — npmjs (`npm i -g aipc-sysik`, без логина). Дополнительно
каждый релиз-тег публикуется в GitHub Packages как
`@sysiknagibator/aipc-sysik` (workflow `gh-packages.yml`, scoped-имя требует
сам GitHub). Установка оттуда — только с авторизацией:

```sh
# ~/.npmrc:
@sysiknagibator:registry=https://npm.pkg.github.com/
//npm.pkg.github.com/:_authToken=ТУТ_PAT_С_READ_PACKAGES
npm i -g @sysiknagibator/aipc-sysik
```
