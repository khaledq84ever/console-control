"""Synthetic byte-level tests for controller_parsers.

These test that the parsing MATH is internally consistent with the byte
layout documented in controller_parsers.py — they do NOT prove the layout
matches real hardware (no PS controller was available to test against when
this was written). See controller_parsers.py's module docstring and
main.py's --raw mode for how to verify/fix against a real controller.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controller_parsers import parse_ds3, parse_ds4, parse_ds5


def _ds4_usb_report(lx=128, ly=128, rx=128, ry=128, l2=0, r2=0,
                     dpad=8, square=False, cross=False, circle=False, triangle=False,
                     l1=False, r1=False, share=False, options=False,
                     l3=False, r3=False, ps=False, touchpad=False):
    report = bytearray(10)
    report[0] = 0x01
    report[1], report[2], report[3], report[4] = lx, ly, rx, ry
    b5 = (dpad & 0x0F)
    b5 |= (0x10 if square else 0) | (0x20 if cross else 0)
    b5 |= (0x40 if circle else 0) | (0x80 if triangle else 0)
    b6 = (0x01 if l1 else 0) | (0x02 if r1 else 0)
    b6 |= (0x10 if share else 0) | (0x20 if options else 0)
    b6 |= (0x40 if l3 else 0) | (0x80 if r3 else 0)
    b7 = (0x01 if ps else 0) | (0x02 if touchpad else 0)
    report[5], report[6], report[7] = b5, b6, b7
    report[8], report[9] = l2, r2
    return bytes(report)


def test_ds4_sticks_centered():
    r = _ds4_usb_report()
    s = parse_ds4(r)
    assert s.left_stick == (0.0, 0.0)
    assert s.right_stick == (0.0, 0.0)


def test_ds4_stick_extremes():
    r = _ds4_usb_report(lx=255, ly=0, rx=0, ry=255)
    s = parse_ds4(r)
    assert s.left_stick[0] > 0.9
    assert s.left_stick[1] < -0.9
    assert s.right_stick[0] < -0.9
    assert s.right_stick[1] > 0.9


def test_ds4_face_buttons():
    r = _ds4_usb_report(cross=True, triangle=True)
    s = parse_ds4(r)
    assert s.buttons["cross"] is True
    assert s.buttons["triangle"] is True
    assert s.buttons["circle"] is False
    assert s.buttons["square"] is False


def test_ds4_shoulder_and_stick_click_buttons():
    r = _ds4_usb_report(l1=True, r3=True, options=True)
    s = parse_ds4(r)
    assert s.buttons["l1"] is True
    assert s.buttons["r1"] is False
    assert s.buttons["r3"] is True
    assert s.buttons["l3"] is False
    assert s.buttons["options"] is True
    assert s.buttons["share"] is False


def test_ds4_ps_and_touchpad():
    r = _ds4_usb_report(ps=True)
    s = parse_ds4(r)
    assert s.buttons["ps"] is True
    assert s.buttons["touchpad"] is False


def test_ds4_dpad_and_triggers():
    r = _ds4_usb_report(dpad=2, l2=128, r2=255)
    s = parse_ds4(r)
    assert s.dpad == 2
    assert 0.49 < s.l2 < 0.51
    assert s.r2 == 1.0


def test_ds4_bluetooth_offset_shift():
    """Same logical data, shifted 2 bytes for the BT report header."""
    usb = _ds4_usb_report(cross=True, lx=200)
    bt = bytearray(len(usb) + 2)
    bt[0] = 0x11
    bt[3:3 + (len(usb) - 1)] = usb[1:]
    s = parse_ds4(bytes(bt), bt=True)
    assert s.buttons["cross"] is True
    assert s.left_stick[0] > 0.5


def test_ds4_too_short_raises():
    try:
        parse_ds4(bytes([0x01, 0x80]))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_ds5_reuses_ds4_layout_plus_mute():
    r = bytearray(_ds4_usb_report(cross=True))
    r[7] |= 0x04  # mute bit
    s = parse_ds5(bytes(r))
    assert s.buttons["cross"] is True
    assert s.buttons["mute"] is True


def test_ds5_mute_over_bluetooth():
    usb = _ds4_usb_report(cross=True)
    bt = bytearray(len(usb) + 2)
    bt[0] = 0x31
    bt[3:3 + (len(usb) - 1)] = usb[1:]
    bt[3 + 6] |= 0x04  # mute bit, same offset math as parse_ds5/parse_ds4 with bt=True
    s = parse_ds5(bytes(bt), bt=True)
    assert s.buttons["cross"] is True
    assert s.buttons["mute"] is True


def _ds3_report(lx=128, ly=128, rx=128, ry=128, cross=False, square=False,
                 circle=False, triangle=False, select=False, start=False, ps=False,
                 l1=False, r1=False, l2_digital=False, r2_digital=False,
                 l3=False, r3=False, dpad_up=False, dpad_right=False,
                 dpad_down=False, dpad_left=False):
    report = bytearray(20)
    report[0] = 0x01
    b2 = (0x01 if select else 0) | (0x02 if l3 else 0) | (0x04 if r3 else 0) | (0x08 if start else 0)
    b2 |= (0x10 if dpad_up else 0) | (0x20 if dpad_right else 0)
    b2 |= (0x40 if dpad_down else 0) | (0x80 if dpad_left else 0)
    b3 = (0x01 if l2_digital else 0) | (0x02 if r2_digital else 0)
    b3 |= (0x04 if l1 else 0) | (0x08 if r1 else 0)
    b3 |= (0x10 if triangle else 0) | (0x20 if circle else 0)
    b3 |= (0x40 if cross else 0) | (0x80 if square else 0)
    b4 = 0x01 if ps else 0
    report[2], report[3], report[4] = b2, b3, b4
    report[6], report[7], report[8], report[9] = lx, ly, rx, ry
    return bytes(report)


def test_ds3_basic_buttons_and_sticks():
    r = _ds3_report(cross=True, select=True, lx=255)
    s = parse_ds3(r)
    assert s.buttons["cross"] is True
    assert s.buttons["square"] is False
    assert s.buttons["share"] is True  # select
    assert s.left_stick[0] > 0.9


def test_ds3_start_and_ps():
    r = _ds3_report(start=True, ps=True)
    s = parse_ds3(r)
    assert s.buttons["options"] is True  # start
    assert s.buttons["ps"] is True
    assert s.buttons["touchpad"] is False


def test_ds3_shoulder_buttons():
    r = _ds3_report(l1=True, r1=True)
    s = parse_ds3(r)
    assert s.buttons["l1"] is True
    assert s.buttons["r1"] is True
    assert s.buttons["l2_digital"] is False
    assert s.buttons["r2_digital"] is False


def test_ds3_trigger_digital_buttons_dont_alias_select_or_l3():
    """Regression test: l2_digital/r2_digital used to read from the same
    byte/bits as select/l3 (b2 instead of b3), so pressing L2 falsely
    reported select=True, and pressing Select falsely reported
    l2_digital=True. See git history for the fix."""
    r_l2 = _ds3_report(l2_digital=True)
    s_l2 = parse_ds3(r_l2)
    assert s_l2.buttons["l2_digital"] is True
    assert s_l2.buttons["share"] is False

    r_select = _ds3_report(select=True)
    s_select = parse_ds3(r_select)
    assert s_select.buttons["share"] is True
    assert s_select.buttons["l2_digital"] is False

    r_r2 = _ds3_report(r2_digital=True)
    s_r2 = parse_ds3(r_r2)
    assert s_r2.buttons["r2_digital"] is True
    assert s_r2.buttons["l3"] is False

    r_l3 = _ds3_report(l3=True)
    s_l3 = parse_ds3(r_l3)
    assert s_l3.buttons["l3"] is True
    assert s_l3.buttons["r2_digital"] is False


def test_ds3_stick_click_buttons():
    r = _ds3_report(l3=True)
    s = parse_ds3(r)
    assert s.buttons["l3"] is True
    assert s.buttons["r3"] is False

    r2 = _ds3_report(r3=True)
    s2 = parse_ds3(r2)
    assert s2.buttons["r3"] is True
    assert s2.buttons["l3"] is False


def test_ds3_face_buttons_circle_and_triangle():
    r = _ds3_report(circle=True, triangle=True)
    s = parse_ds3(r)
    assert s.buttons["circle"] is True
    assert s.buttons["triangle"] is True
    assert s.buttons["cross"] is False
    assert s.buttons["square"] is False


def test_ds3_dpad_all_directions():
    cases = [
        (dict(dpad_up=True), 0),
        (dict(dpad_up=True, dpad_right=True), 1),
        (dict(dpad_right=True), 2),
        (dict(dpad_right=True, dpad_down=True), 3),
        (dict(dpad_down=True), 4),
        (dict(dpad_down=True, dpad_left=True), 5),
        (dict(dpad_left=True), 6),
        (dict(dpad_left=True, dpad_up=True), 7),
        (dict(), 8),  # released
    ]
    for kwargs, expected_hat in cases:
        s = parse_ds3(_ds3_report(**kwargs))
        assert s.dpad == expected_hat, f"{kwargs} -> expected hat {expected_hat}, got {s.dpad}"


def test_ds3_analog_triggers_fall_back_to_digital_bit_on_short_report():
    """On a report too short to have the analog trigger bytes (<=18/19),
    l2/r2 should fall back to the digital press bit - and that fallback
    must read the same b3 bits as l2_digital/r2_digital, not b2."""
    r = bytearray(_ds3_report(l2_digital=True, r2_digital=True))
    short = bytes(r[:10])  # cuts off before bytes 18/19
    s = parse_ds3(short)
    assert s.l2 == 1.0
    assert s.r2 == 1.0

    r2 = bytearray(_ds3_report())  # neither pressed
    s2 = parse_ds3(bytes(r2[:10]))
    assert s2.l2 == 0.0
    assert s2.r2 == 0.0


def test_ds3_analog_triggers_use_long_report_bytes_when_available():
    r = bytearray(_ds3_report(l2_digital=True, r2_digital=True))
    r[18], r[19] = 200, 100
    s = parse_ds3(bytes(r))
    assert abs(s.l2 - 200 / 255.0) < 0.01
    assert abs(s.r2 - 100 / 255.0) < 0.01


def test_ds3_too_short_raises():
    try:
        parse_ds3(bytes([0x01] * 5))
        assert False, "expected ValueError"
    except ValueError:
        pass


if __name__ == "__main__":
    fails = 0
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            fails += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - fails}/{len(tests)} passed")
    sys.exit(1 if fails else 0)
