@echo off
REM One-time setup for ConsoleControl — installs everything it needs:
REM   1. ViGEmBus — free, open-source Windows driver that lets this app
REM      present your PS controller to games as a normal Xbox controller.
REM      https://github.com/nefarius/ViGEmBus (official signed installer)
REM   2. .NET Runtime, ASP.NET Core Runtime, .NET Desktop Runtime (latest
REM      LTS) — NOT required by ConsoleControl itself (it's plain
REM      Python/PyInstaller), installed anyway in case something else on
REM      your machine needs one of them. Set SKIP_DOTNET=1 before running
REM      this script if you don't want them.
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
echo [2/2] .NET runtimes (not needed by ConsoleControl itself, installed anyway
echo       in case something else on your machine needs them)
if "%SKIP_DOTNET%"=="1" (
    echo   SKIP_DOTNET=1 set, skipping.
) else (
    echo   Downloading Microsoft's official .NET install script...
    powershell -Command "Invoke-WebRequest -Uri 'https://dot.net/v1/dotnet-install.ps1' -OutFile '%TEMP%\dotnet-install.ps1'"
    if not exist "%TEMP%\dotnet-install.ps1" (
        echo   Download failed. Get it manually from https://dotnet.microsoft.com/download
    ) else (
        REM All 3 latest-LTS runtime families Microsoft ships standalone:
        REM the base .NET runtime, ASP.NET Core (web apps/APIs), and Windows
        REM Desktop (WPF/WinForms apps) — covers whatever else on the machine
        REM might ask for one of these, not just ConsoleControl's own needs.
        echo   Installing .NET Runtime...
        powershell -ExecutionPolicy Bypass -File "%TEMP%\dotnet-install.ps1" -Channel LTS -Runtime dotnet
        echo   Installing ASP.NET Core Runtime...
        powershell -ExecutionPolicy Bypass -File "%TEMP%\dotnet-install.ps1" -Channel LTS -Runtime aspnetcore
        echo   Installing .NET Desktop Runtime...
        powershell -ExecutionPolicy Bypass -File "%TEMP%\dotnet-install.ps1" -Channel LTS -Runtime windowsdesktop
    )
)

echo.
echo === Setup done. Run ConsoleControl.exe next. ===
pause
