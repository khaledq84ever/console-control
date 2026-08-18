"""Full-pipeline fuzz test: run main.py's real virtual-pad path (HID read
loop -> parser -> VirtualPad) against 100 randomized synthetic controller
reports spanning DS3/DS4/DS5 and USB/Bluetooth, using a fake HID device and
a fake ViGEmBus gamepad - the same no-hardware approach as test_e2e.py, just
with many more, randomized cases instead of a handful of fixed ones.

Expected outcomes are computed independently of controller_parsers.py /
virtual_pad.py (byte offsets and the button-name map are re-derived here
from the documented layouts), so this can't pass by trivially agreeing with
whatever the implementation happens to do - it's exactly the kind of check
that would have caught the DS3 l2_digital/r2_digital byte-swap bug found
during review, generalized to the whole pipeline and both other pads.

Deterministic: seeded RNG, so any failure is reproducible.
"""
import os
import random
import sys
import types
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import hid  # noqa: F401
except ImportError:
    # hidapi's compiled extension isn't available in every environment
    # (e.g. a sandbox with no pip/build tools). These tests never touch a
    # real HID device - FakeHidDevice below replaces it entirely - so a
    # minimal stub is enough to let hid_reader.py's module-level `import
    # hid` succeed.
    sys.modules["hid"] = types.SimpleNamespace(enumerate=lambda *a, **k: [], device=object)

import hid_reader
import main


class FakeHidDevice:
    """Same fake used in test_e2e.py: feeds a fixed queue of reports, one
    per read() call, then ends the loop like Ctrl+C once drained."""

    def __init__(self, reports):
        self._reports = list(reports)
        self.closed = False

    def open_path(self, path):
        pass

    def set_nonblocking(self, flag):
        pass

    def read(self, size, timeout_ms=200):
        if self._reports:
            return list(self._reports.pop(0))
        raise KeyboardInterrupt

    def send_feature_report(self, data):
        pass

    def close(self):
        self.closed = True


_XUSB_NAMES = [
    "XUSB_GAMEPAD_A", "XUSB_GAMEPAD_B", "XUSB_GAMEPAD_X", "XUSB_GAMEPAD_Y",
    "XUSB_GAMEPAD_LEFT_SHOULDER", "XUSB_GAMEPAD_RIGHT_SHOULDER",
    "XUSB_GAMEPAD_BACK", "XUSB_GAMEPAD_START",
    "XUSB_GAMEPAD_LEFT_THUMB", "XUSB_GAMEPAD_RIGHT_THUMB", "XUSB_GAMEPAD_GUIDE",
    "XUSB_GAMEPAD_DPAD_UP", "XUSB_GAMEPAD_DPAD_DOWN",
    "XUSB_GAMEPAD_DPAD_LEFT", "XUSB_GAMEPAD_DPAD_RIGHT",
]

_DPAD_LABELS = {
    "XUSB_GAMEPAD_DPAD_UP", "XUSB_GAMEPAD_DPAD_DOWN",
    "XUSB_GAMEPAD_DPAD_LEFT", "XUSB_GAMEPAD_DPAD_RIGHT",
}

# ControllerState.buttons key -> Xbox button label, per README's stated
# mapping intent (PS face buttons -> matching-position Xbox face buttons).
_EXPECTED_XBOX_LABEL = {
    "cross": "XUSB_GAMEPAD_A", "circle": "XUSB_GAMEPAD_B",
    "square": "XUSB_GAMEPAD_X", "triangle": "XUSB_GAMEPAD_Y",
    "l1": "XUSB_GAMEPAD_LEFT_SHOULDER", "r1": "XUSB_GAMEPAD_RIGHT_SHOULDER",
    "share": "XUSB_GAMEPAD_BACK", "options": "XUSB_GAMEPAD_START",
    "l3": "XUSB_GAMEPAD_LEFT_THUMB", "r3": "XUSB_GAMEPAD_RIGHT_THUMB",
    "ps": "XUSB_GAMEPAD_GUIDE",
}

