"""End-to-end pipeline tests: fake HID device -> read loop -> parser ->
virtual pad, exercising the real code paths in main.py/hid_reader.py rather
than just the byte-math in controller_parsers.py.

No real controller or ViGEmBus needed — the HID device and the ViGEmBus
gamepad are both faked here, so this runs anywhere (including this Linux
dev box and CI), unlike a true hardware test.
"""
import sys
import os
import types
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# hid_reader imports the real `hid` package at module load time; stub it out
# so this runs on machines without hidapi installed too (e.g. this Linux dev
# box) - the fake HID device below never touches the real thing anyway.
sys.modules.setdefault("hid", MagicMock())

import hid_reader
import main


class FakeHidDevice:
    """Stands in for hid.device(): open_path/read/close/send_feature_report,
    fed from a fixed queue of reports (bytes), each returned once."""

    def __init__(self, reports):
        self._reports = list(reports)
        self.closed = False
        self.feature_reports_sent = []

    def open_path(self, path):
        pass

    def set_nonblocking(self, flag):
        pass

    def read(self, size, timeout_ms=200):
        if self._reports:
            return list(self._reports.pop(0))
        # Queue drained: end the read loop the same way Ctrl+C does, rather
        # than returning [] forever (a real disconnected/idle device would
        # just keep timing out — but a test needs a deterministic stop).
        raise KeyboardInterrupt

    def send_feature_report(self, data):
        self.feature_reports_sent.append(bytes(data))

    def close(self):
        self.closed = True


def _ds4_report(lx=128, ly=128, rx=128, ry=128, l2=0, r2=0, cross=False):
    r = bytearray(10)
    r[0] = 0x01
    r[1], r[2], r[3], r[4] = lx, ly, rx, ry
    r[5] = 0x20 if cross else 0
    r[8], r[9] = l2, r2
    return bytes(r)


def test_raw_mode_dedupes_and_prints_all_distinct_reports(capsys):
    reports = [_ds4_report(), _ds4_report(cross=True), _ds4_report(cross=True), _ds4_report()]
    dev = FakeHidDevice(reports)
    info = {"path": b"/fake"}

    import hid_reader as hr
    orig_open = hr.open_controller
    hr.open_controller = lambda i: dev
    try:
        main.run_raw("Fake DS4", "ds4", info)
    finally:
        hr.open_controller = orig_open

    out = capsys.readouterr().out
    printed_hex_lines = [l for l in out.splitlines() if all(c in "0123456789abcdef " for c in l.strip()) and l.strip()]
    # 4 reports fed, but two are identical back-to-back (deduped) -> 3 distinct lines
    assert len(printed_hex_lines) == 3, f"expected 3 distinct report lines, got {len(printed_hex_lines)}:\n{out}"
    assert dev.closed


def test_virtual_pad_end_to_end_receives_correct_calls():
    reports = [_ds4_report(), _ds4_report(cross=True, lx=255)]
    dev = FakeHidDevice(reports)
    info = {"path": b"/fake"}

    fake_gamepad = MagicMock()
    fake_vg_module = types.SimpleNamespace(
        VX360Gamepad=lambda: fake_gamepad,
        XUSB_BUTTON=types.SimpleNamespace(
            XUSB_GAMEPAD_A="A", XUSB_GAMEPAD_B="B", XUSB_GAMEPAD_X="X", XUSB_GAMEPAD_Y="Y",
            XUSB_GAMEPAD_LEFT_SHOULDER="LB", XUSB_GAMEPAD_RIGHT_SHOULDER="RB",
            XUSB_GAMEPAD_BACK="BACK", XUSB_GAMEPAD_START="START",
            XUSB_GAMEPAD_LEFT_THUMB="L3", XUSB_GAMEPAD_RIGHT_THUMB="R3",
            XUSB_GAMEPAD_GUIDE="GUIDE",
            XUSB_GAMEPAD_DPAD_UP="UP", XUSB_GAMEPAD_DPAD_DOWN="DOWN",
            XUSB_GAMEPAD_DPAD_LEFT="LEFT", XUSB_GAMEPAD_DPAD_RIGHT="RIGHT",
        ),
    )
    sys.modules["vgamepad"] = fake_vg_module
    sys.modules.pop("virtual_pad", None)  # force re-import against the fake

    import hid_reader as hr
    orig_open = hr.open_controller
    hr.open_controller = lambda i: dev
    try:
        main.run_virtual_pad("Fake DS4", "ds4", info)
    finally:
        hr.open_controller = orig_open
        sys.modules.pop("vgamepad", None)
        sys.modules.pop("virtual_pad", None)

    # second report presses cross and pushes left stick right -> both should
    # have reached the (fake) gamepad via press_button/left_joystick_float
    pressed = [c.kwargs.get("button") for c in fake_gamepad.press_button.call_args_list]
    assert "A" in pressed, f"expected cross (XUSB A) to be pressed, got {pressed}"

    stick_calls = fake_gamepad.left_joystick_float.call_args_list
    assert any(c.kwargs.get("x_value_float", 0) > 0.5 for c in stick_calls), \
        f"expected a left-stick call with x > 0.5, got {stick_calls}"

    assert fake_gamepad.update.called
    assert fake_gamepad.reset.called
    assert dev.closed


