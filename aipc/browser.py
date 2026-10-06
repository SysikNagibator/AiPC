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
            "ok": False, "reason": "error",
            "error": f"{e}. Запусти Chrome с --remote-debugging-port={port} (это делает пункт Настроить)",
        }


def browser_goto(url: str, port: int = 9222) -> dict:
    """Открыть URL в браузере пользователя. Кавычки/метасимволы режем (инъекция невозможна)."""
    from .os_ops import run_cmd

    url = "".join(c for c in str(url) if c not in '"`$;&|<>^%\n\r')
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    if not url or len(url) > 2000:
        return {"ok": False, "reason": "bad_arg", "error": "битый URL"}
    # Самый надежный способ для уже открытого Chrome — start с URL
    return run_cmd(f'start "" "{url}"')


def _ws_eval(ws_url: str, js: str, timeout: int = 20) -> dict:
    import json as _json

    import websocket  # type: ignore

    ws = websocket.create_connection(ws_url, timeout=timeout)
    try:
        ws.send(_json.dumps({"id": 1, "method": "Runtime.evaluate",
                             "params": {"expression": js, "returnByValue": True, "awaitPromise": True}}))
        import time as _time

        deadline = _time.monotonic() + timeout
        while True:
            msg = _json.loads(ws.recv())
            if msg.get("id") == 1:
                res = msg.get("result", {}).get("result", {})
                if res.get("type") == "string":
                    return {"value": res.get("value")}
                if "value" in res:
                    return {"value": res["value"]}
                if res.get("subtype") == "error" or msg.get("result", {}).get("exceptionDetails"):
                    desc = res.get("description", "js error")
                    return {"js_error": desc[:1000]}
                return {"value": res.get("description", str(res))[:5000]}
            if _time.monotonic() > deadline:
                return {"timeout": True}
    finally:
        try:
            ws.close()
        except Exception:
            pass


def browser_eval(js: str, tab_id: str = "", port: int = 9222, timeout: int = 20) -> dict:
    """Выполнить JS в активной (или указанной) вкладке. Надёжнее кликов: читать DOM, кликать селекторы."""
    if not js:
        return {"ok": False, "reason": "bad_arg", "error": "пустой JS"}
    try:
        import websocket  # type: ignore  # noqa
    except ImportError:
        return {"ok": False, "reason": "missing_dep", "error": "pip install websocket-client"}
    try:
        tabs = [t for t in _cdp(port) if t.get("type") == "page"]
        if not tabs:
            return {"ok": False, "reason": "not_found", "error": "нет открытых вкладок"}
        target = next((t for t in tabs if tab_id and t.get("id") == tab_id), None)
        if target is None:
            active = browser_active_tab(port)
            aid = (active.get("tab") or {}).get("id") if active.get("ok") else None
            target = next((t for t in tabs if t.get("id") == aid), tabs[0])
        res = _ws_eval(target["webSocketDebuggerUrl"], js, timeout)
        if res.get("timeout"):
            return {"ok": False, "reason": "timeout", "error": "CDP не ответил"}
        if "js_error" in res:
            return {"ok": False, "reason": "js_error", "error": res["js_error"]}
        val = res.get("value")
        if isinstance(val, str) and len(val) > 20000:
            val = val[:20000] + f"...[обрезано, было {len(val)}]"
        return {"ok": True, "tab": {"id": target.get("id"), "title": target.get("title"),
                                    "url": target.get("url")}, "result": val}
    except Exception as e:
        return {"ok": False, "reason": "error",
                "error": f"{e}. Chrome нужен с --remote-debugging-port={port}"}


def browser_active_tab(port: int = 9222) -> dict:
    """Активная вкладка: сопоставляем заголовок активного окна Chrome со списком вкладок."""
    try:
        tabs = [t for t in _cdp(port) if t.get("type") == "page"]
    except Exception as e:
        return {"ok": False, "reason": "error",
                "error": f"{e}. Запусти Chrome с --remote-debugging-port={port}"}
    if not tabs:
        return {"ok": False, "reason": "not_found", "error": "нет открытых вкладок"}
    try:
        from .vision import get_active_window

        title = (get_active_window().get("title") or "")
        core = title.rsplit(" - Google Chrome", 1)[0].rsplit(" - ", 1)[-1].strip().lower()
        for t in tabs:
            if core and core in str(t.get("title") or "").lower():
                return {"ok": True, "tab": {"id": t.get("id"), "title": t.get("title"), "url": t.get("url")}}
    except Exception:
        pass
    t = tabs[0]
    return {"ok": True, "tab": {"id": t.get("id"), "title": t.get("title"), "url": t.get("url")},
            "note": "точно активную не определил, взял первую"}


def browser_close_tab(tab_id: str, port: int = 9222) -> dict:
    """Закрыть вкладку по id (см. browser_tabs)."""
    if not tab_id:
        return {"ok": False, "reason": "bad_arg", "error": "нужен tab_id из browser_tabs"}
    try:
        import urllib.request as _url

        last = None
        for method in ("PUT", "GET"):
            try:
                req = _url.Request(f"http://127.0.0.1:{port}/json/close/{tab_id}", method=method)
                with _url.urlopen(req, timeout=5) as r:
                    if r.status == 200:
                        return {"ok": True, "closed": tab_id}
            except Exception as e:
                last = e
        return {"ok": False, "reason": "not_found", "error": f"вкладка не закрыта: {tab_id} ({last})"}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def _history_files() -> list:
    """Пути к History Chrome/Edge (первый существующий приоритетнее)."""
    import os
    from pathlib import Path

    local = Path(os.environ.get("LOCALAPPDATA", ""))
    cands = [
        local / "Google" / "Chrome" / "User Data" / "Default" / "History",
        local / "Microsoft" / "Edge" / "User Data" / "Default" / "History",
        local / "Chromium" / "User Data" / "Default" / "History",
    ]
    return [p for p in cands if p.exists()]


def _chrome_time(micros: int) -> str:
    """Время Chrome (мкс с 1601-01-01) -> ISO."""
    try:
        import datetime as _dt

        base = _dt.datetime(1601, 1, 1)
        return (base + _dt.timedelta(microseconds=int(micros or 0))).isoformat(timespec="seconds")
    except Exception:
        return ""


def browser_history_search(query: str, limit: int = 10) -> dict:
    """Поиск по истории Chrome/Edge («та вкладка что открывал вчера»). Файл копируем — браузер не трогаем."""
    import shutil
    import sqlite3
    import tempfile
    from pathlib import Path

    files = _history_files()
    if not files:
        return {"ok": False, "reason": "not_found", "error": "History Chrome/Edge не найден"}
    out: list[dict] = []
    like = f"%{query}%"
    for src in files[:2]:
        tmp = Path(tempfile.gettempdir()) / f"aipc_hist_{src.parent.parent.name}.db"
        try:
            shutil.copy2(src, tmp)
            con = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
            try:
                rows = con.execute(
                    "SELECT url, title, last_visit_time FROM urls "
                    "WHERE url LIKE ? OR title LIKE ? ORDER BY last_visit_time DESC LIMIT ?",
                    (like, like, max(1, limit)),
                ).fetchall()
            finally:
                con.close()
            for url, title, ts in rows:
                out.append({"url": url, "title": title, "visited": _chrome_time(ts),
                            "browser": src.parent.parent.name})
                if len(out) >= max(1, limit):
                    break
        except Exception:
            continue
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
        if len(out) >= max(1, limit):
            break
    return {"ok": True, "found": out, "count": len(out)}
