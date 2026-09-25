<p align="center">
  <img src="https://files.catbox.moe/e9o2sz.png" alt="AiPC от Sysik">
</p>

<h1 align="center">AiPC от Sysik</h1>

<p align="center">
  <b>Даёшь агенту «это» — и у него появляется настоящий ПК.</b><br>
  Экран, мышь, клавиатура, твой браузер, файлы, терминал, SSH — через привычные tools модели.
</p>

<p align="center">
  <a href="https://github.com/S1sTeam/AiPC/releases"><img src="https://img.shields.io/github/v/release/S1sTeam/AiPC?label=release" alt="release"></a>
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-blue" alt="platform">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="license">
</p>

---

## Что это

**AiPC** — локальный сервис + консольная утилита, которая даёт любому ИИ-агенту полный доступ к твоему компьютеру. Агент перестаёт быть «текстом в чате» и начинает работать как человек за ПК: смотрит на монитор, кликает мышью, печатает, открывает приложения, гуглит в твоём браузере, выполняет команды и ходит по SSH.

Работает с **любой IDE** через открытый протокол **MCP** (Model Context Protocol) и с **любой tool-способной моделью** 2026 года — от `claude-opus-5-5` и `gpt-6-astra` до `gemini-3.8-flash`.

Если модель говорит «у меня нет доступа к компьютеру» — встроенный системный промпт (`aipc/server.py:SYSTEM_PROMPT`) запрещает ей так отвечать и требует действовать через tools AiPC.

---

## Быстрый старт (3 шага, ничего знать не надо)

