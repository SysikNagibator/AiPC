"""Конфиг AiPC: ~/.aipc/config.yaml с дефолтами."""
from __future__ import annotations

import os
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

DEFAULTS = {
    "mode": "ask",  # ask | auto | read-only
    "server": {"host": "127.0.0.1", "port": 18789},
    "screen": {"max_width": 1280},
    "browser": {"cdp_port": 9222},
    "ssh_hosts": {},
    "web_search": {"provider": "duckduckgo"},
    "safety": {
        "deny_cmd": ["format ", "rm -rf /", ":(){:|:&};:"],
        "deny_paths": ["**/Cookies/**", "**/Login Data**", "C:\\Windows\\System32\\*"],
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
    return cfg


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
