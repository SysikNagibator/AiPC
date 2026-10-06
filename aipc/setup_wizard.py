"""Мастер настройки: режим, IDE, браузер, SSH, поиск. Без эмодзи."""
from __future__ import annotations

from .config import ensure_default_config, load_config, save_config


def choose_lang() -> None:
    """Язык меню: English (база) или русский. Пишет config key "lang"."""
    from .i18n import t
    from .menu import MenuItem, run_menu

    try:
        from .menu import clear_screen

        clear_screen()
    except Exception:
        pass
    idx = run_menu(t("title.lang"),
                   [MenuItem("English", "en"), MenuItem("Русский", "ru")])
    if idx == "quit":
        return
    lang = ["en", "ru"][idx]
    cfg = load_config()
    cfg["language"] = lang
    cfg.pop("lang", None)  # старый ключ больше не нужен
    save_config(cfg)
    from .menu import show_card, pause

    show_card(t("title.lang"), f'{t("lang.saved")}{lang}', kind="ok")
    pause()


def choose_mode() -> None:
    from .i18n import t
    from .menu import MenuItem, run_menu

    try:
        from .menu import clear_screen

        clear_screen()
    except Exception:
        pass
    idx = run_menu(t("title.mode"),
                   [MenuItem(t("mode.ask"), "ask"),
                    MenuItem(t("mode.auto"), "auto"),
                    MenuItem(t("mode.ro"), "ro")])
    if idx == "quit":
        return
    modes = ["ask", "auto", "read-only"]
    cfg = load_config()
    cfg["mode"] = modes[idx]
    save_config(cfg)
    from .menu import pause, show_card

    show_card(t("title.mode"), f'{t("mode.saved")}{modes[idx]}', kind="ok")
    pause()


def setup_ide() -> None:
    """Сам прописывает aipc в ВЫБРАННЫЕ IDE (только существующие конфиги)."""
    from .i18n import t
    from .installer import configure_all_ides, ide_config_paths
    from .menu import pause, show_card

    try:
        from .menu import clear_screen

        clear_screen()
    except Exception:
        pass
    detected = sorted({n.split("-")[0]
                       for n, p, oi, _w in ide_config_paths()
                       if p.exists() or (oi is not None and oi.exists())})
    if not detected:
        show_card(t("title.idepick"), t("ide.none"), kind="warn")
        pause()
        return
    show_card(t("title.idepick"),
              "\n".join(f"{i + 1}. {n}" for i, n in enumerate(detected)))
    try:
        ans = input(t("ide.pick")).strip().lower()
    except (KeyboardInterrupt, EOFError):
        return
    if not ans:
        return
    if ans in ("all", "все", "a", "в"):
        only = None
    else:
        idxs = set()
        for part in ans.replace(";", ",").split(","):
            part = part.strip()
            if part.isdigit() and 1 <= int(part) <= len(detected):
                idxs.add(int(part) - 1)
        if not idxs:
            return
        only = [detected[i] for i in sorted(idxs)]
    lines = []
    for name, ok, msg in configure_all_ides(only=only):
        mark = "OK" if ok else "X"
        lines.append(f"{mark} {name}: {msg}")
    body = "\n".join(lines) + "\n\n" + t("setup.ide.after")
    show_card(t("setup.ide.title"), body, kind="ok")
    pause()


def setup_browser() -> None:
    from .i18n import t
    from .menu import pause, show_card

    try:
        from .menu import clear_screen

        clear_screen()
    except Exception:
        pass
    show_card(t("setup.browser.title"), t("setup.browser.body"))
    pause()


def setup_ssh() -> None:
    from .i18n import t
    from .menu import pause, show_card

    try:
        from .menu import clear_screen

        clear_screen()
    except Exception:
        pass
    try:
        host = input(t("setup.ssh.host")).strip()
        if not host:
            return
        user = input(t("setup.ssh.user")).strip() or "root"
        key = input(t("setup.ssh.key")).strip() or None
        try:
            port = int((input(t("setup.ssh.port")).strip() or "22"))
        except ValueError:
            port = 22
        port = max(1, min(65535, port))
        cfg = load_config()
        hosts = cfg.get("ssh_hosts") or {}
        hosts[host] = {"user": user, "key_path": key, "port": port}
        cfg["ssh_hosts"] = hosts
        save_config(cfg)
        show_card(t("setup.ssh"), t("setup.ssh.saved").format(
            user=user, host=host, port=port), kind="ok")
    except (KeyboardInterrupt, EOFError):
        return
    pause()


def choose_theme() -> None:
    """Тема меню: green/mono/amber. Пишет config key ui.theme."""
    from .i18n import t
    from .menu import MenuItem, run_menu

    try:
        from .menu import clear_screen

        clear_screen()
    except Exception:
        pass
    names = ["green", "mono", "amber"]
    labels = [t("theme.green"), t("theme.mono"), t("theme.amber")]
    idx = run_menu(t("title.theme"),
                   [MenuItem(labels[i], names[i]) for i in range(3)],
                   show_title=True)
    if idx == "quit":
        return
    cfg = load_config()
    ui = cfg.get("ui") or {}
    if not isinstance(ui, dict):
        ui = {}
    ui["theme"] = names[idx]
    cfg["ui"] = ui
    save_config(cfg)
    from .menu import pause, show_card

    show_card(t("title.theme"), names[idx], kind="ok")
    pause()


def setup_menu() -> None:
    from .menu import MenuItem, run_menu
    from .i18n import t

    ensure_default_config()
    while True:
        idx = run_menu(
            t("title.setup"),
            [
                MenuItem(t("setup.mode"), "mode", t("setup.mode.hint")),
                MenuItem(t("setup.ide"), "ide", t("setup.ide.hint")),
                MenuItem(t("setup.browser"), "browser", t("setup.browser.hint")),
                MenuItem(t("setup.ssh"), "ssh", t("setup.ssh.hint")),
                MenuItem(t("setup.lang"), "lang", t("setup.lang.hint")),
                MenuItem(t("setup.theme"), "theme", t("setup.theme.hint")),
                MenuItem(t("setup.back"), "back", t("setup.back.hint")),
            ],
        )
        if idx == "quit" or idx == 6:
            return
        if idx == 0:
            choose_mode()
        elif idx == 1:
            setup_ide()
        elif idx == 2:
            setup_browser()
        elif idx == 3:
            setup_ssh()
        elif idx == 4:
            choose_lang()
        elif idx == 5:
            choose_theme()
