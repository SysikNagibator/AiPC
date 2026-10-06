# Архитектура AiPC

English version: [ARCHITECTURE.md](ARCHITECTURE.md).

## Процессы

```
IDE (MCP-клиент, stdio JSON-RPC)
  │  tools/list, tools/call
  ▼
aipc.exe mcp  →  aipc/server.py create_server()
  │  1. _check_limits (скорость, loop_guard)
  │  2. panic-гейт (файл kill switch)
  │  3. read-only гейт
  │  4. класс риска + подтверждение ask/auto/taint (нативное окно)
  │  5. вызов реализации: vision/control/os_ops/browser/net/...
  │  6. untrusted-метка, taint-запись, JSON-аудит
  ▼
Windows OS (WinAPI, UIA, WASAPI, CDP :9222, SSH)
```

Один процесс ОС на подключение IDE. Слушающих сокетов нет: только stdio,
`127.0.0.1:18789` в конфиге — наследие, по умолчанию не используется.

## Путь одного вызова (пример: `run_cmd`)

1. Модель шлёт `tools/call run_cmd {cmd}` по MCP stdio-пайпу.
2. `_wrap("run_cmd", ...)` идёт по гейтам по порядку (см. схему).
3. `os_ops.run_cmd` → `policy.check_cmd_allowed` (нормализация → deny-подстроки
   → секреты окружения → пути внутри команды) → `subprocess.run` → обрезанные
   `{ok, stdout, stderr}`.
4. `audit.log_event` пишет одну JSON-строку (маскированные аргументы, режим, решение).

## Модули

| Модуль | За что отвечает |
|---|---|
| `server.py` | MCP-поверхность, гейты, промпты, профили, taint |
| `policy.py` | режимы, классы риска, deny/allow, временные разрешения, предикат секретов |
| `audit.py` | JSON-lines лог, маскирование секретов, хвост/фильтры |
| `notify.py` | диалоги человеку (ask_user, confirm_action с таймаутом) |
| `panic.py` | файл kill switch + watcher хоткея |
| `vision.py` / `control.py` | экран/UIA, мышь/клавиатура |
| `os_ops.py` / `net.py` / `sysinfo.py` | файлы/процессы, SSH/сеть/скачивание, инфо о хосте |
| `browser.py` | Chrome CDP (вкладки, JS eval) |
| `audio.py` / `video.py` | захват WASAPI, кадры ffmpeg |
| `installer.py` / `maintenance.py` | конфиги IDE, self-install/update, doctor |
| `menu.py` / `__main__.py` / `setup_wizard.py` / `actions.py` | CLI, анимированное меню |
| `platform/` | швы ОС (win32 полный, posix частичный) |
| `config.py` / `i18n.py` / `errors.py` | конфиг+миграции, строки EN/RU, формат ошибок |

## Состояние на диске (`~/.aipc/`)

`config.yaml` (режимы, deny-листы, safety), `audit.log` (+ротация `.bak`),
`allow.json` (временные подтверждения), `panic` (kill switch, если стоит),
`aipc.pid` (процесс Core), `menu.log` (диагностика меню).
