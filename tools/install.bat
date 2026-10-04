@echo off
REM AiPC-Setup: установка команды aipc в PATH (нужен админ)
REM Запускать двойным кликом, UAC подтвердить один раз.
chcp 65001 >nul
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo [AiPC] Нужны права админа. Перезапускаю с UAC...
  powershell -Command "Start-Process '%~f0' -Verb RunAs"
  exit /b 0
)
echo [AiPC] Установка...
python -m pip install --upgrade pip
python -m pip install -r "%~dp0..\requirements.txt"
python -m aipc install
echo.
echo [AiPC] Готово. Открой новый cmd и набери: aipc
pause
