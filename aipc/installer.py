"""Installer: самоустановка exe в Program Files + PATH + MCP во все IDE.

Логика: exe при первом запуске сам копирует себя в Program Files.
Если нет прав админа — сам просит UAC (runas) и продолжает работу.
Настройка MCP для IDE прав админа не требует — делается всегда.
"""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import sys
import time
from pathlib import Path


def is_admin() -> bool:
    try:
        if os.name == "nt":
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def current_exe() -> Path:
    if is_frozen():
        return Path(sys.executable)
    return Path(sys.argv[0]).resolve()


def install_dir() -> str:
    return r"C:\Program Files\AiPC"


def installed_exe() -> Path:
    return Path(install_dir()) / "aipc.exe"


def is_installed() -> bool:
    """Exe уже лежит в Program Files (с учетом регистра и симлинков)?"""
    if not is_frozen():
        return False
    try:
        cur = current_exe().resolve()
        target = installed_exe().resolve()
    except Exception:
        return False
    try:
        return cur == target and target.exists()
    except Exception:
        return False


def relaunch_as_admin(args: str = "") -> None:
    """Перезапустить себя от админа (Windows UAC) и завершить текущий процесс."""
    if os.name != "nt":
        print("Запусти с sudo.")
        sys.exit(1)
    if not is_frozen():
        # dev-режим: python -m aipc ...
        script = f"-m aipc {args}".strip()
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, script, str(Path.cwd()), 1)
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", str(current_exe()), args, None, 1)
    sys.exit(0)


def add_to_system_path(path: str) -> tuple[bool, str]:
    """Добавить в системный PATH (HKLM). Требует админа."""
    if os.name != "nt":
        return False, "только Windows"
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE)
        try:
            cur, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            cur = ""
        if path.lower() in cur.lower():
            winreg.CloseKey(key)
            return True, "уже в PATH"
        new = cur.rstrip(";") + ";" + path
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new)
        winreg.CloseKey(key)
        # разослать WM_SETTINGCHANGE чтобы новый cmd увидел сразу
        try:
            HWND_BROADCAST, WM_SETTINGCHANGE = 0xFFFF, 0x1A
            ctypes.windll.user32.SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", 0, 5000, None)
        except Exception:
            pass
        return True, f"добавлено: {path}"
    except PermissionError:
        return False, "нужны права админа — перезапусти Setup от админа"
    except Exception as e:
        return False, str(e)


def install_self_to_program_files() -> tuple[bool, str]:
    """Копирует aipc.exe в Program Files. Требует админа на запись."""
    dst = Path(install_dir())
    try:
        dst.mkdir(parents=True, exist_ok=True)
        if is_frozen():
            src = current_exe()
            target = dst / "aipc.exe"
            # Не копировать самого себя
            try:
                if src.resolve() == target.resolve() and target.exists():
                    return True, f"уже на месте: {target}"
            except Exception:
                pass
            shutil.copy2(src, target)
            # Рядом кладем пресеты чтобы menu их находило и в frozen-режиме
            try:
                (dst / "mcp_presets").mkdir(exist_ok=True)
            except Exception:
                pass
            return True, f"скопировано {src} -> {target}"
        return True, f"папка готова: {dst} (dev-режим: добавь проект в PATH вручную или собери exe)"
    except PermissionError:
        return False, "нужны права админа"
    except Exception as e:
        return False, str(e)


# --- MCP: пути конфигов IDE на Windows ---
# only_if: писать сюда только если этот путь уже существует (не плодим мусор чужим IDE).

def _home() -> Path:
    return Path(os.path.expanduser("~"))


def ide_config_paths() -> list[tuple[str, Path, Path | None]]:
    """(имя IDE, путь к конфигу, only_if). Пишем только mcpServers.aipc, остальное не трогаем."""
    home = _home()
    appdata = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
    main_antigravity = home / ".gemini" / "config" / "mcp_config.json"
    main_cursor = home / ".cursor" / "mcp.json"
    main_vscode = appdata / "Code" / "User" / "mcp_settings.json"
    gemini_settings = home / ".gemini" / "settings.json"
    claude_code_state = home / ".claude.json"
    roo_dir = appdata / "Code" / "User" / "globalStorage" / "rooveterinaryinc.roo-cline"
    return [
        ("Antigravity", main_antigravity, None),
        ("Antigravity-alt", home / ".gemini" / "antigravity" / "mcp_config.json", main_antigravity),
        ("Cursor", main_cursor, None),
        ("Cursor-alt", appdata / "Cursor" / "User" / "mcp.json", main_cursor),
        ("VSCode-Cline", main_vscode, None),
        ("VSCode-Roo", roo_dir / "settings" / "mcp_settings.json", roo_dir),
        ("GeminiCLI", gemini_settings, gemini_settings),
        ("ClaudeCode", claude_code_state, claude_code_state),
        ("ClaudeDesktop", appdata / "Claude" / "claude_desktop_config.json", None),
    ]


