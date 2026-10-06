"""Иконки приложения из нового логотипа (зелёный неон, 2026).

Файлы (все лежат в assets/):
  AiPC_Logo.svg — векторный исходник (эталон дизайна);
  AiPC_Logo.png — рендер SVG 1024x1024 (прозрачные углы);
  AiPC.ico      — иконка Windows (exe/setup): готовый файл от дизайнера,
                  используется как есть, НЕ перегенерируется;
  AiPC.icns     — иконка macOS: собирается этим скриптом из PNG
                  (PNG-фреймы 16..1024, как делает iconutil).

Логотип уже содержит тёмную плашку и обводку — ретуши нет, только ресайз.
Превью icon_preview_*.png — для проверки видимости, не коммитим.

Использование: python tools/build_icon.py
"""
from __future__ import annotations

import io
import struct
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "AiPC_Logo.png"
ICO = ROOT / "assets" / "AiPC.ico"
ICNS = ROOT / "assets" / "AiPC.icns"

# Канонические фреймы иконки Windows (совпадают с файлом от дизайнера).
ICO_SIZES = {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
             (128, 128), (256, 256)}
# (тип чанка icns, размер кадра): PNG-данные, как делает iconutil.
ICNS_FRAMES = [
    ("icp4", 16), ("icp5", 32), ("icp6", 64),
    ("ic07", 128), ("ic08", 256), ("ic09", 512), ("ic10", 1024),
    ("ic11", 32), ("ic12", 64), ("ic13", 256), ("ic14", 512),
]


def check_ico(dst: Path) -> None:
    """Файл от дизайнера используем как есть — только проверяем состав."""
    img = Image.open(dst)
    sizes = set(img.info.get("sizes") or ())
    assert ICO_SIZES <= sizes, f"{dst}: нет фреймов {sorted(ICO_SIZES - sizes)}"
    img.size = (256, 256)
    img.load()
    print(f"OK: {dst} ({dst.stat().st_size // 1024} KB, {len(sizes)} frames)")


def _png_bytes(img: Image.Image, size: int) -> bytes:
    frame = img.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    frame.save(buf, format="PNG")
    return buf.getvalue()


def write_icns(img: Image.Image, dst: Path) -> None:
    body = bytearray()
    for kind, size in ICNS_FRAMES:
        data = _png_bytes(img, size)
        body += kind.encode("ascii")
        body += struct.pack(">I", len(data) + 8)
        body += data
    with dst.open("wb") as f:
        f.write(b"icns")
        f.write(struct.pack(">I", len(body) + 8))
        f.write(body)


def check_icns(dst: Path) -> None:
    """Минимальная проверка структуры .icns (без macOS под рукой)."""
    raw = dst.read_bytes()
    assert raw[:4] == b"icns", "bad magic"
    assert struct.unpack(">I", raw[4:8])[0] == len(raw), "bad length"
    pos, seen = 8, []
    while pos < len(raw):
        kind = raw[pos:pos + 4].decode("ascii")
        size = struct.unpack(">I", raw[pos + 4:pos + 8])[0]
        payload = raw[pos + 8:pos + size]
        assert payload[:8] == b"\x89PNG\r\n\x1a\n", f"{kind} is not PNG"
        seen.append((kind, size))
        pos += size
    kinds = [k for k, _ in seen]
    assert kinds == [k for k, _ in ICNS_FRAMES], f"frames mismatch: {kinds}"
    print(f"OK: {dst} ({len(raw) // 1024} KB, {len(seen)} frames)")


def main() -> None:
    logo = Image.open(SRC).convert("RGBA")
    w, h = logo.size
    assert w == h and w >= 1024, f"{SRC} должен быть квадратным >=1024, а он {logo.size}"
    check_ico(ICO)
    write_icns(logo, ICNS)
    check_icns(ICNS)
    # Превью на белом и тёмном фоне для проверки видимости (не коммитим).
    for name, bg in (("preview_white", (255, 255, 255, 255)), ("preview_dark", (24, 24, 24, 255))):
        canvas = Image.new("RGBA", (256, 256), bg)
        canvas.alpha_composite(logo.resize((200, 200), Image.LANCZOS), (28, 28))
        canvas.convert("RGB").save(ROOT / "assets" / f"icon_{name}.png")
        print(f"OK: assets/icon_{name}.png")


if __name__ == "__main__":
    main()
