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
    if not js or len(js) > 20000:
        return {"ok": False, "reason": "bad_arg", "error": "пустой/слишком длинный JS"}
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
        return {"ok": True, "tab": {"id": target.get("id"), "title": target.get("title"),
                                    "url": target.get("url")}, "result": res.get("value")}
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