| Шаг | Что сделать |
|-----|-------------|
| 1 | Скачай **`aipc.exe`** из раздела [Releases](https://github.com/S1sTeam/AiPC/releases) или по прямой ссылке ([зеркало v1.0.4.3](https://files.catbox.moe/5yiq9w.zip), распаковать) и запусти двойным кликом |
| 2 | При первом запуске он **сам всё настроит**: один раз попросит права админа (UAC) → скопирует себя в `C:\Program Files\AiPC\` → добавит команду `aipc` в PATH → пропишет себя в MCP-конфиги всех найденных IDE (с бэкапом `.bak`) → откроет меню |
| 3 | В своей IDE обнови MCP-серверы (Refresh / перезапуск) и напиши агенту задачу обычным языком |

Примеры задач агенту:

```
посмотри на мой экран, что за ошибка?
открой YouTube и найди обзор ...
подключись по SSH к 192.168.1.10 и забери лог
```

---

## Меню `aipc`

Открой обычный `cmd` и набери `aipc`. В шапке и заголовке всегда текущая версия (берётся из кода, руками не правится). Управление: **W** — вверх, **S** — вниз, стрелки **↑/↓**, **Enter** — выбор, цифры **1–9** — быстрый выбор, **Q** — назад/выход.

| Пункт | Что делает |
|-------|------------|
| Запустить AiPC-Core | Запускает MCP-сервер для IDE |
| Остановить | Останавливает Core |
| Статус / Проверка работы | Самопроверка: экран, мышь, терминал, конфиг, MCP, браузер |
| Диагностика (doctor) | Полная проверка: установка, PATH, конфиги всех IDE, Chrome, диск |
| Проверить обновления | Смотрит свежий релиз на GitHub; если есть новее — спрашивает и обновляет сам |
| Настроить | Режим `ask/auto/read-only`, IDE, браузер (CDP), SSH-хосты |
| Сервис | Переустановка себя + PATH, перенастройка MCP, kill Core, проверка прав |
| Логи | Последние 20 строк `audit.log` |
| Выход | — |

## Команды без меню

```bat
aipc update    # проверить релиз на GitHub, скачать и переустановить себя
aipc doctor    # та же диагностика, что пунктом меню
aipc kill      # аварийно остановить Core (чужой процесс не тронет)
aipc status / selftest / setup / install / mcp
```

Рамки рисуются только через `rich.Panel` фиксированной ширины — правая стенка не едет ни в старом `conhost`, ни в Windows Terminal. Без эмодзи: только символы `▶ • ✓ ✕`, с автоматическим ASCII-запасом (`OK/X/>/-`) если консоль в старой кодировке.

---

## Подключение IDE

AiPC прописывает себя сам, вручную ничего копировать не надо. Формат везде одинаковый:

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

| IDE | Куда пишется конфиг |
|-----|---------------------|
| Antigravity | `... → MCP Servers → Manage → View raw config` → `~/.gemini/config/mcp_config.json`, затем Refresh |
| Cursor | Settings → MCP → Add server (`mcp.json`) |
| VS Code (Cline / Roo) | `mcp_settings.json` |
| Claude Desktop | `claude_desktop_config.json` |

Готовые пресеты лежат в папке [`mcp_presets/`](mcp_presets/).

---

## Что умеет модель: 31 tool

### Зрение (монитор)

| Tool | Описание |
|------|----------|
| `screen_see` | Скриншот монитора, курсор помечен красным кружком. Вызывать перед кликом и после |
| `screen_region` | Крупный план области (x,y + w,h, всё 0–1000) — для мелких элементов |
| `ui_snapshot` | Дерево UI-элементов с центрами cx/cy 0–1000 — точное наведение без гаданий |
| `windows_list` | Список открытых окон |
| `window_focus` | Фокус окна по подстроке заголовка |
| `window_manage` | Окно: minimize/maximize/restore/close |
| `get_active_window` | Активное окно: заголовок + прямоугольник |

### Управление

| Tool | Описание |
|------|----------|
| `mouse_move` / `mouse_click` / `mouse_drag` | Мышь. Координаты **0–1000 относительные** |
| `mouse_double_click` | Двойной клик |
| `scroll` | Прокрутка |
| `type_text` | Печать текста как с клавиатуры (кириллица через буфер — не роняет) |
| `press_key` | Клавиши, например `["ctrl", "t"]` |
| `clipboard_set` / `clipboard_get` | Буфер обмена: положить / прочитать текст |
| `sleep` | Пауза чтобы дождаться загрузки (до 30 сек) |
| `open_app` | Открыть приложение: `notepad`, `calc`, `chrome` или путь к `.exe` |

### Твой браузер (не пустой headless)

| Tool | Описание |
|------|----------|
| `browser_tabs` | Вкладки **уже открытого** Chrome (нужен флаг `--remote-debugging-port=9222` — ставится пунктом «Настроить») |
| `browser_goto` | Открыть URL в твоём браузере |

### Система и сеть

| Tool | Описание |
|------|----------|
| `fs_list` / `fs_read` / `fs_write` | Файлы (с защитой deny-путей) |
| `run_cmd` | Команда терминала (с deny-листом опасных команд, русский вывод не ломается) |
| `process_list` | Список процессов |
| `download_file` | Скачать файл по URL без браузера (лимит 200 МБ) |
| `web_search_pc` | Веб-поиск со стороны ПК — дополняет нативный поиск модели |
| `ssh_exec` | SSH-команда (хосты, ключи и порты — в `~/.aipc/config.yaml`) |
| `notify_user` | Показать сообщение человеку (всплывающее окно, не блокирует) |
| `ask_user` | Спросить человека Да/Нет/Отмена, ждёт ответа — для режима `ask` |
| `aipc_status` | Версия Core, режим, состояние |

Цикл работы модели: **увидел (`screen_see`) → сделал → снова посмотрел для проверки**. Каждый вызов пишется в `~/.aipc/audit.log`.

---

## Проверенные модели (2026)

| Модель | ID | Контекст | Зачем |
|--------|----|----------|-------|
| Claude Opus 5.5 | `claude-opus-5-5` | 1M | Дешёвый и послушный в агентах; сервер без forced-tool специально под его ограничения |
| GPT-6 Astra | `gpt-6-astra` | 1.05M | Лучший computer use (OSWorld 72.6%) для сложных цепочек |
| GPT-6 Sol / Luna | `gpt-6-sol` / `gpt-6-luna` | 1.05M | Дешевле Astra в разы при ~90% качества |
| Gemini 3.8 Flash | `gemini-3.8-flash` | 1M | Атомарные tools + `thinking_level=high`; не склеивать parts, хранить signatures |
| Claude Fable 5.1 | `claude-fable-5-1` | 1M | Лидер длинных агентских задач |

---

## Безопасность

* Режимы: `ask` (по умолчанию — спрашивать), `auto` (полная автономность), `read-only` (только смотреть).
* Админ-права нужны **только один раз** — на копирование в Program Files и запись PATH. Дальше меню и Core работают без админа.
* Запрещённые команды и пути — в `~/.aipc/config.yaml` (`deny_cmd`, `deny_paths`).
* Каждый вызов tool логируется в `~/.aipc/audit.log` с параметрами.
* Экстренная остановка: пункт меню «Остановить».
* UAC не обходится: elevation только через явный системный промпт Windows.

---

## Структура проекта

```
AiPC/
  aipc/
    __main__.py      # точка входа команды aipc (меню/mcp/status/selftest/setup/install/update/doctor/kill)
    menu.py          # движок меню: W/S+стрелки+Enter, только rich.Panel
    logo.py          # логотип, палитра, версия из кода
    server.py        # MCP-сервер (mcp<2 FastMCP + mcp>=2 MCPServer) + SYSTEM_PROMPT + prompt
    vision.py        # скриншоты/регионы/курсор, окна, UI-дерево (mss + uiautomation)
    control.py       # мышь/клавиатура/буфер/запуск (pyautogui + ctypes)
    os_ops.py        # файлы/терминал с OEM-декодом/процессы
    browser.py       # вкладки Chrome через CDP
    net.py           # web_search_pc (ddgs) + ssh_exec (paramiko) + download_file
    notify.py        # попапы человеку: notify_user + ask_user
    maintenance.py   # update/doctor/kill
    installer.py     # самоустановка в Program Files + PATH + MCP во все IDE
    setup_wizard.py  # мастер: режим/IDE/браузер/SSH
    selftest.py      # проверка работы
    actions.py       # действия пунктов меню
    config.py        # ~/.aipc/config.yaml
    policy.py / audit.py
  mcp_presets/       # готовые MCP-конфиги: antigravity/cursor/vscode/claude
  assets/            # AiPC_Logo.png + AiPC.ico (иконка exe)
  tools/             # install.bat, build_exe.bat, setup_entry.py, exe_entry.py
```

---

## Сборка из исходников

```bat
python -m pip install -r requirements.txt
python -m aipc selftest
python -m aipc mcp
tools\build_exe.bat
```

На выходе: `dist\aipc.exe` и `dist\AiPC-Setup.exe` с иконкой `assets\AiPC.ico`.

---

## FAQ

**Модель говорит «нет доступа к ПК».**
Подключи MCP (раздел выше), перезапусти IDE и напомни: «у тебя есть tools aipc.*, начни с screen_see». Системный промпт в `server.py` делает это автоматически.

**Правая стенка меню едет.**
Обновись до последнего exe: рамки только через `rich.Panel width=64`, плюс авто-переключение консоли в UTF-8.

**Chrome-вкладки не видны (`browser_tabs` пусто).**
Меню → Настроить → Браузер: дописать `--remote-debugging-port=9222` в ярлык Chrome и перезапустить его.

**Интеллектуальная IDE без MCP (веб-чат).**
Веб-версии ChatGPT/Claude не ходят в localhost — для них нужен десктопный клиент IDE из таблицы выше.

---

## Лицензия

MIT. Автор — Sysik. См. [LICENSE](LICENSE).
