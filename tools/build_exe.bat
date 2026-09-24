@echo off
REM Сборка AiPC.exe + AiPC-Setup.exe через PyInstaller
chcp 65001 >nul
cd /d "%~dp0.."
python -m pip install pyinstaller pillow
pyinstaller --onefile --name aipc --console --icon assets\AiPC.ico --exclude-module torch --exclude-module ultralytics tools/exe_entry.py
pyinstaller --onefile --name AiPC-Setup --console --uac-admin --icon assets\AiPC.ico --exclude-module torch --exclude-module ultralytics tools/setup_entry.py
echo Готово: dist\aipc.exe и dist\AiPC-Setup.exe
pause