# hat value (DS4/DS5 raw 0=N..7=NW,8=released convention) -> Xbox dpad labels
_HAT_TO_DIRS = {
    0: {"XUSB_GAMEPAD_DPAD_UP"}, 1: {"XUSB_GAMEPAD_DPAD_UP", "XUSB_GAMEPAD_DPAD_RIGHT"},
    2: {"XUSB_GAMEPAD_DPAD_RIGHT"}, 3: {"XUSB_GAMEPAD_DPAD_RIGHT", "XUSB_GAMEPAD_DPAD_DOWN"},
    4: {"XUSB_GAMEPAD_DPAD_DOWN"}, 5: {"XUSB_GAMEPAD_DPAD_DOWN", "XUSB_GAMEPAD_DPAD_LEFT"},
    6: {"XUSB_GAMEPAD_DPAD_LEFT"}, 7: {"XUSB_GAMEPAD_DPAD_LEFT", "XUSB_GAMEPAD_DPAD_UP"},
    8: set(),
}

_DPAD_DIR_TO_XBOX = {
    "up": {"XUSB_GAMEPAD_DPAD_UP"}, "right": {"XUSB_GAMEPAD_DPAD_RIGHT"},
    "down": {"XUSB_GAMEPAD_DPAD_DOWN"}, "left": {"XUSB_GAMEPAD_DPAD_LEFT"},
    "none": set(),
}

_DS4_FLAG_NAMES = ("square", "cross", "circle", "triangle", "l1", "r1",
                    "share", "options", "l3", "r3", "ps", "touchpad")
_DS3_FLAG_NAMES = ("square", "cross", "circle", "triangle", "l1", "r1",
                    "l2_digital", "r2_digital", "share", "options", "l3", "r3", "ps")


def _make_fake_vgamepad():
    gamepad = MagicMock()
    module = types.SimpleNamespace(
        VX360Gamepad=lambda: gamepad,
        XUSB_BUTTON=types.SimpleNamespace(**{n: n for n in _XUSB_NAMES}),
    )
    return gamepad, module


def _build_ds4_like_report(rng: random.Random, bt: bool) -> tuple[bytes, dict]:
    """Independently encodes a DS4/DS5-shaped USB or Bluetooth report from
    the layout documented in controller_parsers.py's parse_ds4 docstring."""
    lx, ly, rx, ry = (rng.randint(0, 255) for _ in range(4))
    l2, r2 = rng.randint(0, 255), rng.randint(0, 255)
    dpad = rng.randint(0, 8)
    flags = {name: rng.random() < 0.5 for name in _DS4_FLAG_NAMES}

    off = 3 if bt else 1
    report = bytearray(off + 9)
    report[0] = 0x11 if bt else 0x01
    report[off], report[off + 1], report[off + 2], report[off + 3] = lx, ly, rx, ry
    b5 = dpad & 0x0F
    b5 |= (0x10 if flags["square"] else 0) | (0x20 if flags["cross"] else 0)
    b5 |= (0x40 if flags["circle"] else 0) | (0x80 if flags["triangle"] else 0)
    b6 = (0x01 if flags["l1"] else 0) | (0x02 if flags["r1"] else 0)
    b6 |= (0x10 if flags["share"] else 0) | (0x20 if flags["options"] else 0)
    b6 |= (0x40 if flags["l3"] else 0) | (0x80 if flags["r3"] else 0)
    b7 = (0x01 if flags["ps"] else 0) | (0x02 if flags["touchpad"] else 0)
    report[off + 4], report[off + 5], report[off + 6] = b5, b6, b7
    report[off + 7], report[off + 8] = l2, r2

    expected = dict(flags)
    expected.update(dpad=dpad, lx=lx, ly=ly, rx=rx, ry=ry, l2=l2, r2=r2)
    return bytes(report), expected


def _build_ds3_report(rng: random.Random) -> tuple[bytes, dict]:
    """Independently encodes a DS3-shaped report from the SIXAXIS layout
    documented in controller_parsers.py's parse_ds3 docstring/comments."""
    lx, ly, rx, ry = (rng.randint(0, 255) for _ in range(4))
    l2, r2 = rng.randint(0, 255), rng.randint(0, 255)
    flags = {name: rng.random() < 0.5 for name in _DS3_FLAG_NAMES}
    dpad_dir = rng.choice(["none", "up", "right", "down", "left"])

    report = bytearray(20)
    report[0] = 0x01
    b2 = (0x01 if flags["share"] else 0) | (0x02 if flags["l3"] else 0)
    b2 |= (0x04 if flags["r3"] else 0) | (0x08 if flags["options"] else 0)
    b2 |= {"up": 0x10, "right": 0x20, "down": 0x40, "left": 0x80}.get(dpad_dir, 0)
    b3 = (0x01 if flags["l2_digital"] else 0) | (0x02 if flags["r2_digital"] else 0)
    b3 |= (0x04 if flags["l1"] else 0) | (0x08 if flags["r1"] else 0)
    b3 |= (0x10 if flags["triangle"] else 0) | (0x20 if flags["circle"] else 0)
    b3 |= (0x40 if flags["cross"] else 0) | (0x80 if flags["square"] else 0)
    b4 = 0x01 if flags["ps"] else 0
    report[2], report[3], report[4] = b2, b3, b4
    report[6], report[7], report[8], report[9] = lx, ly, rx, ry
    report[18], report[19] = l2, r2

    expected = dict(flags)
    expected.update(dpad_dir=dpad_dir, lx=lx, ly=ly, rx=rx, ry=ry, l2=l2, r2=r2)
    return bytes(report), expected


