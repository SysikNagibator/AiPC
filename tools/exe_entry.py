"""Wrapper для PyInstaller: сохраняет package-контекст, чтобы относительные импорты работали в exe."""
from aipc.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