def test_bluetooth_report_dispatches_correctly_end_to_end():
    usb = _ds4_report(cross=True)
    bt = bytearray(len(usb) + 2)
    bt[0] = 0x11
    bt[3:3 + (len(usb) - 1)] = usb[1:]
    dev = FakeHidDevice([bytes(bt)])
    info = {"path": b"/fake"}

    fake_gamepad = MagicMock()
    fake_vg_module = types.SimpleNamespace(
        VX360Gamepad=lambda: fake_gamepad,
        XUSB_BUTTON=types.SimpleNamespace(
            XUSB_GAMEPAD_A="A", XUSB_GAMEPAD_B="B", XUSB_GAMEPAD_X="X", XUSB_GAMEPAD_Y="Y",
            XUSB_GAMEPAD_LEFT_SHOULDER="LB", XUSB_GAMEPAD_RIGHT_SHOULDER="RB",
            XUSB_GAMEPAD_BACK="BACK", XUSB_GAMEPAD_START="START",
            XUSB_GAMEPAD_LEFT_THUMB="L3", XUSB_GAMEPAD_RIGHT_THUMB="R3",
            XUSB_GAMEPAD_GUIDE="GUIDE",
            XUSB_GAMEPAD_DPAD_UP="UP", XUSB_GAMEPAD_DPAD_DOWN="DOWN",
            XUSB_GAMEPAD_DPAD_LEFT="LEFT", XUSB_GAMEPAD_DPAD_RIGHT="RIGHT",
        ),
    )
    sys.modules["vgamepad"] = fake_vg_module
    sys.modules.pop("virtual_pad", None)

    import hid_reader as hr
    orig_open = hr.open_controller
    hr.open_controller = lambda i: dev
    try:
        main.run_virtual_pad("Fake DS4 (BT)", "ds4", info)
    finally:
        hr.open_controller = orig_open
        sys.modules.pop("vgamepad", None)
        sys.modules.pop("virtual_pad", None)

    pressed = [c.kwargs.get("button") for c in fake_gamepad.press_button.call_args_list]
    assert "A" in pressed, f"BT report should still decode cross correctly, got {pressed}"


def test_ds3_enable_quirk_sent_before_reading():
    dev = FakeHidDevice([])
    info = {"path": b"/fake"}
    import hid_reader as hr
    orig_open = hr.open_controller
    hr.open_controller = lambda i: dev
    try:
        main.run_raw("Fake DS3", "ds3", info)
    finally:
        hr.open_controller = orig_open

    assert len(dev.feature_reports_sent) == 1
    assert dev.feature_reports_sent[0][0] == 0xF4


def test_garbage_short_report_skipped_not_crashed():
    reports = [bytes([0x01, 0x80]), _ds4_report(cross=True)]  # first is too short to parse
    dev = FakeHidDevice(reports)
    info = {"path": b"/fake"}

    fake_gamepad = MagicMock()
    fake_vg_module = types.SimpleNamespace(
        VX360Gamepad=lambda: fake_gamepad,
        XUSB_BUTTON=types.SimpleNamespace(
            XUSB_GAMEPAD_A="A", XUSB_GAMEPAD_B="B", XUSB_GAMEPAD_X="X", XUSB_GAMEPAD_Y="Y",
            XUSB_GAMEPAD_LEFT_SHOULDER="LB", XUSB_GAMEPAD_RIGHT_SHOULDER="RB",
            XUSB_GAMEPAD_BACK="BACK", XUSB_GAMEPAD_START="START",
            XUSB_GAMEPAD_LEFT_THUMB="L3", XUSB_GAMEPAD_RIGHT_THUMB="R3",
            XUSB_GAMEPAD_GUIDE="GUIDE",
            XUSB_GAMEPAD_DPAD_UP="UP", XUSB_GAMEPAD_DPAD_DOWN="DOWN",
            XUSB_GAMEPAD_DPAD_LEFT="LEFT", XUSB_GAMEPAD_DPAD_RIGHT="RIGHT",
        ),
    )
    sys.modules["vgamepad"] = fake_vg_module
    sys.modules.pop("virtual_pad", None)

    import hid_reader as hr
    orig_open = hr.open_controller
    hr.open_controller = lambda i: dev
    try:
        main.run_virtual_pad("Fake DS4", "ds4", info)  # must not raise
    finally:
        hr.open_controller = orig_open
        sys.modules.pop("vgamepad", None)
        sys.modules.pop("virtual_pad", None)

    pressed = [c.kwargs.get("button") for c in fake_gamepad.press_button.call_args_list]
    assert "A" in pressed, "should still process the valid report after skipping the garbage one"


if __name__ == "__main__":
    import io
    import contextlib

    class _FakeCapsys:
        def readouterr(self):
            return types.SimpleNamespace(out=self._buf.getvalue())

    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    for name, t in tests:
        buf = io.StringIO()
        try:
            if "capsys" in t.__code__.co_varnames[:t.__code__.co_argcount]:
                fc = _FakeCapsys()
                fc._buf = buf
                with contextlib.redirect_stdout(buf):
                    t(fc)
            else:
                with contextlib.redirect_stdout(buf):
                    t()
            print(f"PASS {name}")
        except AssertionError as e:
            fails += 1
            print(f"FAIL {name}: {e}")
        except Exception as e:
            fails += 1
            print(f"ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - fails}/{len(tests)} passed")
    sys.exit(1 if fails else 0)
