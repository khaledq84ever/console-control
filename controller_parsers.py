"""Pure byte-parsing for PlayStation controller HID input reports (USB and
Bluetooth alike).

No OS/hardware dependencies here on purpose — these are plain functions over
bytes, so they can be unit-tested on any machine (see tests/test_parsers.py)
even without a real controller or Windows attached.

Byte offsets come from public community-documented HID report layouts (the
same ones used by open-source projects like the Linux kernel's hid-sony
driver, pydualsense, and DS4Windows). They have NOT been verified against
real hardware here (built on a machine with no PS controller attached) — if
a button/axis reads wrong on your machine, run `main.py --raw` to dump live
report bytes and see exactly which byte changes, then fix the offset below.
That's what --raw is for.

Bluetooth reports carry the same gamepad data as USB but shifted 2 bytes
later (report ID 0x11 instead of 0x01, plus a small vendor header) — the
`bt=True` flag below applies that shift.
"""
from dataclasses import dataclass, field


@dataclass
class ControllerState:
    left_stick: tuple[float, float] = (0.0, 0.0)   # x, y in -1.0..1.0
    right_stick: tuple[float, float] = (0.0, 0.0)
    l2: float = 0.0   # analog trigger 0.0..1.0
    r2: float = 0.0
    dpad: int = 8      # 0=N,1=NE,2=E,3=SE,4=S,5=SW,6=W,7=NW,8=released (DS4/DS5 hat convention)
    buttons: dict = field(default_factory=dict)  # name -> bool


def _axis_to_unit(byte_val: int) -> float:
    """0..255 (128=center) -> -1.0..1.0"""
    return (byte_val - 128) / 128.0


def parse_ds4(report: bytes, bt: bool = False) -> ControllerState:
    """DualShock 4. USB: report ID 0x01, data starts at byte 1.
    Bluetooth: report ID 0x11, data starts 2 bytes later (byte 3)."""
    off = 3 if bt else 1
    if len(report) < off + 9:
        raise ValueError(f"DS4 report too short: {len(report)} bytes (bt={bt})")

    b5, b6, b7 = report[off + 4], report[off + 5], report[off + 6]
    s = ControllerState(
        left_stick=(_axis_to_unit(report[off]), _axis_to_unit(report[off + 1])),
        right_stick=(_axis_to_unit(report[off + 2]), _axis_to_unit(report[off + 3])),
        l2=report[off + 7] / 255.0,
        r2=report[off + 8] / 255.0,
        dpad=b5 & 0x0F,
    )
    s.buttons = {
        "square": bool(b5 & 0x10),
        "cross": bool(b5 & 0x20),
        "circle": bool(b5 & 0x40),
        "triangle": bool(b5 & 0x80),
        "l1": bool(b6 & 0x01),
        "r1": bool(b6 & 0x02),
        "l2_digital": bool(b6 & 0x04),
        "r2_digital": bool(b6 & 0x08),
        "share": bool(b6 & 0x10),
        "options": bool(b6 & 0x20),
        "l3": bool(b6 & 0x40),
        "r3": bool(b6 & 0x80),
        "ps": bool(b7 & 0x01),
        "touchpad": bool(b7 & 0x02),
    }
    return s


def parse_ds5(report: bytes, bt: bool = False) -> ControllerState:
    """DualSense (PS5). Same core layout as DS4 (sticks/triggers/buttons);
    adds a mute button. USB report ID 0x01, Bluetooth report ID 0x31."""
    state = parse_ds4(report, bt=bt)
    off = 3 if bt else 1
    state.buttons["mute"] = bool(report[off + 6] & 0x04)
    return state


def parse_ds3(report: bytes) -> ControllerState:
    """DualShock 3. Same report layout over USB or Bluetooth (49 bytes,
    report ID at byte 0). This is the LEAST hardware-verified parser here —
    if buttons read wrong, run `main.py --raw` on real hardware and compare.
    """
    if len(report) < 10:
        raise ValueError(f"DS3 report too short: {len(report)} bytes")

    b2, b3, b4 = report[2], report[3], report[4]
    s = ControllerState(
        left_stick=(_axis_to_unit(report[6]), _axis_to_unit(report[7])),
        right_stick=(_axis_to_unit(report[8]), _axis_to_unit(report[9])),
        l2=(report[18] / 255.0) if len(report) > 18 else float(bool(b2 & 0x01)),
        r2=(report[19] / 255.0) if len(report) > 19 else float(bool(b2 & 0x02)),
    )
    dpad_up, dpad_right, dpad_down, dpad_left = (
        bool(b2 & 0x10), bool(b2 & 0x20), bool(b2 & 0x40), bool(b2 & 0x80),
    )
    s.dpad = _dpad_bits_to_hat(dpad_up, dpad_right, dpad_down, dpad_left)
    s.buttons = {
        "square": bool(b3 & 0x80),
        "cross": bool(b3 & 0x40),
        "circle": bool(b3 & 0x20),
        "triangle": bool(b3 & 0x10),
        "l1": bool(b3 & 0x04),
        "r1": bool(b3 & 0x08),
        "l2_digital": bool(b3 & 0x01),
        "r2_digital": bool(b3 & 0x02),
        "share": bool(b2 & 0x01),    # Select
        "options": bool(b2 & 0x08),  # Start
        "l3": bool(b2 & 0x02),
        "r3": bool(b2 & 0x04),
        "ps": bool(b4 & 0x01),
        "touchpad": False,  # DS3 has no touchpad
    }
    return s


def _dpad_bits_to_hat(up: bool, right: bool, down: bool, left: bool) -> int:
    """Convert 4 individual d-pad direction bits to the DS4-style 0-8 hat value."""
    if up and right:
        return 1
    if right and down:
        return 3
    if down and left:
        return 5
    if left and up:
        return 7
    if up:
        return 0
    if right:
        return 2
    if down:
        return 4
    if left:
        return 6
    return 8  # released
