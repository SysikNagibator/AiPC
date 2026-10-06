@echo off
REM Сборка AiPC: имя файла всегда AiPC_Win_<версия>.exe (версия из кода).
REM Использование: tools\build_exe.bat
chcp 65001 >nul
cd /d "%~dp0.."
python -m pip install pyinstaller pillow
python tools/build_icon.py
python tools/gen_version_info.py
for /f %%v in ('python -c "import aipc; print(aipc.__version__)"') do set VER=%%v
set EXE=AiPC_Win_%VER%.exe
set EXC=--exclude-module torch --exclude-module ultralytics --exclude-module cv2 --exclude-module numpy --exclude-module tkinter --exclude-module Tkinter --exclude-module PIL.ImageTk --exclude-module matplotlib --exclude-module scipy --exclude-module pandas --exclude-module sklearn --exclude-module tensorflow --exclude-module IPython --exclude-module pytest --exclude-module _pytest --exclude-module notebook
pyinstaller --onefile --name %EXE:.exe=% --console --icon assets\AiPC.ico --version-file tools\version_info.txt %EXC% tools/exe_entry.py
pyinstaller --onefile --name AiPC-Setup --console --uac-admin --icon assets\AiPC.ico --version-file tools\version_info.txt %EXC% tools/setup_entry.py
certutil -hashfile dist\%EXE% SHA256 > dist\SHA256SUMS.txt
certutil -hashfile dist\AiPC-Setup.exe SHA256 >> dist\SHA256SUMS.txt
echo Готово: dist\%EXE% и dist\AiPC-Setup.exe (+ SHA256SUMS.txt — приложи к релизу)
pause
