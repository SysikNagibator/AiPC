@echo off
REM Подпись exe сертификатом код-подписи (убирает синий SmartScreen).
REM Нужен PFX-файл сертификата. Как получить — см. docs\SIGNING.md
REM Использование:
REM   set AIPC_CERT=C:\certs\s1steam.pfx
REM   set AIPC_CERT_PASS=пароль
REM   tools\sign.bat
chcp 65001 >nul
cd /d "%~dp0.."

if "%AIPC_CERT%"=="" (
  echo [sign] Не задан AIPC_CERT. Положи PFX и задай переменные. См. docs\SIGNING.md
  exit /b 1
)

where signtool >nul 2>&1
if %errorlevel% neq 0 (
  echo [sign] Нет signtool. Поставь Windows SDK (https://developer.microsoft.com/windows/downloads/windows-sdk/)
  echo [sign] или Build Tools с компонентом "Windows SDK".
  exit /b 1
)

for %%F in (dist\aipc.exe dist\AiPC-Setup.exe) do (
  if exist "%%F" (
    echo [sign] Подписываю %%F ...
    signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /f "%AIPC_CERT%" /p "%AIPC_CERT_PASS%" "%%F"
    if %errorlevel% neq 0 (
      echo [sign] ОШИБКА подписи %%F
      exit /b 1
    )
    signtool verify /pa "%%F"
  )
)
echo [sign] Готово.
