<p align="center">
  <img src="https://files.catbox.moe/e9o2sz.png" alt="AiPC by SYSIK">
</p>

<h1 align="center">AiPC by SYSIK</h1>

<p align="center">
  <b>Дайте агенту «это» — и у него появится настоящий ПК.</b><br>
  Экран, мышь, клавиатура, ваш браузер, файлы, терминал, SSH — через нативные инструменты модели.
</p>

<p align="center">
  <a href="https://github.com/SysikNagibator/AiPC/releases"><img src="https://img.shields.io/github/v/release/SysikNagibator/AiPC?label=release" alt="release"></a>
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-blue" alt="platform">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="python">
  <img src="https://img.shields.io/badge/tools-63-brightgreen" alt="tools">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="license">
</p>

<p align="center">
  <b>EN README: <a href="README.md">English version</a></b> · Скиллы: <a href="SKILL_RU.md">SKILL.md</a> · IDE матриции: <a href="docs/IDES_RU.md">docs/IDES.md</a>
</p>

---

## Содержание

- [Что это](#что-это)
- [Почему AiPC](#почему-aipc)
- [Быстрый старт](#быстрый-старт)
- [Меню `aipc`](#меню-aipc)
- [63 инструмента](#63-инструмента-для-модели)
- [Экономия токенов](#экономия-токенов)
- [Подключение MCP](#подключение-mcp)
- [Самообновление](#самообновление)
- [Безопасность](#безопасность)
- [Решение проблем](#решение-проблем)
- [Структура проекта](#структура-проекта)
- [Сборка из исходников](#сборка-из-исходников)
- [Лицензия](#лицензия)

---

## Что это

**AiPC** — это локальный сервис + консольная утилита, которая даёт любому ИИ-агенту полный доступ
к вашему компьютеру через открытый стандарт **MCP** (Model Context Protocol).

```
[ Агент в любой IDE ] --MCP/stdio--> [ AiPC-Core: один локальный сервис ]
                                            |
        +------------------+----------------+------------------+
        |                  |                |                  |
      Зрение            Управление       Браузер           Система/Сеть
   скриншоты,        мышь+клавиатура,  ваш Chrome через   файлы, терминал,
   дерево UI,         приложения,       CDP + история,     процессы, SSH,
   окна               буфер обмена      JS eval           поиск, sysinfo
```

Агент перестаёт быть «текстом в чате» и начинает работать как человек за ПК:
смотрит на монитор, кликает, печатает, открывает приложения, гуглит в **вашем** браузере,
выполняет команды, использует SSH — и проверяет каждый шаг новым скриншотом.

Если модель говорит «у меня нет доступа к компьютеру», встроенный системный промпт
(`aipc/server.py:SYSTEM_PROMPT`, также отдаётся как MCP-промпт `aipc_instructions`)
запрещает такой ответ и требует действовать через инструменты AiPC.

## Почему AiPC

<p align="center">
  <img src="https://files.catbox.moe/lcq318.png" alt="AiPC by SYSIK">
</p>

| Обычные ограничения агента | С AiPC |
|--------------------|-----------|
| Слепой: нет экрана | `screen_see` — скриншот как нативный image-блок, курсор отмечен |
| Клики наугад | `ui_snapshot` / `ui_find` — готовые координаты x/y (0–1000) |
| Печать в пустоту | `focus_type` — проверенный фокус + атомарный ввод; отказывается печатать вслепую |
| Спит и надеется | `wait_for_window` / `wait_for_ui_element` / `wait_for_change` |
| «Сработало?» неизвестно | `screenshot_diff`, `assert_ui`, `logs_tail`, `audit.log` |
| Нет доступа к машине | Файлы, терминал, процессы, SSH/SFTP, браузер, буфер обмена |
| Трата токенов на скриншоты | Нативные image-блоки (~65 символов + изображение против 55K символов base64) |

---

## Быстрый старт

| Шаг | Что делать |
|------|------------|
| 1 | Скачайте **`AiPC_Win_1.0.7.exe`** из [Releases](https://github.com/SysikNagibator/AiPC/releases) и запустите двойным щелчком |
| 2 | При первом запуске он **всё настроит сам**: запросит админа один раз (UAC) → скопирует себя в `C:\Program Files\AiPC\` → добавит команду `aipc` в PATH → зарегистрируется в MCP-конфигах всех обнаруженных IDE (сначала бэкап `.bak`) → откроет меню |
| 3 | В вашей IDE обновите MCP-серверы (Refresh / перезапуск) и дайте агенту задачу на простом языке |

Примеры задач:

```
посмотри на мой экран, что это за ошибка?
открой YouTube и найди обзор на ...
подключись по SSH к 192.168.1.10 и вытащи вчерашний лог
```

Работает с любой моделью 2026 года, поддерживающей инструменты: `claude-opus-5-5`, `gpt-6-astra`,
`gpt-6-sol` / `luna`, `gemini-3.8-flash`, `claude-fable-5-1`.

---

## Меню `aipc`

Откройте обычный `cmd` и введите `aipc`. Зелёная тема, без мерцания (однопоточный
`rich.Live` в альтернативном буфере), градиентный заголовок, пульсирующий маркер выбора,
опасные пункты красным, строка состояния (`режим • версия • инструменты`), быстрый splash при входе.
Управление: **W** вверх, **S** вниз, стрелки **↑/↓**, **Enter** выбор, цифры 1–9,
**Q** назад/выход. Русская раскладка работает по позиции клавиш. Без эмодзи, есть ASCII-фолбэк.

| Пункт | Что делает |
|------|--------------|
| Запустить AiPC-Core | Проверка рукопожатия как в IDE, затем фоновый Core (stdio отсоединён) |
| Остановить | Останавливает Core (никогда не трогает чужие PID) |
| Статус / Самопроверка | Экран, мышь, терминал, конфиг, MCP, браузер |
| Диагностика (doctor) | Установка, PATH, каждый конфиг IDE, Chrome, диск — помечает устаревшие установки |
| Проверить обновления | Смотрит релизы на GitHub; спрашивает перед скачиванием + установкой |
| Настройка | Режим `ask/auto/read-only`, IDE, браузер (флаг CDP), SSH-хосты |
| Сервис | Переустановка + PATH, перенастройка MCP, убить Core, информация где-я |
| Логи | Последние 20 строк `audit.log` |
| Выход | — |

Нет меню под рукой? Те же действия командами:
`aipc update`, `aipc doctor`, `aipc kill`, `aipc keys` (диагностика клавиатуры),
`aipc status`, `aipc selftest`, `aipc setup`, `aipc install`, `aipc mcp`.

---

## 63 инструмента для модели

**Зрение (15):** `screen_see`, `screen_region`, `ui_snapshot` (по умолчанию активное окно:
0.69с / 17 узлов против 1.7с / 200 рабочих столов), `ui_find`, `assert_ui`, `windows_list`,
`window_focus` (проверенный), `window_manage`, `window_find`, `get_active_window`,
`wait_for_window`, `wait_for_ui_element`, `wait_for_change`, `screenshot_diff`, `screen_info`.

**Мышь и клавиатура (17):** `mouse_move/click/drag/double_click/right_click/middle_click`
(перетаскивание с ctrl/shift/alt), `scroll`, `type_text` (авторазбивка, безопасно для кириллицы),
`press_key`, `key_down/up`, `clipboard_set/get` (+изображения), `sleep`, `open_app`,
`focus_type` (проверенный фокус + атомарный ввод — единственный правильный способ печати).

**Браузер (6):** `browser_tabs`, `browser_goto`, `browser_eval` (JS через CDP —
надёжнее кликов по координатам), `browser_active_tab`, `browser_close_tab`,
`browser_history_search` (копия БД History только для чтения).

**Файлы и система (13):** `fs_list/read/write/find/stat/mkdir/delete/move`
(атомарная запись + `.bak`, защита от бинарников, пагинация, deny-листы),
`run_cmd` (раздельные stdout/stderr, декодирование русской OEM, deny-лист),
`process_list/find`, `wait_for_process`, `download_file` (потоково, без ограничения размера).

**Сеть и машина (5):** `web_search_pc`, `ssh_exec`, `ssh_sftp_get/put`
(дружелюбно к потокам 200 МБ+), `sys_info` (батарея/память/CPU/диски),
`net_check`, `env_get` (отказывается от имён, похожих на секреты).

**Человек и отладка (4):** `notify_user` (всплывающее окно, не блокирует), `ask_user` (Да/Нет,
блокирует для решения человека), `aipc_status`, `logs_tail`.

Цикл агента: **увидеть (`screen_see`) → сделать → снова увидеть для проверки**.
Ошибки структурны: `{"ok": false, "reason": "not_found|timeout|denied|..."}`.
Каждый вызов выполняется ровно один раз, сериализованно; каждый вызов попадает в `~/.aipc/audit.log`
(ротация 2 МБ).

## Экономия токенов

- Скриншоты передаются как **нативные MCP image-блоки**: ~65 символов JSON + изображение
  вместо ~55K символов base64-текста (~10x дешевле за скриншот).
  `raw=true` возвращает устаревший base64, если клиент не умеет отображать изображения.
- Узлы UI компактны: `{"t","n","x","y"}` вместо длинных ключей.
- `ui_snapshot` по умолчанию берёт активное окно; фильтры по роли/имени ещё больше режут токены.
- Предпочитайте поиск перечислению: `ui_find` / `window_find` / `fs_find` / `process_find`.
- Все описания инструментов укладываются в одну короткую строку.

---

## Подключение MCP

AiPC регистрирует себя при каждом запуске меню (19 конфигов в 14 семействах IDE).
Ручной формат для справки:

```json
{
  "mcpServers": {
    "aipc": {
      "command": "C:\\Program Files\\AiPC\\AiPC_Win_1.0.7.exe",
      "args": ["mcp"]
    }
  }
}
```

Полная матрица 40 IDE (авто / пресет / мост): [docs/IDES.md](docs/IDES.md).
Готовые файлы: [mcp_presets/](mcp_presets/). Установка в стиле skill: [SKILL.md](SKILL.md).

Облачные IDE без доступа к localhost (Claude.ai, Manus, Devin, Bolt, v0, Lovable,
Replit…) не могут достучаться до `127.0.0.1` — см. раздел «Bridge» в `docs/IDES.md`.

## Самообновление

Меню → «Проверить обновления» (или `aipc update`): сравнивает с последним релизом GitHub,
показывает changelog и только после вашего явного **Да** скачивает и переустанавливает
себя (UAC). Версия всегда видна в заголовке меню; `aipc doctor` помечает
устаревшую установку в Program Files.

---

## Безопасность

- Режимы: `ask` (по умолчанию — модель должна подтвердить через `ask_user`), `auto`,
  `read-only` (все изменяющие инструменты блокируются **на стороне сервера**, а не только промптом).
- Права админа нужны **один раз** — для копирования в Program Files + записи PATH.
- Deny-листы для команд (mimikatz, шаблоны ransomware, закодированный PowerShell,
  нормализация `^`-обфускации) и путей (секреты браузера, приватные ключи,
  кусты реестра, `System32`) лежат в `~/.aipc/config.yaml` и **автообновляются**
  (`safety.version`) без стирания ваших дополнений.
- Ввод идёт только в **проверенное** активное окно (`focus_type`).
- Защита секретов: `env_get` отказывается от имён `*KEY/*TOKEN/*SECRET/*PASSWORD*`.
- Аварийная остановка: меню → Остановить, или `aipc kill` (сначала проверяет, что PID наш).

---

## Решение проблем

| Симптом | Решение |
|---------|-----|
| Модель говорит «нет доступа к ПК» | Переподключите MCP (Refresh / перезапуск IDE), напомните: «у тебя есть инструменты aipc.*, начни с screen_see» |
| Меню не реагирует на клавиши | Запустите `aipc keys`, нажмите W/S/стрелки/Enter/Esc — пришлите нам 5 строк |
| Команда `aipc` неизвестна | Откройте **новый** cmd (PATH применяется к новым оболочкам); переустановите через `dist\aipc.exe` |
| Правая стенка меню съезжает | Обновитесь: с 1.0.4.4 кадры рендерятся только через `rich.Panel` фиксированной ширины |
| Вкладки Chrome не видны | Меню → Настройка → Браузер (добавляет `--remote-debugging-port=9222`), перезапустите Chrome |
| Старая версия в Program Files | `aipc doctor` подскажет; запустите свежий `dist\AiPC_Win_1.0.7.exe` → UAC → обновлено |
| GitHub страница/API 404 | Наш репозиторий однажды затроттлили эвристики GitHub за злоупотребления; зеркало + процесс апелляции в issues |

---

## Структура проекта

```
AiPC/
  aipc/            # server.py (MCP) · vision/control/os_ops/browser/net/sysinfo
                   # notify · installer (self-install + 19 IDE configs)
                   # maintenance (update/doctor/kill) · menu · policy/audit
  mcp_presets/     # готовые MCP-конфиги (16 файлов)
  assets/          # логотип + иконка exe (видна на светлой и тёмной темах)
  tools/           # build_exe.bat · build_icon.py · sign.bat · version_info.txt
  tests/           # pytest: policy, installer merge, server (19 тестов)
  docs/            # IDES.md (40 IDE) · SIGNING.md (SmartScreen)
  SKILL.md         # установка skill одним файлом · CHANGELOG.md · LICENSE (MIT)
```

---

## Сборка из исходников

```bat
python -m pip install -r requirements.txt
python -m pytest tests -q
python -m aipc selftest
tools\build_exe.bat
```

Выход: `dist\AiPC_Win_1.0.7.exe` (~36 МБ, иконка + publisher version-info) и `dist\AiPC-Setup.exe`.
Подпись, убирающая синий SmartScreen: см. [docs/SIGNING.md](docs/SIGNING.md) (нужен
сертификат code-signing: Certum Open Source ~€25/год — самый дешёвый старт).

---

## Лицензия

MIT. Автор — SYSIK. См. [LICENSE](LICENSE).
