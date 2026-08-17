@echo off
REM Optional: installs the latest .NET Desktop Runtime.
REM NOT required by ConsoleControl.exe itself (it's a plain PyInstaller/Python
REM build with no .NET dependency) — this is here in case something else on
REM your machine needs it. Uses Microsoft's own dotnet-install script with
REM -Channel LTS so it always grabs whatever the current latest LTS release
REM is, instead of a version number baked into this file that could go stale.

echo Downloading Microsoft's official .NET install script...
powershell -Command "Invoke-WebRequest -Uri 'https://dot.net/v1/dotnet-install.ps1' -OutFile '%TEMP%\dotnet-install.ps1'"
if not exist "%TEMP%\dotnet-install.ps1" (
    echo Download failed. Get it manually from https://dotnet.microsoft.com/download
    pause
    exit /b 1
)

echo Installing latest .NET Desktop Runtime (LTS channel)...
powershell -ExecutionPolicy Bypass -File "%TEMP%\dotnet-install.ps1" -Channel LTS -Runtime windowsdesktop

echo.
echo Done.
pause
