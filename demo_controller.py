"""Builds a scripted sequence of synthetic USB HID reports for --demo mode
(see main.py) — lets the real parser pipeline run end-to-end with no real
controller, hidapi, or ViGEmBus needed, which is useful in sandboxes like
this dev box where none of those are even installable.

This does NOT prove the byte offsets match real hardware — it only proves
the parsing/dispatch code runs without crashing and decodes what it's fed
the way the docstrings in controller_parsers.py say it should. Only a real
controller (main.py --raw, on Windows) can validate the offsets themselves.
"""


def _ds4_report(lx=128, ly=128, rx=128, ry=128, l2=0, r2=0, dpad=8,
                 square=False, cross=False, circle=False, triangle=False,
                 l1=False, r1=False, share=False, options=False,
                 l3=False, r3=False, ps=False, touchpad=False):
    report = bytearray(10)
    report[0] = 0x01
    report[1], report[2], report[3], report[4] = lx, ly, rx, ry
    b5 = dpad & 0x0F
    b5 |= (0x10 if square else 0) | (0x20 if cross else 0)
    b5 |= (0x40 if circle else 0) | (0x80 if triangle else 0)
    b6 = (0x01 if l1 else 0) | (0x02 if r1 else 0)
    b6 |= (0x10 if share else 0) | (0x20 if options else 0)
    b6 |= (0x40 if l3 else 0) | (0x80 if r3 else 0)
    b7 = (0x01 if ps else 0) | (0x02 if touchpad else 0)
    report[5], report[6], report[7] = b5, b6, b7
    report[8], report[9] = l2, r2
    return bytes(report)


def _ds5_report(lx=128, ly=128, rx=128, ry=128, l2=0, r2=0, dpad=8,
                 square=False, cross=False, circle=False, triangle=False,
                 l1=False, r1=False, share=False, options=False,
                 l3=False, r3=False, ps=False, touchpad=False, mute=False):
    """DS5 puts L2/R2 analog + a sequence byte BETWEEN the sticks and the
    buttons (unlike DS4) - see controller_parsers.parse_ds5's docstring."""
    report = bytearray(11)
    report[0] = 0x01
    report[1], report[2], report[3], report[4] = lx, ly, rx, ry
    report[5], report[6] = l2, r2
    b8 = dpad & 0x0F
    b8 |= (0x10 if square else 0) | (0x20 if cross else 0)
    b8 |= (0x40 if circle else 0) | (0x80 if triangle else 0)
    b9 = (0x01 if l1 else 0) | (0x02 if r1 else 0)
    b9 |= (0x10 if share else 0) | (0x20 if options else 0)
    b9 |= (0x40 if l3 else 0) | (0x80 if r3 else 0)
    b10 = (0x01 if ps else 0) | (0x02 if touchpad else 0) | (0x04 if mute else 0)
    report[8], report[9], report[10] = b8, b9, b10
    return bytes(report)


def _ds3_report(lx=128, ly=128, rx=128, ry=128, cross=False, square=False,
                 circle=False, triangle=False, select=False, start=False, ps=False,
                 l1=False, r1=False, l2_digital=False, r2_digital=False,
                 l3=False, r3=False, dpad_up=False, dpad_right=False,
                 dpad_down=False, dpad_left=False, l2=0, r2=0):
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
    report[18], report[19] = l2, r2
    return bytes(report)


def _ds4_script():
    frames = [
        ("centered / released", _ds4_report()),
        ("face buttons: cross+triangle", _ds4_report(cross=True, triangle=True)),
        ("face buttons: square+circle", _ds4_report(square=True, circle=True)),
        ("shoulders: l1+r1", _ds4_report(l1=True, r1=True)),
        ("stick clicks: l3+r3", _ds4_report(l3=True, r3=True)),
        ("share+options", _ds4_report(share=True, options=True)),
        ("ps+touchpad", _ds4_report(ps=True, touchpad=True)),
    ]
    frames += [(f"dpad={d}", _ds4_report(dpad=d)) for d in range(9)]
    frames += [
        ("left stick full right", _ds4_report(lx=255)),
        ("left stick full left", _ds4_report(lx=0)),
        ("right stick full up", _ds4_report(ry=0)),
        ("triggers: L2 half, R2 full", _ds4_report(l2=128, r2=255)),
    ]
    return frames


def _ds5_script():
    return [
        ("centered / released", _ds5_report()),
        ("face buttons: cross+triangle", _ds5_report(cross=True, triangle=True)),
        ("face buttons: square+circle", _ds5_report(square=True, circle=True)),
        ("shoulders: l1+r1", _ds5_report(l1=True, r1=True)),
        ("stick clicks: l3+r3", _ds5_report(l3=True, r3=True)),
        ("share+options", _ds5_report(share=True, options=True)),
        ("ps+touchpad", _ds5_report(ps=True, touchpad=True)),
        ("mute", _ds5_report(mute=True)),
    ] + [(f"dpad={d}", _ds5_report(dpad=d)) for d in range(9)] + [
        ("left stick full right", _ds5_report(lx=255)),
        ("left stick full left", _ds5_report(lx=0)),
        ("right stick full up", _ds5_report(ry=0)),
        ("triggers: L2 half, R2 full (must NOT fire any button)", _ds5_report(l2=128, r2=255)),
    ]


def _ds3_script():
    return [
        ("centered / released", _ds3_report()),
        ("face buttons: cross+triangle", _ds3_report(cross=True, triangle=True)),
        ("face buttons: square+circle", _ds3_report(square=True, circle=True)),
        ("shoulders: l1+r1", _ds3_report(l1=True, r1=True)),
        ("triggers (digital): l2+r2", _ds3_report(l2_digital=True, r2_digital=True)),
        ("select (share) alone", _ds3_report(select=True)),
        ("l3 alone (must not alias select)", _ds3_report(l3=True)),
        ("start (options) + ps", _ds3_report(start=True, ps=True)),
        ("dpad up", _ds3_report(dpad_up=True)),
        ("dpad right", _ds3_report(dpad_right=True)),
        ("dpad down", _ds3_report(dpad_down=True)),
        ("dpad left", _ds3_report(dpad_left=True)),
        ("left stick full right", _ds3_report(lx=255)),
        ("analog triggers (long report): l2=200 r2=100", _ds3_report(l2=200, r2=100)),
    ]


_SCRIPTS = {"ds3": _ds3_script, "ds4": _ds4_script, "ds5": _ds5_script}


def scripted_reports(gen: str) -> list:
    """Returns [(label, raw_report_bytes), ...] for the given generation."""
    return _SCRIPTS[gen]()
