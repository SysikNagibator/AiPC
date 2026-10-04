"""Сборка assets/AiPC.ico из AiPC_Logo.png.

Проблема: исходный логотип — тёмно-синий глиф на прозрачности, в проводнике
(особенно на тёмной теме) иконка выглядит как чёрный квадрат.
Решение: яркий синий глиф на тёмной скруглённой плашке со светлой обводкой —
видно и на белой, и на тёмной теме, в стиле постера.

Использование: python tools/build_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "AiPC_Logo.png"
DST = ROOT / "assets" / "AiPC.ico"

TILE = 1024
BG = (13, 24, 48, 255)        # тёмно-синяя плашка
BORDER = (80, 150, 255, 255)  # яркая обводка
TOP = (110, 180, 255)         # верх градиента глифа
BOTTOM = (36, 99, 235)        # низ градиента глифа


def rounded_tile(size: int) -> Image.Image:
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    r = int(size * 0.22)
    d.rounded_rectangle([8, 8, size - 8, size - 8], radius=r, fill=BG)
    d.rounded_rectangle([8, 8, size - 8, size - 8], radius=r, outline=BORDER, width=max(6, size // 42))
    return tile


def glyph_layer(size: int) -> Image.Image:
    logo = Image.open(SRC).convert("RGBA")
    # Маска из альфа-канала исходника
    mask = logo.split()[3].resize((size, size), Image.LANCZOS)
    # Вертикальный градиент
    grad = Image.new("RGBA", (size, size))
    px = grad.load()
    for y in range(size):
        t = y / max(1, size - 1)
        c = tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3)) + (255,)
        for x in range(size):
            px[x, y] = c
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask)
    return out


def main() -> None:
    tile = rounded_tile(TILE)
    glyph = glyph_layer(int(TILE * 0.72))
    tile.alpha_composite(glyph, (int(TILE * 0.14), int(TILE * 0.14)))
    tile.save(DST, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"OK: {DST}")
    # Превью на белом и тёмном фоне для проверки видимости
    for name, bg in (("preview_white", (255, 255, 255, 255)), ("preview_dark", (24, 24, 24, 255))):
        canvas = Image.new("RGBA", (256, 256), bg)
        canvas.alpha_composite(tile.resize((200, 200), Image.LANCZOS), (28, 28))
        canvas.convert("RGB").save(ROOT / "assets" / f"icon_{name}.png")
        print(f"OK: assets/icon_{name}.png")


if __name__ == "__main__":
    main()
