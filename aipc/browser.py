"""Browser: подключение к уже открытому Chrome/Edge через CDP + история."""
from __future__ import annotations

import json
import urllib.request


def _cdp(port: int, path: str = "/json/list"):
    url = f"http://127.0.0.1:{port}{path}"
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def browser_tabs(port: int = 9222) -> dict:
    try:
        tabs = _cdp(port)
        out = [{"id": t.get("id"), "title": t.get("title"), "url": t.get("url"), "type": t.get("type")} for t in tabs]
        return {"ok": True, "tabs": out}
    except Exception as e:
        return {
            "ok": False,
            "error": f"{e}. Запусти Chrome с --remote-debugging-port={port} (это делает пункт Настроить)",
        }


def browser_goto(url: str, port: int = 9222) -> dict:
    """Открывает URL в уже запущенном браузере (новая вкладка через CDP невозможна без ws — открываем через run)."""
    from .os_ops import run_cmd

    if not url.startswith("http"):
        url = "https://" + url
    # Самый надежный способ для уже открытого Chrome — start с URL
    return run_cmd(f'start "" "{url}"')


def browser_read_hint() -> dict:
    return {
        "ok": True,
        "hint": "Подключи Playwright для полного чтения страниц: pip install playwright && playwright install chromium. "
        "Сейчас доступны tabs + goto + история через файл History (см. browser_history_search в полном Core).",
    }
