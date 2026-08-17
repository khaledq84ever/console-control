@echo off
REM Builds ConsoleControl.exe if it's missing, then runs it.
cd /d "%~dp0"

if not exist "dist\ConsoleControl.exe" (
    echo dist\ConsoleControl.exe not found, building it first...
    call build_exe.bat
)

if not exist "dist\ConsoleControl.exe" (
    echo Build failed - dist\ConsoleControl.exe still missing.
    pause
    exit /b 1
)

dist\ConsoleControl.exe
pause
