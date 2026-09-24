"""Точка входа команды `aipc`. Использование:
  aipc            -> красивое меню
  aipc mcp        -> MCP-сервер (stdio) для IDE
  aipc status     -> быстрая проверка
  aipc selftest   -> проверка работы
  aipc install    -> установка в PATH (требует админа, через Setup)
  aipc setup      -> мастер настройки
"""
from __future__ import annotations

import sys


def _first_run_setup() -> None:
    """Авто-настройка при запуске exe: конфиг + эталонные пресеты рядом. Без вопросов."""
    try:
        from .config import ensure_default_config

        ensure_default_config()
    except Exception:
        pass
    try:
        import json
        from pathlib import Path

        from .installer import mcp_server_entry

        command, args = mcp_server_entry()
        preset = {"mcpServers": {"aipc": {"command": command, "args": args}}}
        base = Path(__file__).resolve().parent.parent / "mcp_presets"
        for fname in ("antigravity.json", "cursor.json", "vscode.json", "claude_desktop.json"):
            p = base / fname
            if not p.exists():
                try:
                    p.write_text(json.dumps(preset, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
    except Exception:
        pass


def cmd_menu() -> int:
    from . import __version__ as _ver
    from .menu import MenuItem, run_menu
    from . import actions as A
    from . import setup_wizard as W
    from . import selftest as T

    _first_run_setup()  # пресеты рядом + конфиг
    try:
        from .installer import ensure_installed

        ensure_installed()  # сам в Program Files + MCP во все IDE (с UAC если надо)
    except SystemExit:
        raise
    except Exception:
        pass
    while True:
        idx = run_menu(
            f"AiPC от Sysik v{_ver}",
            [
                MenuItem("Запустить AiPC-Core", "run"),
                MenuItem("Остановить", "stop"),
                MenuItem("Статус / Проверка работы", "status"),
                MenuItem("Настроить", "setup"),
                MenuItem("Сервис (PATH, автозапуск)", "service"),
                MenuItem("Логи", "logs"),
                MenuItem("Выход", "exit"),
            ],
        )
        if idx == "quit" or idx == 6:
            return 0
        if idx == 0:
            A.start_core()
        elif idx == 1:
            A.stop_core()
        elif idx == 2:
            T.show_selftest()
        elif idx == 3:
            W.setup_menu()
        elif idx == 4:
            service_menu()
        elif idx == 5:
            A.show_logs()


def service_menu() -> None:
    from .menu import MenuItem, run_menu
    from .installer import is_admin, is_installed

    while True:
        idx = run_menu(
            "Сервис",
            [
                MenuItem("Переустановить себя + MCP (нужен админ)", "path"),
                MenuItem("Только перенастроить MCP во всех IDE", "mcp"),
                MenuItem("Проверить: где лежу / админ", "admin"),
                MenuItem("Назад", "back"),
            ],
        )
        if idx == "quit" or idx == 3:
            return
        from rich.console import Console
        from rich.panel import Panel
        from rich.align import Align
        from .logo import MENU_WIDTH, THEME

        console = Console(highlight=False, legacy_windows=False)
        if idx == 0:
            from .installer import ensure_installed

            try:
                where = ensure_installed()
                console.print(Align.center(Panel(f"Готово. Работаю из: {where}", width=MENU_WIDTH, border_style="green")))
            except SystemExit:
                return
            input("\nEnter... ")
        elif idx == 1:
            from .installer import configure_all_ides

            lines = [f"{name}: {msg}" for name, _ok, msg in configure_all_ides()]
            console.print(Align.center(Panel("\n".join(lines), title=" MCP ", width=MENU_WIDTH, border_style="green")))
            input("\nEnter... ")
        elif idx == 2:
            import sys as _sys
            from .installer import current_exe

            console.print(Align.center(Panel(f"admin={is_admin()}\nfrozen={getattr(_sys, 'frozen', False)}\ninstalled={is_installed()}\nexe={current_exe()}", width=MENU_WIDTH, border_style=THEME["border"])))
            input("\nEnter... ")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return cmd_menu()
    cmd = argv[0].lower()
    if cmd == "-m":
        # Совместимость: старые запуски вида `aipc.exe -m aipc mcp` (баг 1.0.0).
        # Такого больше не генерируем, но чужой вызов молча чиним вместо ошибки.
        argv = argv[1:]
        if argv and argv[0].lower() == "aipc":
            argv = argv[1:]
        if not argv:
            return cmd_menu()
        cmd = argv[0].lower()
    if cmd == "mcp":
        from .server import main as server_main

        server_main()
        return 0
    if cmd == "status":
        from . import actions as A

        A.show_status()
        return 0
    if cmd == "selftest":
        from .selftest import show_selftest

        show_selftest()
        return 0
    if cmd == "setup":
        from .setup_wizard import setup_menu

        setup_menu()
        return 0
    if cmd == "install" or cmd == "--self-install":
        # Привилегированный шаг: копия в Program Files + PATH + MCP во все IDE.
        # Без админа — сам просит UAC и делает, руками ничего не надо.
        from .installer import ensure_installed, is_admin, is_frozen, privileged_self_install, relaunch_as_admin

        if cmd == "--self-install" and not is_admin():
            relaunch_as_admin("--self-install")
            return 0
        if cmd == "--self-install":
            return privileged_self_install()
        ensure_installed()
        return 0
    if cmd in ("--help", "-h", "help"):
        print(__doc__)
        return 0
    if cmd in ("--version", "-v"):
        from aipc import __version__

        print(__version__)
        return 0
    print(f"Неизвестная команда: {cmd}\n{__doc__}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
