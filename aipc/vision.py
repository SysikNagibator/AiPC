"""Vision: скриншоты, окна, UI-дерево. Опциональные зависимости, graceful fallback."""
from __future__ import annotations


def _encode(img, monitor: int):
    import base64
    import io

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"ok": True, "image_b64": b64, "width": img.width, "height": img.height, "monitor": monitor}


def _draw_cursor(img, full_w: int, full_h: int) -> None:
    """Красный кружок там где курсор (на скриншоте его иначе не видно)."""
    try:
        import pyautogui  # type: ignore
        from PIL import ImageDraw  # type: ignore

        mx, my = pyautogui.position()
        sx, sy = img.width / full_w, img.height / full_h
        cx, cy = int(mx * sx), int(my * sy)
        r = max(8, img.width // 100)
        d = ImageDraw.Draw(img)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 40, 40), width=max(2, r // 4))
    except Exception:
        pass


def screen_see(monitor: int = 0, max_width: int = 1280, cursor: bool = True) -> dict:
    """Скриншот монитора -> base64 JPEG + размер. Глаза модели."""
    try:
        import mss  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError as e:
        return {"ok": False, "error": f"нет зависимостей экрана: {e}. pip install mss pillow"}

    try:
        with mss.mss() as sct:
            mons = sct.monitors
            idx = monitor + 1 if (monitor + 1) < len(mons) else 1
            shot = sct.grab(mons[idx])
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            full_w, full_h = img.width, img.height
            if img.width > max_width:
                h = int(img.height * max_width / img.width)
                img = img.resize((max_width, h))
            if cursor:
                _draw_cursor(img, full_w, full_h)
            return _encode(img, monitor)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def screen_region(x: int, y: int, w: int, h: int, monitor: int = 0, max_width: int = 800) -> dict:
    """Крупный план области: x,y левый верх + w,h размер, всё 0-1000 относительных."""
    try:
        import mss  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError as e:
        return {"ok": False, "error": f"нет зависимостей экрана: {e}. pip install mss pillow"}

    def clamp(v: int) -> int:
        return max(0, min(1000, v))

    x, y, w, h = clamp(x), clamp(y), max(10, w), max(10, h)
    try:
        with mss.mss() as sct:
            mons = sct.monitors
            idx = monitor + 1 if (monitor + 1) < len(mons) else 1
            mon = mons[idx]
            mw, mh = mon["width"], mon["height"]
            left = mon["left"] + int(x / 1000 * mw)
            top = mon["top"] + int(y / 1000 * mh)
            width = min(int(w / 1000 * mw), mw - (left - mon["left"]))
            height = min(int(h / 1000 * mh), mh - (top - mon["top"]))
            shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            if img.width > max_width:
                img = img.resize((max_width, int(img.height * max_width / img.width)))
            res = _encode(img, monitor)
            res["region"] = {"x": x, "y": y, "w": w, "h": h}
            return res
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_active_window() -> dict:
    """Активное окно: заголовок + прямоугольник + maximized."""
    try:
        import pygetwindow as gw  # type: ignore
    except ImportError:
        return {"ok": False, "error": "нет pygetwindow. pip install pygetwindow"}
    try:
        w = gw.getActiveWindow()
        if not w:
            return {"ok": False, "error": "нет активного окна"}
        return {"ok": True, "title": w.title, "rect": [w.left, w.top, w.width, w.height],
                "is_maximized": bool(w.isMaximized)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def window_manage(title_substr: str, action: str = "minimize") -> dict:
    """Окно: minimize/maximize/restore/close по подстроке заголовка."""
    valid = ("minimize", "maximize", "restore", "close")
    if action not in valid:
        return {"ok": False, "error": f"action только {valid}"}
    try:
        import pygetwindow as gw  # type: ignore
    except ImportError:
        return {"ok": False, "error": "нет pygetwindow. pip install pygetwindow"}
    try:
        for w in gw.getAllWindows():
            if title_substr.lower() in (w.title or "").lower():
                try:
                    getattr(w, action)()
                except Exception:
                    if action == "close":
                        try:
                            w.close()
                        except Exception as e:
                            return {"ok": False, "error": str(e)}
                    else:
                        raise
                return {"ok": True, "title": w.title, "action": action}
        return {"ok": False, "error": f"окно не найдено: {title_substr}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def ui_snapshot(max_nodes: int = 200, monitor: int = 0, role: str = "", name_contains: str = "") -> dict:
    """Дерево UI-элементов с центрами cx/cy в 0-1000. Фильтры role/name режут токены."""
    nodes, err = _collect_ui(monitor, role, name_contains, max(10, min(1000, max_nodes)))
    if err and not nodes:
        return {"ok": False, "reason": "missing_dep" if "uiautomation" in err else "error", "error": err}
    return {"ok": True, "nodes": nodes, "count": len(nodes)}


def windows_list(limit: int = 50) -> dict:
    try:
        import pygetwindow as gw  # type: ignore
    except ImportError:
        return {"ok": False, "error": "нет pygetwindow. pip install pygetwindow"}
    try:
        out = []
        for w in gw.getAllWindows()[:limit]:
            try:
                out.append({"title": w.title, "is_active": w.isActive, "size": [w.width, w.height]})
            except Exception:
                continue
        return {"ok": True, "windows": out}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def window_focus(title_substr: str) -> dict:
    try:
        import pygetwindow as gw  # type: ignore
    except ImportError:
        return {"ok": False, "error": "нет pygetwindow"}
    try:
        for w in gw.getAllWindows():
            if title_substr.lower() in (w.title or "").lower():
                try:
                    w.activate()
                except Exception:
                    try:
                        w.minimize()
                        w.restore()
                    except Exception:
                        pass
                return {"ok": True, "title": w.title}
        return {"ok": False, "reason": "not_found", "error": f"окно не найдено: {title_substr}"}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def _monitor_rect(monitor: int = 0) -> dict:
    import mss  # type: ignore

    with mss.mss() as sct:
        mons = sct.monitors
        idx = monitor + 1 if (monitor + 1) < len(mons) else 1
        return mons[idx]


def _grab_region(monitor: int, x: int, y: int, w: int, h: int):
    """Захват области 0-1000 -> PIL.Image. Бросает исключения наверх."""
    import mss  # type: ignore
    from PIL import Image  # type: ignore

    def clamp(v: int) -> int:
        return max(0, min(1000, v))

    x, y = clamp(x), clamp(y)
    mon = _monitor_rect(monitor)
    mw, mh = mon["width"], mon["height"]
    left = mon["left"] + int(x / 1000 * mw)
    top = mon["top"] + int(y / 1000 * mh)
    width = max(2, min(int(max(10, w) / 1000 * mw), mw - (left - mon["left"])))
    height = max(2, min(int(max(10, h) / 1000 * mh), mh - (top - mon["top"])))
    with mss.mss() as sct:
        shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
    return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def _poll(timeout: float, interval: float, fn):
    import time as _time

    deadline = _time.monotonic() + max(1.0, timeout)
    while True:
        hit = fn()
        if hit:
            return hit
        if _time.monotonic() >= deadline:
            return None
        _time.sleep(min(interval, max(0.1, deadline - _time.monotonic())))


def _collect_ui(monitor: int = 0, role: str = "", name_contains: str = "", max_nodes: int = 200) -> tuple[list, str]:
    """Общий сборщик UI-дерева. Возвращает (nodes, error)."""
    try:
        import uiautomation as auto  # type: ignore
    except ImportError:
        return [], "нет uiautomation. pip install uiautomation (только Windows)"
    try:
        mon = _monitor_rect(monitor)
    except Exception as e:
        return [], str(e)
    mw, mh, ml, mt = mon["width"], mon["height"], mon["left"], mon["top"]
    role, name_contains = role.lower(), name_contains.lower()
    nodes: list[dict] = []

    def walk(control, depth: int) -> None:
        if len(nodes) >= max_nodes or depth > 6:
            return
        try:
            children = control.GetChildren()
        except Exception:
            return
        for c in children:
            if len(nodes) >= max_nodes:
                return
            try:
                rect = c.BoundingRectangle
                cx = int((rect.left + rect.right) / 2 - ml) / mw * 1000
                cy = int((rect.top + rect.bottom) / 2 - mt) / mh * 1000
                if not (0 <= cx <= 1000 and 0 <= cy <= 1000 and rect.right > rect.left):
                    walk(c, depth + 1)
                    continue
                ctype = str(c.ControlTypeName or "")
                cname = str(c.Name or "")
                if role and role not in ctype.lower():
                    walk(c, depth + 1)
                    continue
                if name_contains and name_contains not in cname.lower():
                    walk(c, depth + 1)
                    continue
                try:
                    offscreen = bool(c.IsOffscreen)
                except Exception:
                    offscreen = False
                nodes.append({"type": ctype, "name": cname[:120], "cx": int(cx), "cy": int(cy),
                              "offscreen": offscreen})
                walk(c, depth + 1)
            except Exception:
                continue

    try:
        walk(auto.GetRootControl(), 0)
    except Exception as e:
        return [], str(e)
    return nodes, ""


def ui_find(text: str, role: str = "", monitor: int = 0, max_nodes: int = 200) -> dict:
    """Найти элементы по тексту (нечётко) + опционально роли. Возвращает совпадения с cx/cy."""
    nodes, err = _collect_ui(monitor, role, text, max_nodes)
    if err and not nodes:
        return {"ok": False, "reason": "missing_dep" if "uiautomation" in err else "error", "error": err}
    return {"ok": True, "found": nodes, "count": len(nodes)}


def assert_ui(text: str, present: bool = True, role: str = "", monitor: int = 0) -> dict:
    """Проверить есть ли элемент. ok=True только если утверждение holds."""
    res = ui_find(text, role, monitor)
    if not res.get("ok"):
        return res
    holds = (res.get("count", 0) > 0) == present
    out = {"ok": holds, "holds": holds, "expected_present": present,
           "count": res.get("count", 0), "matches": res.get("found", [])[:10]}
    if not holds:
        out["reason"] = "assert_failed"
    return out


def wait_for_window(title: str, timeout: float = 15.0) -> dict:
    """Ждать пока откроется окно с подстрокой в заголовке."""
    try:
        import pygetwindow as gw  # type: ignore
    except ImportError:
        return {"ok": False, "reason": "missing_dep", "error": "нет pygetwindow"}
    found = _poll(timeout, 0.5, lambda: [w.title for w in gw.getAllWindows()
                                         if title.lower() in (w.title or "").lower()][:1])
    if found:
        return {"ok": True, "title": found[0]}
    return {"ok": False, "reason": "timeout", "error": f"окно не открылось за {timeout}с: {title}"}


def wait_for_ui_element(text: str, role: str = "", timeout: float = 15.0, monitor: int = 0) -> dict:
    """Ждать появления UI-элемента (кнопки/поля)."""
    found = _poll(timeout, 0.7, lambda: (ui_find(text, role, monitor, 100).get("found") or [None])[0])
    if found:
        return {"ok": True, "match": found}
    return {"ok": False, "reason": "timeout", "error": f"элемент не появился за {timeout}с: {text!r}"}


def _region_score(img1, img2) -> float:
    from PIL import ImageChops, ImageStat  # type: ignore

    diff = ImageChops.difference(img1.convert("L"), img2.convert("L"))
    return float(ImageStat.Stat(diff).mean[0]) / 255.0 * 100.0


def wait_for_change(x: int, y: int, w: int, h: int, timeout: float = 15.0, monitor: int = 0,
                    threshold: float = 3.0) -> dict:
    """Ждать изменения пикселей в области (игры, канвасы, загрузки)."""
    try:
        base = _grab_region(monitor, x, y, w, h)
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}

    def changed():
        try:
            score = _region_score(base, _grab_region(monitor, x, y, w, h))
            return {"score": round(score, 2)} if score >= threshold else None
        except Exception:
            return None

    hit = _poll(timeout, 0.5, changed)
    if hit:
        return {"ok": True, "changed": True, "score": hit["score"]}
    return {"ok": False, "reason": "timeout", "changed": False,
            "error": f"область не изменилась за {timeout}с"}


def screenshot_diff(x: int, y: int, w: int, h: int, monitor: int = 0, delay: float = 1.0) -> dict:
    """Изменилась ли область за delay секунд. Проверка «сработало ли действие»."""
    try:
        import time as _time

        base = _grab_region(monitor, x, y, w, h)
        _time.sleep(max(0.2, min(10.0, delay)))
        score = _region_score(base, _grab_region(monitor, x, y, w, h))
        return {"ok": True, "changed": score >= 3.0, "score": round(score, 2)}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def window_find(substring: str, limit: int = 10) -> dict:
    """Нечёткий поиск окон: все совпадения с прямоугольниками."""
    try:
        import pygetwindow as gw  # type: ignore
    except ImportError:
        return {"ok": False, "reason": "missing_dep", "error": "нет pygetwindow"}
    try:
        out = []
        for w in gw.getAllWindows():
            try:
                if substring.lower() in (w.title or "").lower():
                    out.append({"title": w.title, "rect": [w.left, w.top, w.width, w.height],
                                "is_active": bool(w.isActive)})
                    if len(out) >= max(1, limit):
                        break
            except Exception:
                continue
        return {"ok": True, "found": out, "count": len(out)}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


def screen_info() -> dict:
    """Мониторы, разрешение, DPI/масштаб. Для маппинга 0-1000 в пиксели."""
    try:
        import mss  # type: ignore

        with mss.mss() as sct:
            mons = [{"left": m["left"], "top": m["top"], "width": m["width"], "height": m["height"]}
                    for m in sct.monitors[1:]]
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}
    dpi, scale = 96, 100
    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        try:
            dpi = ctypes.windll.user32.GetDpiForSystem()
        except Exception:
            hdc = ctypes.windll.user32.GetDC(None)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(None, hdc)
        scale = int(dpi / 96 * 100)
    except Exception:
        pass
    return {"ok": True, "monitors": mons, "count": len(mons),
            "primary": mons[0] if mons else {}, "dpi": dpi, "scale_percent": scale,
            "note": "0-1000 модели = доля от ширины/высоты монитора"}
