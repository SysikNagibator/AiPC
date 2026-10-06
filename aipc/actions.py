"""Действия пунктов меню (без эмодзи)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .config import config_dir, ensure_default_config, load_config


def _rich():
    from .logo import MENU_WIDTH, THEME
    try:
        from .menu import _ensure_utf8

        _ensure_utf8()
    except Exception:
        pass
    try:
        from .menu import clear_screen

        clear_screen()
    except Exception:
        pass
    # Чистый экран под каждый экшен: прошлые выводы не висят хвостом.
    # clear_screen идёт через WinAPI cls (ANSI-clear молча глотается рядом консолей).
    return MENU_WIDTH, THEME


def show_status() -> None:
    _rich()
    from .i18n import t
    from .logo import MARK_ERR, MARK_OK, safe_mark
    from .config import load_config

    ok_m, err_m = safe_mark(MARK_OK), safe_mark(MARK_ERR)

    cfg = load_config()
    from aipc import __version__

    lines = [
        f"{t('act.status.mode')}{cfg.get('mode')}",
        f"{t('act.status.config')}{config_dir() / 'config.yaml'}",
        f"{t('act.status.version')}{__version__}",
    ]
    # Проверки без падений
    checks = []
    for mod, key in [("mss", "st.shot"), ("pyautogui", "st.mouse"),
                     ("mcp", "st.mcp"), ("rich", "st.menu")]:
        name = t(key)
        try:
            __import__(mod)
            checks.append(f"{ok_m} {name}")
        except ImportError:
            checks.append(f"{err_m} {name} (pip install {mod})")
    # имена проверок локализуем отдельно, модули — нет
    from .menu import show_card, pause

    show_card(t("act.status.title"), "\n".join(lines + ["", *checks]))
    pause()


def _core_command() -> tuple[list, str | None]:
    """Команда запуска Core + cwd. Одна на handshake и на фон."""
    from .installer import current_exe, is_frozen

    if is_frozen():
        return [str(current_exe()), "mcp"], None
    return [sys.executable, "-m", "aipc", "mcp"], str(Path(__file__).resolve().parent.parent)


def _launch_core():
    """Запустить Core ОТВЯЗАННО от консоли меню: stdin/stdout/stderr в DEVNULL.

    Иначе MCP-сервер на stdio читает те же нажатия что меню (клавиши пропадают),
    а протокольные байты мусорят в консоль.
    """
    cmd, cwd = _core_command()
    return subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def handshake_core(timeout: float = 25.0) -> dict:
    """Проверка как у IDE: спавн Core с пайпами, initialize, tools/list, прибить."""
    import asyncio

    async def _go():
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        cmd, cwd = _core_command()
        params = StdioServerParameters(command=cmd[0], args=cmd[1:], cwd=cwd)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as s:
                await s.initialize()
                tools = await s.list_tools()
                return len(tools.tools)

    try:
        n = asyncio.run(asyncio.wait_for(_go(), timeout))
        return {"ok": True, "tools": n}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


def _proc_alive(pid: int) -> bool:
    try:
        import psutil  # type: ignore

        return bool(psutil.pid_exists(pid))
    except Exception:
        pass
    try:
        r = subprocess.run(f'tasklist /FI "PID eq {pid}" /FO CSV /NH', shell=True,
                           capture_output=True, text=True, timeout=10)
        out = (r.stdout or "").lower()
        return bool(out.strip()) and "no tasks" not in out and "нет задач" not in out
    except Exception:
        return False


def start_core() -> None:
    _rich()
    from .i18n import t
    from .policy import load_mode

    ensure_default_config()
    pid_file = config_dir() / "aipc.pid"
    try:
        from .menu import show_card, pause

        show_card(t("act.start.title"), t("act.start.checking"))
        hs = handshake_core()
        if not hs.get("ok"):
            show_card(t("act.error"),
                      t("act.start.noanswer").format(err=hs.get("error")),
                      kind="err")
            pause()
            return
        proc = _launch_core()
        pid_file.write_text(str(proc.pid), encoding="utf-8")
        alive = _wait_alive(proc.pid, 3.0)
        if alive:
            show_card(t("act.start.title"),
                      t("act.start.up").format(pid=proc.pid, n=hs.get("tools"),
                                              mode=load_mode()),
                      kind="ok")
        else:
            show_card(t("act.warn"),
                      t("act.start.silent").format(pid=proc.pid),
                      kind="warn")
    except Exception as e:
        from .menu import show_card, pause

        show_card(t("act.error"), t("act.start.fail").format(err=e), kind="err")
    pause()


def _wait_alive(pid: int, timeout: float) -> bool:
    import time as _time

    deadline = _time.monotonic() + timeout
    while _time.monotonic() < deadline:
        if _proc_alive(pid):
            _time.sleep(0.4)
            if _proc_alive(pid):
                return True
        else:
            return False
        _time.sleep(0.3)
    return _proc_alive(pid)


def stop_core() -> None:
    _rich()
    from .i18n import t
    from .maintenance import kill_core
    from .menu import pause, show_card

    res = kill_core()
    if res.get("ok"):
        show_card(t("act.stop.title"), res.get("note", t("act.stop.done")),
                  kind="ok")
    else:
        show_card(t("act.error"), res.get("error", ""), kind="err")
    pause()


def show_doctor() -> None:
    _rich()
    from .i18n import t
    from .logo import MARK_ERR, MARK_OK, safe_mark
    from .maintenance import doctor
    from .menu import pause, show_card

    show_card(t("act.doctor.title"), t("act.doctor.busy"))
    try:
        results = doctor()
    except Exception as e:
        import traceback

        show_card(t("act.error"),
                  t("act.doctor.crashed").format(
                      err=e, trace=traceback.format_exc()[-800:]),
                  kind="err")
        pause()
        return
    ok_m, err_m = safe_mark(MARK_OK), safe_mark(MARK_ERR)
    lines = []
    all_ok = True
    for name, ok, note in results:
        all_ok = all_ok and ok
        mark = ok_m if ok else err_m
        lines.append(f"{mark} {name}: {note}")
    title = t("act.doctor.ok") if all_ok else t("act.doctor.issues")
    show_card(title.strip(), "\n".join(lines),
              kind="ok" if all_ok else "warn")
    pause()


def show_update_check() -> bool:
    """Проверить релиз на GitHub. Если есть новее — спросить и обновить. True = обновление запущено."""
    from .maintenance import check_update, self_update
    from .menu import MenuItem, run_menu
    from .i18n import t
    from .menu import pause, show_card

    _rich()
    show_card(t("act.update.title"), t("act.update.checking"))
    info = check_update()
    if not info.get("ok"):
        show_card(t("act.update.title"),
                  t("act.update.fail").format(err=info.get("error")),
                  kind="err")
        pause()
        return False
    if not info.get("update"):
        show_card(t("act.update.title"),
                  t("act.update.fresh").format(ver=info.get("current")),
                  kind="ok")
        pause()
        return False
    notes = info.get("notes", "")
    body = f"{t('act.update.found')}: {info.get('current')} -> {info.get('latest')}\n\n{notes[:800]}"
    show_card(t("act.update.title"), body, kind="warn")
    choice = run_menu(t("update.ask"), [MenuItem(t("update.yes"), "yes"), MenuItem(t("update.no"), "no")])
    if choice == "quit" or choice == 1:
        return False
    code = self_update()
    if code == 0:
        show_card(t("act.update.title"), t("act.update.started"), kind="ok")
        try:
            from .i18n import t as _t

            input(_t("act.update.exit"))
        except (EOFError, KeyboardInterrupt):
            pass
        return True
    pause()
    return False


def show_logs() -> None:
    _rich()
    from .i18n import t
    from .menu import pause, show_card

    p = config_dir() / "audit.log"
    text = ""
    try:
        if p.exists():
            # Хвост файла без чтения всего лога в память
            with p.open("rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 65536))
                tail = f.read().decode("utf-8", errors="replace")
            lines = tail.splitlines()[-20:]
            text = "\n".join(lines) or t("act.logs.empty")
        else:
            text = t("act.logs.nofile")
    except Exception as e:
        text = t("act.logs.err").format(err=e)
    show_card(t("act.logs.title"), text)
    pause()
