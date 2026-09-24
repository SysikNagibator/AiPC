"""Политика безопасности: режимы ask/auto/read-only, deny-листы."""
from __future__ import annotations

from fnmatch import fnmatch
from .config import load_config


def check_cmd_allowed(cmd: str) -> tuple[bool, str]:
    cfg = load_config()
    if cfg.get("mode") == "read-only":
        return False, "read-only режим: выполнение команд запрещено"
    deny = cfg.get("safety", {}).get("deny_cmd", [])
    low = cmd.lower()
    for d in deny:
        if d.lower() in low:
            return False, f"запрещенная команда: {d}"
    return True, ""


def check_path_allowed(path: str) -> tuple[bool, str]:
    cfg = load_config()
    deny = cfg.get("safety", {}).get("deny_paths", [])
    for pat in deny:
        try:
            if fnmatch(path, pat) or fnmatch(path.replace("/", "\\"), pat):
                return False, f"запрещенный путь: {pat}"
        except Exception:
            continue
    return True, ""


def is_auto() -> bool:
    return load_config().get("mode") == "auto"
