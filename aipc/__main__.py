"""Точка входа команды `aipc`. Использование:
  aipc            -> красивое меню
  aipc mcp        -> MCP-сервер (stdio) для IDE
  aipc status     -> быстрая проверка
  aipc selftest   -> проверка работы
  aipc setup      -> мастер настройки
  aipc install    -> установка в PATH (требует админа, через Setup)
  aipc update     -> самообновление с GitHub
  aipc doctor     -> полная диагностика
  aipc kill       -> аварийно остановить Core
  aipc keys       -> проверка клавиатуры (что видит меню)
  aipc audit      -> просмотр audit.log (--tail N, --since ISO, --tool NAME)
  aipc panic      -> аварийный стоп всех инструментов (снять: aipc panic --off)
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


# Группы главного меню в одном месте: списки key, разделитель — между группами.
MENU_GROUPS = [["run", "stop"], ["status", "doctor", "update"],
               ["setup", "service", "logs"], ["exit"]]


def cmd_menu() -> int:
    from .menu import MenuItem, run_menu
    from . import actions as A
    from . import setup_wizard as W
    from . import selftest as T
    from .i18n import t

    try:
        from .panic import start_watcher

        start_watcher()
    except Exception:
        pass
    _first_run_setup()  # пресеты рядом + конфиг
    try:
        from .maintenance import refresh_update_cache_async

        refresh_update_cache_async()  # фоновая проверка релизов на новом гите
    except Exception:
        pass
    try:
        from .installer import ensure_installed

        ensure_installed()  # сам в Program Files + MCP во все IDE (с UAC если надо)
    except SystemExit:
        raise
    except Exception:
        pass
    first = True
    while True:
        idx = run_menu(
            t("title.menu"),
            [
                MenuItem(t("menu.run"), "run", t("menu.run.hint")),
                MenuItem(t("menu.stop"), "stop", t("menu.stop.hint")),
                MenuItem(t("menu.status"), "status", t("menu.status.hint")),
                MenuItem(t("menu.doctor"), "doctor", t("menu.doctor.hint")),
                MenuItem(t("menu.update"), "update", t("menu.update.hint")),
                MenuItem(t("menu.setup"), "setup", t("menu.setup.hint")),
                MenuItem(t("menu.service"), "service", t("menu.service.hint")),
                MenuItem(t("menu.logs"), "logs", t("menu.logs.hint")),
                MenuItem(t("menu.exit"), "exit", t("menu.exit.hint")),
            ],
            splash_first=first,
            groups=MENU_GROUPS,
            show_title=False,
        )
        first = False
        from .menu import _menu_log

        _menu_log(f"menu-result idx={idx}")
        if idx == "quit" or idx == 8:
            _menu_log("menu exit")
            return 0
        try:
            _run_action(idx, A, T, W)
        except Exception:
            import traceback

            _menu_log("action crash, see console")
            from .i18n import t as _t
            from .menu import pause, show_card

            show_card(_t("act.error"),
                      _t("act.crash") + "\n" + traceback.format_exc()[-1500:],
                      kind="err")
            pause()


def _run_action(idx, A, T, W) -> None:
    """Диспетчер пунктов меню. Исключения ловит вызыватель (видимый трейс + пауза)."""
    if idx == 0:
        A.start_core()
    elif idx == 1:
        A.stop_core()
    elif idx == 2:
        T.show_selftest()
    elif idx == 3:
        A.show_doctor()
    elif idx == 4:
        if A.show_update_check():
            import sys as _sys

            _sys.exit(0)
    elif idx == 5:
        W.setup_menu()
    elif idx == 6:
        service_menu()
    elif idx == 7:
        A.show_logs()


def service_menu() -> None:
    from .menu import MenuItem, run_menu
    from .installer import is_admin, is_installed
    from .i18n import t

    while True:
        idx = run_menu(
            t("title.service"),
            [
                MenuItem(t("service.reinstall"), "path", t("service.reinstall.hint")),
                MenuItem(t("service.mcp"), "mcp", t("service.mcp.hint")),
                MenuItem(t("service.kill"), "kill", t("service.kill.hint")),
                MenuItem(t("service.where"), "admin", t("service.where.hint")),
                MenuItem(t("service.back"), "back", t("service.back.hint")),
            ],
        )
        if idx == "quit" or idx == 4:
            return
        from .i18n import t as _t
        from .menu import pause, show_card

        try:
            from .menu import clear_screen

            clear_screen()
        except Exception:
            pass
        if idx == 0:
            from .installer import ensure_installed

            try:
                where = ensure_installed()
                show_card(t("title.service"),
                          _t("svc.done").format(where=where), kind="ok")
            except SystemExit:
                return
            pause()
        elif idx == 1:
            from .installer import configure_all_ides

            lines = [f"{name}: {msg}" for name, _ok, msg in configure_all_ides()]
            show_card(_t("svc.mcp"), "\n".join(lines), kind="ok")
            pause()
        elif idx == 2:
            from .maintenance import kill_core

            res = kill_core()
            show_card(t("title.service"),
                      res.get("note", res.get("error", "")),
                      kind="ok" if res.get("ok") else "err")
            pause()
        elif idx == 3:
            import sys as _sys
            from .installer import current_exe

            show_card(t("title.service"),
                      f"admin={is_admin()}\nfrozen={getattr(_sys, 'frozen', False)}\n"
                      f"installed={is_installed()}\nexe={current_exe()}")
            pause()


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

        server_main(argv)
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
        from .installer import ide_config_paths, plan_install

        args = argv[1:]
        if "--list-ides" in args:
            for name, path, _oi, _w in ide_config_paths():
                mark = "есть" if path.exists() else "нет"
                print(f"{name}: {path} [{mark}]")
            return 0
        only = [args[i + 1] for i, a in enumerate(args[:-1]) if a == "--ide"]
        create_missing = "--all" in args
        if "--dry-run" in args:
            from .installer import plan_install as _plan

            for item in _plan(only or None, create_missing):
                print(f"[{item['action']}] {item['kind']}: {item['target']}\n    {item['detail']}")
            return 0
        ensure_installed()
        from .installer import configure_all_ides

        for name, ok, msg in configure_all_ides(only=only or None,
                                                create_missing=create_missing):
            print(f"[mcp] {name}: {msg}")
        return 0
    if cmd == "uninstall":
        from .installer import uninstall_self

        args = argv[1:]
        only = [args[i + 1] for i, a in enumerate(args[:-1]) if a == "--ide"]
        if "--yes" not in args:
            if not sys.stdin.isatty():
                print("нужен --yes в неинтерактивном режиме")
                return 2
            ans = input("Убрать AiPC из IDE-конфигов, PATH и Program Files? [y/N] ").strip().lower()
            if ans not in ("y", "yes", "д", "да"):
                print("отмена")
                return 0
        bad = 0
        for name, ok, msg in uninstall_self(only or None):
            print(f"[rm] {name}: {msg}")
            bad += 0 if ok else 1
        return 1 if bad else 0
    if cmd == "update":
        from .maintenance import self_update

        return self_update()
    if cmd == "doctor":
        from . import actions as A

        A.show_doctor()
        return 0
    if cmd == "kill":
        from .maintenance import kill_core

        res = kill_core()
        print(res.get("note", res.get("error", res)))
        return 0 if res.get("ok") else 1
    if cmd == "audit":
        return cmd_audit(argv[1:])
    if cmd == "panic":
        from . import panic as _panic

        if "--off" in argv[1:]:
            print("снято" if _panic.clear_panic() else "не было активно")
            return 0
        reason = " ".join(a for a in argv[1:] if not a.startswith("-")) or "ручная остановка"
        _panic.set_panic(reason)
        print("PANIC активен: все инструменты заблокированы. Снять: aipc panic --off")
        print("Горячая клавиша Ctrl+Alt+Shift+K тоже ставит PANIC (снимается только через CLI).")
        return 0


def cmd_audit(args: list[str]) -> int:
    """aipc audit --tail N | --since ISO | --tool NAME — просмотр audit.log."""
    from .audit import tail_events

    tail = 50
    since = ""
    tool = ""
    it = iter(args)
    for a in it:
        if a == "--tail":
            try:
                tail = max(1, min(500, int(next(it))))
            except (StopIteration, ValueError):
                print("нужно число после --tail")
                return 2
        elif a == "--since":
            try:
                since = next(it)
            except StopIteration:
                print("нужна дата после --since (ISO, напр. 2026-10-06T10:00)")
                return 2
        elif a == "--tool":
            try:
                tool = next(it)
            except StopIteration:
                print("нужно имя после --tool")
                return 2
    evs = tail_events(tail, since, tool)
    if not evs:
        print("событий нет")
        return 0
    for e in evs:
        dec = f"[{e.get('decision')}]" if e.get("decision") else ""
        print(f"{e.get('ts')} {e.get('mode')} {e.get('tool')} ok={e.get('ok')} {dec} :: {e.get('note', '')}")
    return 0
    if cmd == "keys":
        from .menu import _read_key_wide

        print("Жми клавиши (W/S/стрелки/Enter/Esc), 5 нажатий...")
        for i in range(5):
            try:
                print(f"  {i + 1}: {_read_key_wide()}")
            except (OSError, EOFError, KeyboardInterrupt) as e:
                print(f"  ОШИБКА ВВОДА: {type(e).__name__}: {e}")
                return 1
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
