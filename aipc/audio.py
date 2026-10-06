"""Захват аудио: системный звук (loopback) и микрофон через WASAPI.

Движок: pyaudiowpatch (portaudio + WASAPI loopback), float32 моно ->
WAV mono 16-bit. Ресемпл линейный, без новых зависимостей сверх pyaudiowpatch.
"""
from __future__ import annotations

import time as _time

MAX_SECONDS = 30.0


def _wasapi_capture(source: str, seconds: float) -> tuple[bytes, int, float]:
    """Возвращает (pcm16 mono bytes, rate, seconds). Бросает исключения наверх.

    pyaudiowpatch сам владеет потоком PortAudio; ручной COM не нужен.
    """
    import pyaudiowpatch as pya  # type: ignore  # noqa

    p = pya.PyAudio()
    try:
        if source == "loopback":
            info = p.get_default_wasapi_loopback()
        else:
            idx = p.get_default_input_device_info()["index"]
            info = p.get_device_info_by_index(idx)
        rate = int(info.get("defaultSampleRate") or 48000)
        ch = int(info.get("maxInputChannels") or 1)
        channels = min(max(ch, 1), 2)

        stream = p.open(
            format=pya.paFloat32,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=int(info["index"]),
            frames_per_buffer=1024,
        )
        try:
            target = int(rate * seconds)
            buf = bytearray()
            deadline = _time.monotonic() + seconds + 12.0
            import struct

            while len(buf) < target * channels * 4:
                if _time.monotonic() > deadline:
                    break
                try:
                    chunk = stream.read(1024, exception_on_overflow=False)
                except Exception:
                    break
                buf += chunk
            n = min(target, len(buf) // (channels * 4))
            f = memoryview(buf)[: n * channels * 4]
            samples = struct.unpack("<%df" % (n * channels), bytes(f))
            pcm16 = bytearray(n * 2)
            pack = struct.Struct("<h").pack_into
            for i in range(n):
                if channels == 2:
                    s = (samples[i * 2] + samples[i * 2 + 1]) * 0.5
                else:
                    s = samples[i]
                if s > 1.0:
                    s = 1.0
                elif s < -1.0:
                    s = -1.0
                pack(pcm16, i * 2, int(s * 32767))
            got = n
        finally:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass
        return bytes(pcm16), rate, (got / rate) if rate else 0.0
    finally:
        try:
            p.terminate()
        except Exception:
            pass


def _resample_mono(pcm: bytes, src_rate: int, dst_rate: int) -> tuple[bytes, int]:
    """Линейный ресемпл mono int16. Без зависимостей."""
    import array

    if not dst_rate or dst_rate == src_rate or src_rate <= 0:
        return pcm, src_rate
    a = array.array("h")
    a.frombytes(pcm)
    n = len(a)
    if n == 0:
        return pcm, src_rate
    m = max(1, int(n * dst_rate / src_rate))
    out = array.array("h")
    for i in range(m):
        pos = i * (n - 1) / max(1, m - 1) if m > 1 else 0
        i0 = int(pos)
        frac = pos - i0
        i1 = min(i0 + 1, n - 1)
        out.append(int(a[i0] * (1 - frac) + a[i1] * frac))
    data = out.tobytes() if hasattr(out, "tobytes") else out.tostring()
    return data, dst_rate


def _wav_bytes(pcm: bytes, rate: int) -> bytes:
    import struct

    header = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(pcm), b"WAVE",
                         b"fmt ", 16, 1, 1, rate, rate * 2, 2, 16, b"data", len(pcm))
    return header + pcm


def audio_listen(source: str = "loopback", seconds: float = 5.0, rate: int = 0,
                 save_to: str = "") -> dict:
    """Слушать системный звук (loopback: музыка/видео) или микрофон.

    seconds 1-30. rate=0 — частота устройства, иначе ресемпл (напр. 16000).
    save_to — путь .wav: вернуть только путь без байтов (дешево).
    """
    import os as _os

    if _os.name != "nt":
        return {"ok": False, "reason": "error", "error": "только Windows"}
    source = str(source or "loopback").lower()
    if source not in ("loopback", "mic"):
        return {"ok": False, "reason": "bad_arg", "error": "source только mic/loopback"}
    try:
        seconds = max(1.0, min(MAX_SECONDS, float(seconds)))
    except (TypeError, ValueError):
        return {"ok": False, "reason": "bad_arg", "error": "seconds числом 1-30"}
    try:
        import pyaudiowpatch  # type: ignore  # noqa
    except ImportError:
        return {"ok": False, "reason": "missing_dep",
                "error": "нет pyaudiowpatch. pip install pyaudiowpatch"}
    try:
        pcm, dev_rate, actual = _wasapi_capture(source, seconds)
        if not pcm:
            return {"ok": False, "reason": "error",
                    "error": "звук не поймал (нет устройств или поток пуст)"}
        if rate:
            pcm, dev_rate = _resample_mono(pcm, dev_rate, int(rate))
        if save_to:
            from pathlib import Path

            from .policy import check_path_allowed

            ok, err = check_path_allowed(save_to)
            if not ok:
                return {"ok": False, "reason": "denied", "error": err}
            p = Path(save_to).expanduser()
            if not p.suffix:
                p = p.with_suffix(".wav")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(_wav_bytes(pcm, dev_rate))
            return {"ok": True, "path": str(p), "seconds": round(actual, 2),
                    "rate": dev_rate, "source": source}
        import base64

        return {"ok": True, "wav_b64": base64.b64encode(_wav_bytes(pcm, dev_rate)).decode(),
                "seconds": round(actual, 2), "rate": dev_rate, "source": source}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)[:500]}
