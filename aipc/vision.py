"""Vision: скриншоты, окна. Опциональные зависимости, graceful fallback."""
from __future__ import annotations

import base64
import io


def screen_see(monitor: int = 0, max_width: int = 1280) -> dict:
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
            if img.width > max_width:
                h = int(img.height * max_width / img.width)
                img = img.resize((max_width, h))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return {"ok": True, "image_b64": b64, "width": img.width, "height": img.height, "monitor": monitor}
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
