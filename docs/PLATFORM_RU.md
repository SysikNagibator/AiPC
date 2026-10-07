# Поддержка платформ AiPC

Статус: **Windows 10/11 полностью; macOS/Linux — базовые фичи работают**
(`pip install aipc-sysik`), полный контроль остаётся за Windows.
Швы кода в `aipc/platform/` (интерфейсы `base.py`, полный
бэкенд `win32.py`, частичный `posix.py`).

## Матрица возможностей

| Группа | Windows | macOS | Linux |
|---|---|---|---|
| Скриншоты (`screen_see`, …) | ok (mss) | ok (mss) | ok под X11 |
| Файлы, терминал, процессы | ok | ok | ok |
| Браузер через CDP | ok | ok (тот же флаг Chrome) | ok |
| Текстовый буфер обмена | ok | ok (`pbcopy/pbpaste`) | ok (`xclip`/`xsel`) |
| Мышь и клавиатура | ok | блокировано: нужно разрешение Accessibility | блокировано: Wayland режет синтетический ввод; X11 работает |
| Окна, UIA-дерево (`ui_snapshot`, `window_*`) | ok (uiautomation) | нет (нужен порт на AXUIElement) | нет (нужен порт на AT-SPI) |
| Захват звука | ok (WASAPI) | нет (нужен ScreenCaptureKit/BlackHole) | нет (нужен монитор PipeWire) |
| Установщик (Program Files/PATH/UAC) | ok | н/д (`pip install`) | н/д (`pip install`) |
| MCP-конфиги IDE | ok | ok (пути XDG/Library) | ok (пути XDG) |
| Самообновление | ok (exe + SHA256) | ok (ассет + SHA256, установка руками) | ok (ассет + SHA256, установка руками) |

## Правила

- Новый платформенный код — за `aipc/platform/base.py` + два бэкенда,
  а не инлайн-`if os.name` по модулям.
- Гейт `require(group)` возвращает чистый `not_supported` вместо трейсбека.
- Бейдж платформ в README меняем, только когда платформа реально работает
  (строка матрицы в основном `ok`, CI зелёный на этой ОС).

## Жёсткие ограничения

- **Wayland**: синтетические мышь/клавиатура отрезаны дизайном. Варианты:
  X11-сессия, демон `ydotool` (root) или API конкретного композитора. Не планируем.
- **macOS**: разрешения Accessibility + Screen Recording — диалоги на каждое
  приложение; неподписанный exe будет спамить. Сначала подпись (см. SIGNING.md).
