@echo off
REM One-time setup for ConsoleControl — installs everything it needs:
REM   1. ViGEmBus — free, open-source Windows driver that lets this app
REM      present your PS controller to games as a normal Xbox controller.
REM      https://github.com/nefarius/ViGEmBus (official signed installer)
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
    echo   Looking up the latest installer from github.com/nefarius/ViGEmBus...
    REM Asks GitHub's API for whatever the current release asset actually is,
    REM instead of guessing a filename — the project has renamed its release
    REM assets before (and even moved orgs), which silently 404'd a hardcoded
    REM guess in an earlier version of this script.
    set VIGEM_OUT=%TEMP%\ViGEmBusSetup.exe
    powershell -Command ^
        "$rel = Invoke-RestMethod -Uri 'https://api.github.com/repos/nefarius/ViGEmBus/releases/latest';" ^
        "$asset = $rel.assets | Where-Object { $_.name -like '*.exe' -or $_.name -like '*x64*.msi' } | Select-Object -First 1;" ^
        "if ($asset) { Invoke-WebRequest -Uri $asset.browser_download_url -OutFile '%VIGEM_OUT%' }"
    if not exist "%VIGEM_OUT%" (
        echo   Download failed. Install manually from:
        echo   https://github.com/nefarius/ViGEmBus/releases
    ) else (
        echo   Launching installer — approve the Windows prompt to continue...
        start /wait "" "%VIGEM_OUT%"
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
