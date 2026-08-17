# Console Control

Plug in (or Bluetooth-pair) a PS3, PS4, or PS5 controller and it just works
as a normal controller in every PC game — no per-game configuration needed.

It works by reading the real controller over USB HID or Bluetooth, then
emitting a virtual Xbox 360 controller via **ViGEmBus** (a free, open-source
Windows driver). Every PC game already understands Xbox controllers, so this
sidesteps games that don't natively support PlayStation pads.

## Quick start (Windows)

1. **Install ViGEmBus once**: double-click `install_vigembus.bat`
   (downloads the official signed installer from the
   [ViGEmBus project](https://github.com/ViGEm/ViGEmBus) and runs it — you'll
   get the normal Windows driver-install confirmation prompt).
2. **Connect your controller**:
   - USB: plug the cable in.
   - Bluetooth: pair it first in Windows Settings → Bluetooth & devices
     (same as any Bluetooth accessory) — this app doesn't do the pairing,
     Windows does.
3. Run `ConsoleControl.exe`. It auto-detects the controller and says
   **"Ready!"** — that's it, open any game.

**Optional:** `install_dotnet.bat` installs the latest .NET Desktop Runtime.
ConsoleControl.exe itself doesn't need it (it's plain Python/PyInstaller,
no .NET dependency) — only run this if something else on your machine
requires .NET.

## Building the .exe

PyInstaller can't cross-compile, so `build_exe.bat` has to run **on
Windows**:
```
build_exe.bat
```
Output: `dist\ConsoleControl.exe`

## Running from source (any OS, for development)

```
pip install -r requirements.txt
python main.py --list      # just detect controllers, no ViGEmBus needed
python main.py --raw       # print raw HID bytes (see below)
python main.py             # normal mode: drive a virtual Xbox pad
```
Note: `vgamepad` (the ViGEmBus client) only works on Windows — `--list` and
`--raw` work anywhere HID access is available, since they don't touch it.

## Supported controllers

| Controller | Transport | Confidence |
|---|---|---|
| DualSense (PS5) | USB + Bluetooth | High — layout shared with DS4, widely documented |
| DualSense Edge (PS5) | USB + Bluetooth | High |
| DualShock 4 (PS4), both hardware revisions | USB + Bluetooth | High |
| DualShock 3 (PS3) | USB + Bluetooth | Lower — see note below |

**Honesty note:** the byte offsets used to decode each controller's HID
reports come from public, community-documented specs (the same ones used by
projects like DS4Windows, pydualsense, and the Linux kernel's `hid-sony`
driver) — this was built without a real PS controller attached to test
against. DS3 in particular has the least consistent documentation across
sources. If a button or stick reads wrong on your actual controller:

```
ConsoleControl.exe --raw
```

This prints the raw HID report bytes live and highlights which byte changed
each time you press something — from there, fixing an offset in
`controller_parsers.py` is a one-line change. `tests/test_parsers.py` has
synthetic tests for the byte math itself (do the bit-masks decode correctly)
but can't validate the offsets are in the *right place* for real hardware —
only real hardware can do that.

## Files

- `controller_parsers.py` — pure byte→state parsing, no OS/hardware deps, unit-tested
- `hid_reader.py` — finds/opens the controller via HID, handles the PS3 USB "wake up" quirk
- `virtual_pad.py` — maps parsed state onto a ViGEmBus virtual Xbox 360 pad
- `main.py` — the console app tying it together
- `install_vigembus.bat` — one-time driver setup
- `build_exe.bat` — packaging
