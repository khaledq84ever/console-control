@echo off
REM One-time setup: installs ViGEmBus, the free open-source Windows driver
REM that lets this app present your PS controller to games as a normal
REM Xbox controller. Official project: https://github.com/ViGEm/ViGEmBus
REM This just downloads and launches Microsoft/ViGEm's own signed installer
REM — you'll get the normal Windows "allow this driver" prompt, same as
REM installing any other device driver.

echo Checking for ViGEmBus...
sc query ViGEmBus >nul 2>&1
if %errorlevel% == 0 (
    echo ViGEmBus is already installed. Nothing to do.
    pause
    exit /b 0
)

echo ViGEmBus not found — downloading the official installer...
set DOWNLOAD_URL=https://github.com/ViGEm/ViGEmBus/releases/latest/download/ViGEmBusSetup_x64.msi
set OUT=%TEMP%\ViGEmBusSetup_x64.msi

powershell -Command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%OUT%'"
if not exist "%OUT%" (
    echo Download failed. Install ViGEmBus manually from:
    echo https://github.com/ViGEm/ViGEmBus/releases
    pause
    exit /b 1
)

echo Launching installer — approve the Windows prompt to continue...
msiexec /i "%OUT%"

echo.
echo If the install finished OK, you're done. Run ConsoleControl.exe next.
pause
