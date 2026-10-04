"""Политика безопасности: режимы ask/auto/read-only, deny-листы."""
from __future__ import annotations

from fnmatch import fnmatch
from .config import load_config


def check_cmd_allowed(cmd: str) -> tuple[bool, str]:
    cfg = load_config()
    if cfg.get("mode") == "read-only":
        return False, "read-only режим: выполнение команд запрещено"
    deny = cfg.get("safety", {}).get("deny_cmd", [])
    # Нормализация: схлопываем ^ $ ` и лишние пробелы — ловля простых обходов
    low = cmd.lower()
    for ch in ("^", "`"):
        low = low.replace(ch, "")
    low = " ".join(low.split())
    for d in deny:
        if str(d).lower() in low:
            return False, f"запрещенная команда: {d}"
    return True, ""


def check_path_allowed(path: str) -> tuple[bool, str]:
    import os

    cfg = load_config()
    deny = cfg.get("safety", {}).get("deny_paths", [])
    expanded = os.path.expanduser(path)
    norm = os.path.normcase(expanded).replace("/", "\\")
    base = os.path.normcase(os.path.basename(expanded))
    for pat in deny:
        try:
            pnorm = os.path.normcase(str(pat)).replace("/", "\\")
            if fnmatch(norm, pnorm):
                return False, f"запрещенный путь: {pat}"
            # Паттерны-имени (без сепаратора: *.pfx, id_rsa) сверяем с basename,
            # чтобы ловить и относительные пути. Паттерны-пути — только целиком:
            # иначе basename '*' из '...\*' заблокировал бы вообще всё.
            if "\\" not in pnorm and fnmatch(base, pnorm):
                return False, f"запрещенный путь: {pat}"
        except Exception:
            continue
    return True, ""


def is_auto() -> bool:
    return load_config().get("mode") == "auto"
