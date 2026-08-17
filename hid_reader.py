"""Finds and reads PlayStation controllers over USB or Bluetooth using HID —
works the same way for either transport once the OS has a device node for
it (for Bluetooth, that means: pair it in Windows Bluetooth settings first,
same as any other Bluetooth accessory; this app doesn't need to do the
pairing itself).
"""
import sys
import time

import hid

SONY_VID = 0x054C

# (name, product_id, generation, parser_kind)
KNOWN_CONTROLLERS = [
    ("DualShock 3 (PS3)", 0x0268, "ds3"),
    ("DualShock 4 (PS4) v1", 0x05C4, "ds4"),
    ("DualShock 4 (PS4) v2", 0x09CC, "ds4"),
    ("DualSense (PS5)", 0x0CE6, "ds5"),
    ("DualSense Edge (PS5)", 0x0DF2, "ds5"),
]

# DS3 ships "silent" over USB until the host sends this feature report once.
# This exact 4-byte payload on report ID 0xF4 is the well-known unlock used
# by every DS3 Windows driver (MotioninJoy, SCPToolkit, DsHidMini, etc).
_DS3_USB_ENABLE_REPORT = bytes([0xF4, 0x42, 0x03, 0x00, 0x00])


def list_controllers():
    """Return [(name, generation, hid.device_info dict), ...] for every
    connected/paired PlayStation controller this process can see."""
    found = []
    for info in hid.enumerate(SONY_VID, 0):
        pid = info["product_id"]
        for name, known_pid, gen in KNOWN_CONTROLLERS:
            if pid == known_pid:
                found.append((name, gen, info))
                break
    return found


def open_controller(device_info: dict):
    dev = hid.device()
    dev.open_path(device_info["path"])
    dev.set_nonblocking(False)
    return dev


def is_bluetooth(device_info: dict) -> bool:
    """Best-effort transport guess: HID over Bluetooth on Windows shows up
    with a different bus in the device path than a directly wired USB HID
    endpoint. We don't strictly need to know this up front — read_loop
    figures out the real transport from the report ID it actually receives
    (0x01 = USB layout, 0x11/0x31 = Bluetooth layout) — this is only used
    for the friendly "connected via ___" status line.
    """
    path = device_info.get("path", b"")
    if isinstance(path, bytes):
        path = path.decode(errors="ignore")
    return "bluetooth" in path.lower() or "bthenum" in path.lower()


def enable_ds3(dev) -> None:
    """Send the USB wake-up feature report DS3 needs before it starts
    streaming input reports. Bluetooth DS3 doesn't need this."""
    try:
        dev.send_feature_report(_DS3_USB_ENABLE_REPORT)
    except Exception as exc:  # some hidapi backends want get before set; non-fatal either way
        print(f"(DS3 enable report warning, continuing anyway: {exc})", file=sys.stderr)


def read_loop(dev, on_report, running_flag, poll_errors_ok=True):
    """Block, calling on_report(bytes) for every HID report until
    running_flag() returns False. Reconnection/backoff is the caller's job —
    this just reads."""
    while running_flag():
        try:
            data = dev.read(64, timeout_ms=200)
        except Exception as exc:
            if not poll_errors_ok:
                raise
            print(f"read error: {exc}", file=sys.stderr)
            time.sleep(0.5)
            continue
        if data:
            on_report(bytes(data))
