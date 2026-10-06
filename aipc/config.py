"""Конфиг AiPC: ~/.aipc/config.yaml с дефолтами."""
from __future__ import annotations

import os
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

SAFETY_VERSION = 3

DEFAULTS = {
    "mode": "ask",  # ask | auto | read-only
    "lang": "en",  # en | ru — язык меню (EN база). Устарело: см. language.
    "language": "en",  # en | ru — канонический ключ языка меню
    "ui": {"theme": "green", "animations": False, "center": False},
    "update": {"auto_check": True},  # фоновая проверка релизов на новом гите
    "server": {"host": "127.0.0.1", "port": 18789},
    "screen": {"max_width": 1280},
    "browser": {"cdp_port": 9222},
    "ssh_hosts": {},
    "web_search": {"provider": "duckduckgo"},
    "installer": {"auto_register": False},  # не трогать IDE-конфиги при каждом запуске меню
    "safety": {
        "deny_cmd": [
            "format ",
            "rm -rf /",
            ":(){:|:&};:",
            "mimikatz",
            "sekurlsa",
            "ntdsutil",
            "vssadmin delete",
            "vssadmin resize",
            "bcdedit",
            "cipher /w",
            "wevtutil cl ",
            "wevtutil clear-log",
            "certutil -decode",
            "certutil -urlcache",
            "bitsadmin /transfer",
            "powershell -e ",
            "powershell -enc ",
            "powershell --encode",
            "powershell /e",
            "pwsh -e",
            "pwsh -enc",
            " -encodedcommand ",
            "frombase64string",
            "invoke-expression",
            "iex ",
            "iex(",
            "get-childitem env:",
            "gci env:",
            "dir env:",
            "[environment]::getenvironmentvariables",
            "reg delete hklm",
            "reg add hklm",
            "rd /s /q c:\\windows",
            "rd /s /q c:/windows",
            "del /f /s /q c:\\windows",
            "takeown /f c:\\windows",
            "icacls c:\\windows",
            "net user ",
            "net localgroup administrators",
            "schtasks /create",
            "sc create",
            "wmic shadowcopy delete",
        ],
        "deny_paths": [
            "**/Cookies/**",
            "**/Login Data**",
            "**/id_rsa",
            "**/id_ed25519",
            "**/*.pem",
            "**/*.pfx",
            "**/*.p12",
            "**/*.kdbx",
            "**/NTUSER.DAT*",
            "**/SAM*",
            "**/SECURITY*",
            # Те же имена без пути — ловят относительные пути (vault.pfx, id_rsa)
            "id_rsa",
            "id_ed25519",
            "*.pem",
            "*.pfx",
            "*.p12",
            "*.kdbx",
            "C:\\Windows\\System32\\*",
            # Хранилища секретов, облачные ключи, окружения, кошельки,
            # профили браузеров (токены сессий), мессенджеры.
            "**/.ssh/**",
            "**/.aws/**",
            "**/.kube/**",
            "**/.gnupg/**",
            "**/.password-store/**",
            "**/.env",
            "**/.env.*",
            "**/wallet.dat",
            "**/*.wallet",
            "**/Local State*",
            "**/Web Data*",
            "**/leveldb/**",
            "**/Local Storage/**",
            "**/Session Storage/**",
            "**/tdata/**",
            ".env",
            ".env.*",
        ],
        "allow_ssh_keys": False,  # true = разрешить чтение id_rsa/*.pem/*.pfx (opt-in)
        # Этап 1.1-1.2: подтверждения и allowlist (только additive-ключи).
        "confirm_timeout": 120,  # секунд ждать человека, потом denied_timeout
        "allow_minutes": 10,  # запасной срок «запомнить» (если пресетов нет)
        "allow_presets": [10, 60],  # вариации времени в окне подтверждения
        "run_cmd_policy": "deny",  # deny | allowlist (см. cmd_allowlist)
        "cmd_allowlist": [],  # префиксы команд для allowlist-режима
        "sensitive_windows_extra": [],  # свои подстроки чувствительных окон
        "taint_guard": True,  # подтверждать опасное после недоверенного ввода даже в auto
        "taint_window": 10,  # ...если untrusted был в последних N вызовах
        "max_calls_per_min": 120,  # лимит скорости вызовов tools
        "loop_repeat": 10,  # один и тот же вызов N раз подряд = loop_guard
        "max_download_mb": 200,  # потолок скачивания (download_file, sftp)
    },
}


def config_dir() -> Path:
    base = os.environ.get("AIPC_HOME") or str(Path.home() / ".aipc")
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    return config_dir() / "config.yaml"


def load_config() -> dict:
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    path = config_path()
    if path.exists() and yaml is not None:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for k, v in data.items():
                if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    cfg[k] = {**cfg[k], **v}
                else:
                    cfg[k] = v
        except Exception:
            pass
    _upgrade_safety(cfg, path)
    return cfg


def _upgrade_safety(cfg: dict, path) -> None:
    """Дотянуть deny-листы старых установок до актуальных (свои добавления не трем)."""
    try:
        safety = cfg.get("safety") or {}
        if safety.get("version") == SAFETY_VERSION:
            return
        def_safety = DEFAULTS["safety"]
        for key in ("deny_cmd", "deny_paths"):
            merged = list(def_safety.get(key, []))
            for item in safety.get(key, []) or []:
                if item not in merged:
                    merged.append(item)
            safety[key] = merged
        safety["version"] = SAFETY_VERSION
        cfg["safety"] = safety
        if yaml is not None:
            try:
                path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
            except Exception:
                pass
    except Exception:
        pass


def save_config(cfg: dict) -> Path:
    path = config_path()
    if yaml is None:
        return path
    path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def ensure_default_config() -> Path:
    path = config_path()
    if not path.exists():
        save_config(load_config())
    return path
