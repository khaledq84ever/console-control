"""Unit tests for hid_reader.py's pure logic: matching enumerated HID
devices against the known-controller table, and the Bluetooth-vs-USB path
heuristic. `hid.enumerate` itself is faked here (no real HID access needed),
so this runs anywhere.
"""
import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# hid_reader imports the `hid` package at module load time; stub it out
# before importing hid_reader so this runs on machines without hidapi too.
sys.modules.setdefault("hid", MagicMock())

import hid_reader


def _dev(product_id, path=b"/fake/path"):
    return {"product_id": product_id, "path": path}


def test_list_controllers_matches_known_ds4():
    hid_reader.hid.enumerate = MagicMock(return_value=[_dev(0x05C4)])
    found = hid_reader.list_controllers()
    assert len(found) == 1
    name, gen, info = found[0]
    assert gen == "ds4"
    assert "DualShock 4" in name


def test_list_controllers_matches_every_known_pid():
    from hid_reader import KNOWN_CONTROLLERS
    devices = [_dev(pid) for _, pid, _ in KNOWN_CONTROLLERS]
    hid_reader.hid.enumerate = MagicMock(return_value=devices)
    found = hid_reader.list_controllers()
    assert len(found) == len(KNOWN_CONTROLLERS)
    assert [gen for _, gen, _ in found] == [gen for _, _, gen in KNOWN_CONTROLLERS]


def test_list_controllers_ignores_unknown_sony_device():
    """A Sony-VID device with a product_id we don't recognize (e.g. some
    other Sony peripheral) must not be reported as a controller."""
    hid_reader.hid.enumerate = MagicMock(return_value=[_dev(0xFFFF)])
    found = hid_reader.list_controllers()
    assert found == []


def test_list_controllers_empty_when_none_connected():
    hid_reader.hid.enumerate = MagicMock(return_value=[])
    assert hid_reader.list_controllers() == []


def test_list_controllers_multiple_distinct_controllers():
    hid_reader.hid.enumerate = MagicMock(return_value=[_dev(0x05C4), _dev(0x0CE6)])
    found = hid_reader.list_controllers()
    gens = sorted(gen for _, gen, _ in found)
    assert gens == ["ds4", "ds5"]


def test_is_bluetooth_true_for_bluetooth_path():
    assert hid_reader.is_bluetooth({"path": b"\\\\?\\HID#{BTHENUM}#Dev&whatever"}) is True
    assert hid_reader.is_bluetooth({"path": "some/Bluetooth/path"}) is True


def test_is_bluetooth_false_for_usb_path():
    assert hid_reader.is_bluetooth({"path": b"\\\\?\\HID#VID_054C&PID_05C4#USB"}) is False


def test_is_bluetooth_handles_missing_path():
    assert hid_reader.is_bluetooth({}) is False


def test_open_controller_opens_and_configures_device():
    fake_dev = MagicMock()
    hid_reader.hid.device = MagicMock(return_value=fake_dev)
    result = hid_reader.open_controller({"path": b"/fake/path"})
    fake_dev.open_path.assert_called_once_with(b"/fake/path")
    fake_dev.set_nonblocking.assert_called_once_with(False)
    assert result is fake_dev


def test_enable_ds3_sends_correct_feature_report():
    fake_dev = MagicMock()
    hid_reader.enable_ds3(fake_dev)
    fake_dev.send_feature_report.assert_called_once()
    payload = fake_dev.send_feature_report.call_args[0][0]
    assert payload[0] == 0xF4


def test_enable_ds3_swallows_exceptions():
    """Some hidapi backends throw on this call; it must not crash the
    caller - main.py relies on this being non-fatal."""
    fake_dev = MagicMock()
    fake_dev.send_feature_report.side_effect = OSError("backend says no")
    hid_reader.enable_ds3(fake_dev)  # must not raise


class _AlwaysFailingDevice:
    def read(self, size, timeout_ms=200):
        raise OSError("device is gone")


class _FlakyThenGoodDevice:
    """Fails a few times, then reads succeed - must NOT trip
    max_consecutive_errors, since the counter should reset on any success."""

    def __init__(self, fail_times, then_reports):
        self._fails_left = fail_times
        self._reports = list(then_reports)

    def read(self, size, timeout_ms=200):
        if self._fails_left > 0:
            self._fails_left -= 1
            raise OSError("transient hiccup")
        if self._reports:
            return list(self._reports.pop(0))
        raise KeyboardInterrupt  # deterministic stop once drained


def test_read_loop_gives_up_after_max_consecutive_errors():
    """Regression test: a dead HID handle (unplugged, or a Bluetooth pad
    gone out of range/asleep) never recovers on its own, so read_loop must
    stop retrying and return (not hang forever) once told a limit - letting
    the caller (main.py) reopen a fresh device instead of spinning on a
    handle that will never work again."""
    dev = _AlwaysFailingDevice()
    calls = []
    hid_reader.time.sleep = lambda s: calls.append(s)  # skip real sleeping in the test
    try:
        hid_reader.read_loop(dev, lambda data: None, lambda: True, max_consecutive_errors=5)
    finally:
        import time as _time
        hid_reader.time.sleep = _time.sleep
    # 4 retry sleeps (after errors 1-4), then error 5 hits the cap and
    # returns immediately without a 5th sleep.
    assert len(calls) == 4, f"expected exactly 4 retry sleeps before giving up, got {len(calls)}"


def test_read_loop_resets_error_count_on_any_successful_read():
    dev = _FlakyThenGoodDevice(fail_times=3, then_reports=[bytes([0x01, 0x02])] * 3)
    hid_reader.time.sleep = lambda s: None
    reports_seen = []
    try:
        try:
            hid_reader.read_loop(dev, lambda data: reports_seen.append(data), lambda: True,
                                  max_consecutive_errors=4)
        except KeyboardInterrupt:
            pass  # _FlakyThenGoodDevice's deterministic "queue drained" stop
    finally:
        import time as _time
        hid_reader.time.sleep = _time.sleep
    assert len(reports_seen) == 3, "3 failures then 3 good reads should not hit a 4-error cap"


if __name__ == "__main__":
    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    for name, t in tests:
        try:
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