def _run_one_case(gen: str, report: bytes, expected: dict):
    gamepad, fake_vg = _make_fake_vgamepad()
    sys.modules["vgamepad"] = fake_vg
    sys.modules.pop("virtual_pad", None)

    dev = FakeHidDevice([report])
    orig_open = hid_reader.open_controller
    hid_reader.open_controller = lambda info: dev
    try:
        result = main.run_virtual_pad(f"Fake {gen}", gen, {"path": b"/fake"})
    finally:
        hid_reader.open_controller = orig_open
        sys.modules.pop("vgamepad", None)
        sys.modules.pop("virtual_pad", None)

    assert result == 0, f"run_virtual_pad returned {result} for {gen} report {report.hex()}"
    assert dev.closed

    pressed = {c.kwargs.get("button") for c in gamepad.press_button.call_args_list}

    for name, label in _EXPECTED_XBOX_LABEL.items():
        want = bool(expected.get(name))
        got = label in pressed
        assert got == want, (
            f"{gen} report {report.hex()}: button '{name}' -> {label} "
            f"expected pressed={want}, got pressed={got} (all pressed: {sorted(pressed)})"
        )

    if "dpad" in expected:
        want_dirs = _HAT_TO_DIRS[expected["dpad"]]
    else:
        want_dirs = _DPAD_DIR_TO_XBOX[expected["dpad_dir"]]
    got_dirs = pressed & _DPAD_LABELS
    assert got_dirs == want_dirs, (
        f"{gen} report {report.hex()}: dpad expected {want_dirs}, got {got_dirs}"
    )

    stick_call = gamepad.left_joystick_float.call_args_list[-1]
    assert abs(stick_call.kwargs["x_value_float"] - (expected["lx"] - 128) / 128.0) < 0.02
    assert abs(stick_call.kwargs["y_value_float"] - (-(expected["ly"] - 128) / 128.0)) < 0.02

    rstick_call = gamepad.right_joystick_float.call_args_list[-1]
    assert abs(rstick_call.kwargs["x_value_float"] - (expected["rx"] - 128) / 128.0) < 0.02
    assert abs(rstick_call.kwargs["y_value_float"] - (-(expected["ry"] - 128) / 128.0)) < 0.02

    ltrig_call = gamepad.left_trigger_float.call_args_list[-1]
    assert abs(ltrig_call.kwargs["value_float"] - expected["l2"] / 255.0) < 0.01
    rtrig_call = gamepad.right_trigger_float.call_args_list[-1]
    assert abs(rtrig_call.kwargs["value_float"] - expected["r2"] / 255.0) < 0.01


def _build_100_cases(rng: random.Random) -> list:
    cases = []
    for _ in range(35):
        cases.append(("ds4", *_build_ds4_like_report(rng, bt=False)))
    for _ in range(25):
        cases.append(("ds4", *_build_ds4_like_report(rng, bt=True)))
    for _ in range(20):
        cases.append(("ds5", *_build_ds4_like_report(rng, bt=rng.random() < 0.5)))
    for _ in range(20):
        cases.append(("ds3", *_build_ds3_report(rng)))
    return cases


def test_fuzz_full_pipeline_100_cases():
    rng = random.Random(20260818)  # fixed seed: deterministic, reproducible failures
    cases = _build_100_cases(rng)
    assert len(cases) == 100
    for gen, report, expected in cases:
        _run_one_case(gen, report, expected)


if __name__ == "__main__":
    try:
        test_fuzz_full_pipeline_100_cases()
        print("PASS test_fuzz_full_pipeline_100_cases (100/100 synthetic cases)")
    except AssertionError as e:
        print(f"FAIL test_fuzz_full_pipeline_100_cases: {e}")
        sys.exit(1)
