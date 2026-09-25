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


def ui_snapshot(max_nodes: int = 200, monitor: int = 0) -> dict:
    """Дерево UI-элементов (кнопки/поля) с центрами cx/cy в 0-1000. Точное наведение."""
    try:
        import uiautomation as auto  # type: ignore
    except ImportError:
        return {"ok": False, "error": "нет uiautomation. pip install uiautomation (только Windows)"}
    try:
        import mss  # type: ignore

        with mss.mss() as sct:
            mons = sct.monitors
            idx = monitor + 1 if (monitor + 1) < len(mons) else 1
            mon = mons[idx]
        mw, mh, ml, mt = mon["width"], mon["height"], mon["left"], mon["top"]
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
                    if 0 <= cx <= 1000 and 0 <= cy <= 1000 and rect.right > rect.left:
                        nodes.append({
                            "type": str(c.ControlTypeName or ""),
                            "name": str(c.Name or "")[:120],
                            "cx": int(cx), "cy": int(cy),
                        })
                    walk(c, depth + 1)
                except Exception:
                    continue

        walk(auto.GetRootControl(), 0)
        return {"ok": True, "nodes": nodes, "count": len(nodes)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


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
        return {"ok": False, "error": f"окно не найдено: {title_substr}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
