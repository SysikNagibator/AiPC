"""Генерация tools/version_info.txt из версии кода.

Имя файла всегда AiPC_Win_<версия>.exe. Не править руками.
Использование: python tools/gen_version_info.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aipc import __version__  # noqa: E402
from aipc.installer import exe_filename  # noqa: E402


def _v4(version: str) -> tuple[int, int, int, int]:
    parts = []
    for p in version.split("."):
        digits = "".join(c for c in p if c.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])  # type: ignore[return-value]


def main() -> None:
    v = _v4(__version__)
    name = exe_filename()
    text = f"""# UTF-8 (сгенерировано tools/gen_version_info.py, не править руками)
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={v},
    prodvers={v},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', 'S1sTeam'),
            StringStruct('FileDescription', 'AiPC от SYSIK — доступ агента к ПК'),
            StringStruct('FileVersion', '{__version__}'),
            StringStruct('InternalName', 'aipc'),
            StringStruct('LegalCopyright', 'Copyright (c) 2026 SYSIK (MIT)'),
            StringStruct('OriginalFilename', '{name}'),
            StringStruct('ProductName', 'AiPC'),
            StringStruct('ProductVersion', '{__version__}'),
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    out = Path(__file__).resolve().parent / "version_info.txt"
    out.write_text(text, encoding="utf-8")
    print(f"OK: {out} ({name})")


if __name__ == "__main__":
    main()
