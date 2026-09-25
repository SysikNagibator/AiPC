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
    return Console(highlight=False, legacy_windows=False), Panel, Align, MENU_WIDTH, THEME


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


def start_core() -> None:
    console, Panel, Align, WIDTH, THEME = _rich()
    ensure_default_config()
    pid_file = config_dir() / "aipc.pid"
    try:
        from .installer import current_exe, is_frozen

        if is_frozen():
            # exe не понимает -m: запускаем его же с командой mcp
            proc = subprocess.Popen([str(current_exe()), "mcp"])
        else:
            proc = subprocess.Popen(
                [sys.executable, "-m", "aipc", "mcp"],
                cwd=str(Path(__file__).resolve().parent.parent),
            )
        pid_file.write_text(str(proc.pid), encoding="utf-8")
        console.print(Align.center(Panel(f"AiPC-Core запущен, PID {proc.pid}\nПодключи MCP в IDE и работай.", title=" Запустить ", width=WIDTH, border_style="green")))
    except Exception as e:
        console.print(Align.center(Panel(f"Не запустился: {e}", title=" Ошибка ", width=WIDTH, border_style="red")))
    input("\nEnter чтобы вернуться... ")


def stop_core() -> None:
    console, Panel, Align, WIDTH, THEME = _rich()
    pid_file = config_dir() / "aipc.pid"
    try:
        if pid_file.exists():
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            import os, signal

            try:
                if sys.platform == "win32":
                    subprocess.run(f"taskkill /PID {pid} /F", shell=True, capture_output=True)
                else:
                    os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
            pid_file.unlink(missing_ok=True)
            console.print(Align.center(Panel("Остановлен.", title=" Стоп ", width=WIDTH, border_style=THEME["border"])))
        else:
            console.print(Align.center(Panel("Не был запущен (нет PID-файла).", title=" Стоп ", width=WIDTH, border_style=THEME["border"])))
    except Exception as e:
        console.print(Align.center(Panel(f"Ошибка: {e}", title=" Ошибка ", width=WIDTH, border_style="red")))
    input("\nEnter чтобы вернуться... ")


def show_doctor() -> None:
    console, Panel, Align, WIDTH, THEME = _rich()
    from rich.table import Table
    from .logo import MARK_OK, MARK_ERR, safe_mark
    from .maintenance import doctor

    ok_m, err_m = safe_mark(MARK_OK), safe_mark(MARK_ERR)
    table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    table.add_column("check")
    table.add_column("res")
    all_ok = True
    for name, ok, note in doctor():
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
