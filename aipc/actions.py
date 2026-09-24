"""Действия пунктов меню (без эмодзи)."""
from __future__ import annotations

import subprocess
import sys
import time
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
    lines = [
        f"Режим: {cfg.get('mode')}",
        f"Конфиг: {config_dir() / 'config.yaml'}",
        f"Версия tools: 1.0.0",
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
    # Запуск MCP в фоне: python -m aipc mcp
    try:
        proc = subprocess.Popen([sys.executable, "-m", "aipc", "mcp"], cwd=str(Path(__file__).resolve().parent.parent))
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


def show_logs() -> None:
    console, Panel, Align, WIDTH, THEME = _rich()
    p = config_dir() / "audit.log"
    text = ""
    try:
        if p.exists():
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]
            text = "\n".join(lines) or "(пусто)"
        else:
            text = "(лог пока пуст)"
    except Exception as e:
        text = f"Ошибка чтения: {e}"
    console.print(Align.center(Panel(text, title=" Логи (последние 20) ", width=WIDTH, border_style=THEME["border"])))
    input("\nEnter чтобы вернуться... ")
