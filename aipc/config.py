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
    "server": {"host": "127.0.0.1", "port": 18789},
    "screen": {"max_width": 1280},
    "browser": {"cdp_port": 9222},
    "ssh_hosts": {},
    "web_search": {"provider": "duckduckgo"},
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
            " -encodedcommand ",
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
        ],
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
