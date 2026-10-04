"""Мастер настройки: режим, IDE, браузер, SSH, поиск. Без эмодзи."""
from __future__ import annotations

from .config import ensure_default_config, load_config, save_config


def _pause():
    input("\nEnter чтобы вернуться... ")


def choose_mode() -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.align import Align
    from .logo import MENU_WIDTH, THEME
    from .menu import MenuItem, run_menu

    console = Console(highlight=False, legacy_windows=False)
    idx = run_menu("Режим работы", [MenuItem("ask — спрашивать (по умолчанию)", "ask"), MenuItem("auto — полная автономность", "auto"), MenuItem("read-only — только смотреть", "ro")])
    if idx == "quit":
        return
    modes = ["ask", "auto", "read-only"]
    cfg = load_config()
    cfg["mode"] = modes[idx]
    save_config(cfg)
    console.print(Align.center(Panel(f"Режим: {modes[idx]}", width=MENU_WIDTH, border_style="green")))
    _pause()


def setup_ide() -> None:
    """Сам прописывает aipc во все найденные IDE (Antigravity/Cursor/VSCode/Claude)."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.align import Align
    from .logo import MENU_WIDTH, THEME
    from .installer import configure_all_ides

    console = Console(highlight=False, legacy_windows=False)
    lines = []
    for name, ok, msg in configure_all_ides():
        mark = "OK" if ok else "X"
        lines.append(f"{mark} {name}: {msg}")
    body = "\n".join(lines) + "\n\nПосле — Refresh MCP / перезапуск IDE."
    console.print(Align.center(Panel(body, title=" Подключить IDE ", width=MENU_WIDTH, border_style=THEME["border"])))
    _pause()


def setup_browser() -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.align import Align
    from .logo import MENU_WIDTH, THEME

    console = Console(highlight=False, legacy_windows=False)
    body = (
        "Чтобы модель видела ТВОЙ браузер, а не пустой:\n\n"
        '1. Закрой Chrome\n'
        '2. В свойствах ярлыка допиши:\n'
        "   --remote-debugging-port=9222\n"
        "3. Открой Chrome снова\n\n"
        "Проверка: пункт Статус/Проверка -> browser_tabs должен показать вкладки."
    )
    console.print(Align.center(Panel(body, title=" Браузер ", width=MENU_WIDTH, border_style=THEME["border"])))
    _pause()


def setup_ssh() -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.align import Align
    from .logo import MENU_WIDTH, THEME

    console = Console(highlight=False, legacy_windows=False)
    try:
        host = input("host (напр. 192.168.1.10) [пусто=назад]> ").strip()
        if not host:
            return
        user = input("user> ").strip() or "root"
        key = input("key_path (пусто=ssh-agent)> ").strip() or None
        cfg = load_config()
        hosts = cfg.get("ssh_hosts") or {}
        hosts[host] = {"user": user, "key_path": key, "port": 22}
        cfg["ssh_hosts"] = hosts
        save_config(cfg)
        console.print(Align.center(Panel(f"Сохранено: {user}@{host}", width=MENU_WIDTH, border_style="green")))
    except (KeyboardInterrupt, EOFError):
        return
    _pause()


def setup_menu() -> None:
    from .menu import MenuItem, run_menu

    ensure_default_config()
    while True:
        idx = run_menu(
            "Настроить",
            [
                MenuItem("Режим ask/auto/read-only", "mode"),
                MenuItem("Подключить IDE (MCP-пресет)", "ide"),
                MenuItem("Подключить браузер (CDP)", "browser"),
                MenuItem("SSH-хосты", "ssh"),
                MenuItem("Назад", "back"),
            ],
        )
        if idx == "quit" or idx == 4:
            return
        if idx == 0:
            choose_mode()
        elif idx == 1:
            setup_ide()
        elif idx == 2:
            setup_browser()
        elif idx == 3:
            setup_ssh()
