"""Cross-platform build: PyInstaller onefile + SHA256SUMS.txt.

Usage:  python tools/build_all.py
Output: dist/AiPC-<os>-<ver>[.exe] + dist/SHA256SUMS.txt

Windows keeps tools/build_exe.bat for local use (icon + version resource);
CI uses this script on all three OSes.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass  # раннеры Windows бывают с cp1252-консолью

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

EXCLUDES = ["torch", "ultralytics", "cv2", "numpy", "tkinter", "Tkinter",
            "PIL.ImageTk", "matplotlib", "scipy", "pandas", "sklearn",
            "tensorflow", "IPython", "pytest", "_pytest", "notebook"]


def version() -> str:
    sys.path.insert(0, str(ROOT))
    from aipc import __version__

    return str(__version__)


def build() -> Path:
    ver = version()
    if sys.platform == "win32":
        name = f"AiPC_Win_{ver}"
    elif sys.platform == "darwin":
        name = f"AiPC_macOS_{ver}"
    else:
        name = f"AiPC_Linux_{ver}"
    cmd = [sys.executable, "-m", "PyInstaller", "--onefile",
           "--name", name, "--console", "--clean", "--noconfirm"]
    for mod in EXCLUDES:
        cmd += ["--exclude-module", mod]
    if sys.platform == "win32":
        ico = ROOT / "assets" / "AiPC.ico"
        if ico.exists():
            cmd += ["--icon", str(ico)]
    elif sys.platform == "darwin":
        icns = ROOT / "assets" / "AiPC.icns"
        if icns.exists():
            cmd += ["--icon", str(icns)]
        # Linux: у PyInstaller нет встраиваемых иконок для ELF —
        # иконка ставится через .desktop/hicolor при установке пакета.
    cmd.append(str(ROOT / "tools" / "exe_entry.py"))
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)
    out = DIST / (name + (".exe" if sys.platform == "win32" else ""))
    if not out.exists():
        # PyInstaller names mac dir differently — find it
        cands = sorted(DIST.glob(name + "*"))
        out = cands[0] if cands else out
    return out


def sums(paths: list) -> Path:
    DIST.mkdir(parents=True, exist_ok=True)
    sums_file = DIST / "SHA256SUMS.txt"
    with sums_file.open("w", encoding="utf-8") as f:
        for p in paths:
            h = hashlib.sha256()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 256), b""):
                    h.update(chunk)
            f.write(f"{h.hexdigest()}  {Path(p).name}\n")
    print("wrote", sums_file)
    return sums_file


def main() -> int:
    DIST.mkdir(exist_ok=True)
    out = build()
    print("built:", out, out.stat().st_size // 1048576, "MB")
    sums([out])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
