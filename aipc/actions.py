"""Действия пунктов меню (без эмодзи)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .config import config_dir, ensure_default_config, load_config


def _rich():
    from rich.console import Console
    from rich.panel import Panel
    from rich.align import Align
    from .logo import MENU_WIDTH, THEME
    try:
        from .menu import _ensure_utf8

        _ensure_utf8()
    except Exception:
        pass
    console = Console(highlight=False, legacy_windows=False)
    # Чистый экран под каждый экшен: прошлые выводы не висят хвостом.
    # clear_screen идёт через WinAPI cls (ANSI-clear молча глотается рядом консолей).
    try:
        from .menu import clear_screen

        clear_screen()
    except Exception:
        pass
    return console, Panel, Align, MENU_WIDTH, THEME


def show_status() -> None:
    console, Panel, Align, WIDTH, THEME = _rich()
    from .logo import MARK_OK, MARK_ERR, safe_mark
    from .config import load_config

    ok_m, err_m = safe_mark(MARK_OK), safe_mark(MARK_ERR)

    cfg = load_config()
    from aipc import __version__

    lines = [
        f"Режим: {cfg.get('mode')}",
        f"Конфиг: {config_dir() / 'config.yaml'}",
        f"Версия tools: {__version__}",
    ]
    # Проверки без падений
    checks = []
    for mod, name in [("mss", "скриншоты"), ("pyautogui", "мышь/клава"), ("mcp", "MCP-сервер"), ("rich", "меню")]:
        try:
            __import__(mod)
            checks.append(f"{ok_m} {name}")
        except ImportError:
            checks.append(f"{err_m} {name} (pip install {mod})")
    body = "\n".join(lines + ["", *checks])
    console.print(Align.center(Panel(body, title=" Статус ", width=WIDTH, border_style=THEME["border"])))
    input("\nEnter чтобы вернуться... ")


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
    console, Panel, Align, WIDTH, THEME = _rich()
    ensure_default_config()
    pid_file = config_dir() / "aipc.pid"
    try:
        console.print(Align.center(Panel("Проверяю Core как IDE (handshake)...",
                                         title=" Запустить ", width=WIDTH, border_style=THEME["border"])))
        hs = handshake_core()
        if not hs.get("ok"):
            console.print(Align.center(Panel(f"Core не отвечает: {hs.get('error')}\nСмотри Doctor.",
                                             title=" Ошибка ", width=WIDTH, border_style="red")))
            input("\nEnter чтобы вернуться... ")
            return
        proc = _launch_core()
        pid_file.write_text(str(proc.pid), encoding="utf-8")
        alive = _wait_alive(proc.pid, 3.0)
        if alive:
            console.print(Align.center(Panel(
                f"AiPC-Core запущен и отвечает.\nPID {proc.pid} | tools: {hs.get('tools')} | режим ask",
                title=" Запустить ", width=WIDTH, border_style="green")))
        else:
            console.print(Align.center(Panel(
                f"Процесс {proc.pid} запустился, но не отвечает.\nСмотри Логи и Doctor.",
                title=" Внимание ", width=WIDTH, border_style="yellow")))
    except Exception as e:
        console.print(Align.center(Panel(f"Не запустился: {e}", title=" Ошибка ", width=WIDTH, border_style="red")))
    input("\nEnter чтобы вернуться... ")


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
    console, Panel, Align, WIDTH, THEME = _rich()
    from .maintenance import kill_core

    res = kill_core()
    if res.get("ok"):
        console.print(Align.center(Panel(res.get("note", "Остановлен."), title=" Стоп ", width=WIDTH, border_style="green")))
    else:
        console.print(Align.center(Panel(f"Ошибка: {res.get('error')}", title=" Ошибка ", width=WIDTH, border_style="red")))
    input("\nEnter чтобы вернуться... ")


def show_doctor() -> None:
    console, Panel, Align, WIDTH, THEME = _rich()
    from rich.table import Table
    from .logo import MARK_OK, MARK_ERR, safe_mark
    from .maintenance import doctor

    console.print(Align.center(Panel("Собираю диагностику...", title=" Doctor ", width=WIDTH,
                                     border_style=THEME["border"])))
    try:
        results = doctor()
    except Exception as e:
        import traceback

        console.print(Align.center(Panel(f"Doctor упал: {e}\n{traceback.format_exc()[-800:]}",
                                         title=" Ошибка ", width=WIDTH, border_style="red")))
        input("\nEnter чтобы вернуться... ")
        return
    ok_m, err_m = safe_mark(MARK_OK), safe_mark(MARK_ERR)
    table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    table.add_column("check")
    table.add_column("res")
    all_ok = True
    for name, ok, note in results:
        all_ok = all_ok and ok
        mark = ok_m if ok else err_m
        style = THEME["ok"] if ok else THEME["err"]
        table.add_row(name, f"[{style}]{mark} {note}[/{style}]")
    title = " Doctor: ВСЕ ОК " if all_ok else " Doctor: есть замечания "
    console.print(Align.center(Panel(table, title=title, width=WIDTH, border_style="green" if all_ok else "yellow")))
    input("\nEnter чтобы вернуться... ")


def show_update_check() -> bool:
    """Проверить релиз на GitHub. Если есть новее — спросить и обновить. True = обновление запущено."""
    from .maintenance import check_update, self_update
    from .menu import MenuItem, run_menu

    console, Panel, Align, WIDTH, THEME = _rich()
    console.print(Align.center(Panel("Проверяю GitHub...", title=" Обновления ", width=WIDTH, border_style=THEME["border"])))
    info = check_update()
    if not info.get("ok"):
        console.print(Align.center(Panel(f"Не проверить: {info.get('error')}\nПроверь интернет и попробуй позже.", title=" Обновления ", width=WIDTH, border_style="red")))
        input("\nEnter чтобы вернуться... ")
        return False
    if not info.get("update"):
        console.print(Align.center(Panel(f"У тебя свежее: {info.get('current')}", title=" Обновления ", width=WIDTH, border_style="green")))
        input("\nEnter чтобы вернуться... ")
        return False
    notes = info.get("notes", "")
    body = f"Текущая: {info.get('current')}\nНовая: {info.get('latest')}\n\n{notes[:800]}"
    console.print(Align.center(Panel(body, title=" Найдено обновление ", width=WIDTH, border_style="yellow")))
    choice = run_menu("Обновить сейчас?", [MenuItem("Да, скачать и обновить", "yes"), MenuItem("Нет, позже", "no")])
    if choice == "quit" or choice == 1:
        return False
    code = self_update()
    if code == 0:
        console.print(Align.center(Panel("Обновление запущено, это окно можно закрыть.", width=WIDTH, border_style="green")))
        input("\nEnter чтобы выйти... ")
        return True
    input("\nEnter чтобы вернуться... ")
    return False


def show_logs() -> None:
    console, Panel, Align, WIDTH, THEME = _rich()
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
            text = "\n".join(lines) or "(пусто)"
        else:
            text = "(лог пока пуст)"
    except Exception as e:
        text = f"Ошибка чтения: {e}"
    console.print(Align.center(Panel(text, title=" Логи (последние 20) ", width=WIDTH, border_style=THEME["border"])))
    input("\nEnter чтобы вернуться... ")
