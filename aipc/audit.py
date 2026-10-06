"""Аудит каждого вызова tool. С ротацией чтобы лог не рос бесконечно."""
from __future__ import annotations

import re
from .config import config_dir

MAX_LOG_BYTES = 2 * 1024 * 1024

# Паттерны секретов для маскирования в логах и ответах (этап 1.4).
# Узкие (известные префиксы), чтобы не портить обычные тексты.
_MASK_RULES = [
    # Приватные ключи целиком, включая тело.
    (re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"
                r"[\s\S]*?-----END (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
     "[PRIVATE KEY REDACTED]"),
    (re.compile(r"\b(ghp_|gho_|github_pat_)[A-Za-z0-9_]+"), r"\1***"),
    (re.compile(r"\bsk-(?:ant|proj)-[A-Za-z0-9\-_]+"), "sk-***"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AKIA***"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]+\b"), "xox***"),
    # Пароль в URL: https://user:PASS@host
    (re.compile(r"(https?://)([^:/\s]+):([^@\s]+)@"), r"\1\2:***@"),
    # password=..., "secret": "..." — маскируем значение.
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|auth[_-]?token)\b"
                r"\s*[:=]\s*['\"]?([^\s'\",}\]]+)"), r"\1=***"),
]


def mask_secrets(text: str) -> str:
    """Заменить секреты в тексте на *** (для логов и ответов модели)."""
    try:
        out = str(text)
        for rx, repl in _MASK_RULES:
            out = rx.sub(repl, out)
        return out
    except Exception:
        return str(text)[:500]


def _rotate(p) -> None:
    try:
        if p.exists() and p.stat().st_size > MAX_LOG_BYTES:
            bak = p.with_suffix(".log.bak")
            if bak.exists():
                bak.unlink()
            p.rename(bak)
    except Exception:
        pass


def tail_log(n: int = 20, max_bytes: int = 65536) -> list[str]:
    """Хвост audit.log для отладки агента (сырые строки)."""
    try:
        p = config_dir() / "audit.log"
        if not p.exists():
            return []
        with p.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            tail = f.read().decode("utf-8", errors="replace")
        return tail.splitlines()[-max(1, n):]
    except Exception:
        return []


def tail_events(n: int = 50, since: str = "", tool: str = "") -> list[dict]:
    """Разобранные события (JSON-lines; старые текстовые строки пропускаем)."""
    import json

    out: list[dict] = []
    for line in tail_log(max(1, n * 3), 256 * 1024):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if not isinstance(ev, dict) or "tool" not in ev:
            continue
        if tool and ev.get("tool") != tool:
            continue
        if since and str(ev.get("ts", "")) < since:
            continue
        out.append(ev)
    return out[-max(1, n):]


def log_event(tool: str, params: dict, ok: bool = True, note: str = "",
              mode: str = "", decision: str = "") -> None:
    """Структурированный JSON-lines: ts, tool, args (замаскированные),
    mode, decision, ok, note."""
    import json

    try:
        from .policy import load_mode

        cur_mode = mode or load_mode()
    except Exception:
        cur_mode = mode or "ask"
    try:
        p = config_dir() / "audit.log"
        _rotate(p)
        import datetime as _dt

        ev = {
            "ts": _dt.datetime.now().isoformat(timespec="seconds"),
            "tool": tool,
            "args": mask_secrets(params if isinstance(params, dict) else {"v": params}),
            "mode": cur_mode,
            "decision": decision,
            "ok": bool(ok),
            "note": mask_secrets(note),
        }
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except Exception:
        pass
