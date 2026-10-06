"""Видео для агента: инфо и кадры image-блоками.

Движок: ffmpeg из imageio-ffmpeg (бинар внутри пакета, без системной
установки). Кадры декодируются в rawvideo RGB и кодируются в JPEG через PIL.
"""
from __future__ import annotations

import re
import subprocess

MAX_FRAMES = 12
MAX_WIDTH = 1280


def _ffmpeg() -> str:
    import imageio_ffmpeg  # type: ignore  # noqa

    return imageio_ffmpeg.get_ffmpeg_exe()


def _check(path: str):
    from pathlib import Path

    from .policy import check_path_allowed

    ok, err = check_path_allowed(path)
    if not ok:
        return False, "denied", err, None
    p = Path(path).expanduser()
    if not p.is_file():
        return False, "not_found", "файла нет", None
    return True, "", "", p


def _probe_text(path) -> str:
    proc = subprocess.run(
        [_ffmpeg(), "-hide_banner", "-i", str(path)],
        capture_output=True, timeout=20)
    return (proc.stderr or b"").decode("utf-8", "replace")


def _parse_meta(text: str) -> dict:
    dur = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    fps = re.search(r"(\d+(?:\.\d+)?)\s*fps", text)
    res = re.search(r"Video:.*?\s(\d{2,5})x(\d{2,5})", text)
    codec = re.search(r"Video:\s*(\w+)", text)
    duration = (int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3))) if dur else 0.0
    return {
        "seconds": round(duration, 2),
        "fps": float(fps.group(1)) if fps else 0.0,
        "width": int(res.group(1)) if res else 0,
        "height": int(res.group(2)) if res else 0,
        "codec": codec.group(1) if codec else "unknown",
    }


def _grab_sized(path, t: float, width: int, height: int, max_width: int = MAX_WIDTH) -> bytes:
    """Один кадр на момент t -> JPEG bytes."""
    import io

    from PIL import Image

    proc = subprocess.run(
        [_ffmpeg(), "-hide_banner", "-loglevel", "error",
         "-ss", f"{max(0.0, t):.3f}", "-i", str(path),
         "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, timeout=40)
    raw = proc.stdout or b""
    need = width * height * 3
    if len(raw) < need:
        raise RuntimeError("кадр не извлёкся")
    img = Image.frombytes("RGB", (width, height), raw[:need])
    if img.width > max_width:
        h = int(img.height * max_width / img.width)
        img = img.resize((max_width, h))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def video_info(path: str) -> dict:
    """Длительность, размер, fps, кодек. Первый шаг перед извлечением кадров."""
    code, reason, err, p = _check(path)
    if not code:
        return {"ok": False, "reason": reason, "error": err}
    try:
        text = _probe_text(p)
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)[:300]}
    if "Video:" not in text:
        tail = text.strip().splitlines()[-1][:300] if text.strip() else "не удалось прочитать"
        return {"ok": False, "reason": "error", "error": tail}
    meta = _parse_meta(text)
    return {"ok": True, "path": str(p), **meta}


def video_frames(path: str, times: str = "", count: int = 4,
                 max_width: int = MAX_WIDTH) -> dict:
    """Кадры видео как JPEG bytes (отдаются image-блоками выше по стеку).

    times — моменты в секундах через запятую ("1.5,4"); иначе count 1-12
    равномерных кадров. Строка, а не список — чтобы JSON-схема была без anyOf.
    """
    code, reason, err, p = _check(path)
    if not code:
        return {"ok": False, "reason": reason, "error": err}
    try:
        text = _probe_text(p)
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)[:300]}
    meta = _parse_meta(text)
    w, h, dur = meta["width"], meta["height"], meta["seconds"]
    if not w or not h or dur <= 0:
        return {"ok": False, "reason": "error", "error": "не удалось прочитать видео"}
    ts: list[float] = []
    if times:
        raw = times if isinstance(times, str) else ",".join(str(x) for x in times)
        try:
            ts = [max(0.0, min(float(x.strip()), dur - 0.05))
                  for x in raw.split(",") if x.strip()][:MAX_FRAMES]
        except (TypeError, ValueError):
            return {"ok": False, "reason": "bad_arg", "error": 'times — числа через запятую, "1.5,4"'}
        if not ts:
            return {"ok": False, "reason": "bad_arg", "error": "times пустой"}
    else:
        try:
            count = max(1, min(MAX_FRAMES, int(count)))
        except (TypeError, ValueError):
            return {"ok": False, "reason": "bad_arg", "error": "count 1-12"}
        if count == 1:
            ts = [dur / 2]
        else:
            ts = [min(dur * i / (count - 1), dur - 0.05) for i in range(count)]
    frames = []
    for t in ts:
        try:
            frames.append({"t": round(t, 2), "jpeg": _grab_sized(p, t, w, h, max_width)})
        except Exception:
            continue
    if not frames:
        return {"ok": False, "reason": "error", "error": "ни один кадр не извлёкся"}
    return {"ok": True, "path": str(p), "seconds": dur, "width": w, "height": h,
            "frames": frames, "stamps": [f["t"] for f in frames]}
