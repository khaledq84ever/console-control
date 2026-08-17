@echo off
REM Build a standalone ConsoleControl.exe. Must run ON WINDOWS
REM (PyInstaller can't cross-compile from Linux/Mac).

python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --console --name ConsoleControl --collect-all vgamepad main.py

echo.
echo Done. Find it at dist\ConsoleControl.exe