def mcp_server_entry() -> tuple[str, list[str]]:
    """Правильная пара (command, args) для MCP-конфигов.

    ВАЖНО: command — только путь к исполняемому файлу, без аргументов одной строкой,
    иначе MCP-клиенты (Cursor/VS Code/Claude) не смогут запустить сервер.
    """
    if is_frozen():
        exe = str(installed_exe() if is_installed() else current_exe())
        return exe, ["mcp"]
    return sys.executable, ["-m", "aipc", "mcp"]


def merge_mcp_file(path: Path, command: str, args: list[str]) -> tuple[bool, str]:
    """Аккуратно дописать aipc в mcpServers. Бэкап .bak. Возвращает (ok, msg)."""
    entry = {"command": command, "args": args}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if path.exists():
            try:
                bak = path.with_suffix(path.suffix + ".bak")
                if not bak.exists():
                    shutil.copy2(path, bak)
                data = json.loads(path.read_text(encoding="utf-8") or "{}")
            except Exception:
                data = {}
        servers = data.get("mcpServers")
        if not isinstance(servers, dict):
            servers = {}
            data["mcpServers"] = servers
        if servers.get("aipc") == entry:
            return True, f"{path}: уже настроено"
        servers["aipc"] = entry
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True, f"{path}: прописано"
    except Exception as e:
        return False, f"{path}: {e}"


def configure_all_ides(command: str | None = None, args: list[str] | None = None) -> list[tuple[str, bool, str]]:
    """Прописать aipc во все известные IDE. Прав админа не надо. Возвращает отчет."""
    if command is None or args is None:
        command, args = mcp_server_entry()
    report: list[tuple[str, bool, str]] = []
    for name, path, only_if in ide_config_paths():
        try:
            if only_if is not None and not only_if.exists():
                continue
            ok, msg = merge_mcp_file(path, command, args)
            report.append((name, ok, msg))
        except Exception as e:
            report.append((name, False, str(e)))
    return report


def privileged_self_install() -> int:
    """Шаг с правами админа: копия в Program Files + PATH. Вызывается как `aipc --self-install`."""
    print("=== AiPC: установка (админ) ===")
    ok1, msg1 = install_self_to_program_files()
    print(f"[1/2] {msg1}")
    ok2, msg2 = add_to_system_path(install_dir())
    print(f"[2/2] {msg2}")
    for name, ok, msg in configure_all_ides(str(installed_exe())):
        print(f"[mcp] {name}: {msg}")
    return 0 if (ok1 and ok2) else 1


def ensure_installed() -> str:
    """Гарантировать что exe в Program Files + MCP настроен. Возвращает путь к exe для работы.

    - dev-режим (python): ничего не копирует, только MCP на текущий python-модуль.
    - frozen вне Program Files: просит UAC (один раз), ждет конца установки,
      затем перезапускается из Program Files.
    - frozen в Program Files: просто обновляет MCP и работает.
    """
    if not is_frozen():
        configure_all_ides()
        return str(current_exe())

    if is_installed():
        configure_all_ides(*mcp_server_entry())
        return str(installed_exe())

    # Первый запуск не из Program Files
    if not is_admin():
        print("Первый запуск: кладу себя в Program Files и настраиваю MCP.")
        print("Сейчас попрошу права админа один раз...")
        time.sleep(1)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", str(current_exe()), "--self-install", None, 1)
        # Ждем пока админ-процесс закончит (макс 3 мин)
        for _ in range(180):
            time.sleep(1)
            if installed_exe().exists():
                break
        # Перезапуск из установленного места, дальше — меню
        try:
            import subprocess

            subprocess.Popen([str(installed_exe())])
        except Exception:
            pass
        sys.exit(0)

    # Уже админ, но лежим не там — ставим молча
    code = privileged_self_install()
    if code == 0:
        try:
            import subprocess

            subprocess.Popen([str(installed_exe())])
        except Exception:
            pass
        sys.exit(0)
    return str(current_exe())
