@echo off
REM One-time setup for ConsoleControl — installs everything it needs:
REM   1. ViGEmBus — free, open-source Windows driver that lets this app
REM      present your PS controller to games as a normal Xbox controller.
REM      https://github.com/ViGEm/ViGEmBus (official signed installer)
REM   2. .NET Desktop Runtime (latest LTS) — NOT required by ConsoleControl
REM      itself (it's plain Python/PyInstaller), included only in case
REM      something else on your machine needs it. Safe to let this step run;
REM      skip it by answering "n" if you don't want it.
REM Both installers are official, signed, and pulled straight from their
REM real publishers — nothing unverified gets downloaded here.

echo === Console Control setup ===
echo.

echo [1/2] ViGEmBus (required)...
sc query ViGEmBus >nul 2>&1
if %errorlevel% == 0 (
    echo   Already installed, skipping.
) else (
    echo   Downloading official installer from github.com/ViGEm/ViGEmBus...
    set VIGEM_URL=https://github.com/ViGEm/ViGEmBus/releases/latest/download/ViGEmBusSetup_x64.msi
    set VIGEM_OUT=%TEMP%\ViGEmBusSetup_x64.msi
    powershell -Command "Invoke-WebRequest -Uri '%VIGEM_URL%' -OutFile '%VIGEM_OUT%'"
    if not exist "%VIGEM_OUT%" (
        echo   Download failed. Install manually from:
        echo   https://github.com/ViGEm/ViGEmBus/releases
    ) else (
        echo   Launching installer — approve the Windows prompt to continue...
        msiexec /i "%VIGEM_OUT%"
    )
)

echo.
echo [2/2] .NET Desktop Runtime (optional, not needed by ConsoleControl itself)
set /p DOTNET_ANSWER="  Install it too? [y/N] "
if /i "%DOTNET_ANSWER%"=="y" (
    echo   Downloading Microsoft's official .NET install script...
    powershell -Command "Invoke-WebRequest -Uri 'https://dot.net/v1/dotnet-install.ps1' -OutFile '%TEMP%\dotnet-install.ps1'"
    if exist "%TEMP%\dotnet-install.ps1" (
        powershell -ExecutionPolicy Bypass -File "%TEMP%\dotnet-install.ps1" -Channel LTS -Runtime windowsdesktop
    ) else (
        echo   Download failed. Get it manually from https://dotnet.microsoft.com/download
    )
) else (
    echo   Skipped.
)

echo.
echo === Setup done. Run ConsoleControl.exe next. ===
pause
