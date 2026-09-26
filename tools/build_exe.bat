@echo off
REM Сборка AiPC.exe + AiPC-Setup.exe через PyInstaller
chcp 65001 >nul
cd /d "%~dp0.."
python -m pip install pyinstaller pillow
python tools/build_icon.py
set EXC=--exclude-module torch --exclude-module ultralytics --exclude-module cv2 --exclude-module numpy --exclude-module tkinter --exclude-module Tkinter --exclude-module PIL.ImageTk --exclude-module matplotlib --exclude-module scipy --exclude-module pandas --exclude-module sklearn --exclude-module tensorflow --exclude-module IPython --exclude-module pytest --exclude-module _pytest --exclude-module notebook
pyinstaller --onefile --name aipc --console --icon assets\AiPC.ico --version-file tools\version_info.txt %EXC% tools/exe_entry.py
pyinstaller --onefile --name AiPC-Setup --console --uac-admin --icon assets\AiPC.ico --version-file tools\version_info.txt %EXC% tools/setup_entry.py
echo Готово: dist\aipc.exe и dist\AiPC-Setup.exe
pause
