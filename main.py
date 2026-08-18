"""Console Control — plug in (or pair) a PS3/PS4/PS5 controller and it just
works as a normal controller in every PC game, over USB cable or Bluetooth.

Usage:
    ConsoleControl.exe                 auto-detect, run as a virtual Xbox pad
    ConsoleControl.exe --raw           don't touch ViGEmBus, just print raw
                                        HID bytes as they change (wiring test
                                        / used to fix a wrong button mapping)
    ConsoleControl.exe --list          list detected controllers and exit
"""
import argparse
import datetime
import sys
import time

import hid_reader
from controller_parsers import parse_ds3, parse_ds4, parse_ds5

PARSERS = {"ds3": parse_ds3, "ds4": parse_ds4, "ds5": parse_ds5}

BT_REPORT_IDS = {0x11, 0x31}


def _transport_label(report_id: int) -> str:
    return "Bluetooth" if report_id in BT_REPORT_IDS else "USB cable"


def _open_ds5_report_log():
    """DS5's byte layout was wrong for a long time and its Bluetooth offset
    is still unverified against real hardware (see controller_parsers.py's
    parse_ds5 docstring) — so every DS5 connection logs its raw report bytes
    to a timestamped file, regardless of --raw/normal mode, giving something
    concrete to check parser offsets against without needing --raw run
    separately. One line per distinct report, deduped like --raw's own
    on-screen output."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"ds5_report_log_{ts}.txt"
    f = open(path, "w", encoding="utf-8")
    f.write(f"# Console Control DS5 raw HID report log — started {datetime.datetime.now().isoformat()}\n")
    f.write("# columns: <seconds since start> <report id, hex> <full report, hex bytes>\n")
    f.flush()
    return path, f


def _make_ds5_logger(log_file):
    start = time.monotonic()
    last = None

    def log_report(data: bytes):
        nonlocal last
        if data == last:
            return
        last = data
        elapsed = time.monotonic() - start
        hex_bytes = " ".join(f"{b:02x}" for b in data)
        log_file.write(f"{elapsed:8.3f} {data[0]:#04x} {hex_bytes}\n")
        log_file.flush()

    return log_report


def cmd_list() -> int:
    found = hid_reader.list_controllers()
    if not found:
        print("No PlayStation controller detected.")
        print("  - USB: plug the cable into the PC")
        print("  - Bluetooth: pair it first in Windows Settings > Bluetooth")
        return 1
    print(f"Found {len(found)} controller(s):")
    for name, gen, info in found:
        print(f"  - {name}  (path: {info['path']})")
    return 0


def _wait_for_controller(poll_seconds=2.0):
    print("Waiting for a PlayStation controller (USB or Bluetooth)...")
    print("  Plug it in with a cable, or pair it in Windows Settings > Bluetooth.")
    while True:
        found = hid_reader.list_controllers()
        if found:
            return found[0]
        time.sleep(poll_seconds)


def run_raw(name, gen, info):
    print(f"Connected: {name} — raw mode (no virtual pad, just printing report bytes)")
    print("Press buttons / move sticks to see which bytes change. Ctrl+C to stop.\n")
    dev = hid_reader.open_controller(info)
    if gen == "ds3":
        hid_reader.enable_ds3(dev)

    log_path, log_file = (_open_ds5_report_log() if gen == "ds5" else (None, None))
    if log_path:
        print(f"Logging raw DS5 reports to {log_path}\n")
    log_report = _make_ds5_logger(log_file) if log_file else None

    last = None
    running = True

    def on_report(data: bytes):
        nonlocal last
        if data != last:
            print(" ".join(f"{b:02x}" for b in data))
            last = data
        if log_report:
            log_report(data)

    try:
        hid_reader.read_loop(dev, on_report, lambda: running)
    except KeyboardInterrupt:
        pass
    finally:
        dev.close()
        if log_file:
            log_file.close()
        print("\nStopped.")


def run_virtual_pad(name, gen, info):
    import virtual_pad  # imported lazily: needs ViGEmBus/vgamepad only in this mode

    print(f"Connected: {name}")
    try:
        pad = virtual_pad.VirtualPad()
    except Exception as exc:
        print("\nCouldn't create the virtual Xbox controller.")
        print("This almost always means ViGEmBus isn't installed yet.")
        print("Run install_setup.bat (in this folder), then try again.")
        print(f"(details: {exc})")
        return 1

    dev = hid_reader.open_controller(info)
    if gen == "ds3":
        hid_reader.enable_ds3(dev)

    log_path, log_file = (_open_ds5_report_log() if gen == "ds5" else (None, None))
    if log_path:
        print(f"Logging raw DS5 reports to {log_path} (for verifying the parser)")
    log_report = _make_ds5_logger(log_file) if log_file else None

    parser = PARSERS[gen]
    running = True
    last_status_time = [0.0]

    def on_report(data: bytes):
        if log_report:
            log_report(data)
        report_id = data[0]
        bt = report_id in BT_REPORT_IDS
        try:
            state = parser(data, bt=bt) if gen != "ds3" else parser(data)
        except ValueError:
            return  # short/garbage report, skip a frame rather than crash
        pad.update(state)

        now = time.time()
        if now - last_status_time[0] > 2.0:
            last_status_time[0] = now
            pressed = [b for b, v in state.buttons.items() if v]
            print(f"\rActive as Xbox controller ({_transport_label(report_id)}) "
                  f"— pressed: {', '.join(pressed) if pressed else 'none':<40}", end="", flush=True)

    print("Ready! This controller now works as an Xbox controller in any game.")
    print("Press Ctrl+C here to stop.\n")
    try:
        hid_reader.read_loop(dev, on_report, lambda: running)
    except KeyboardInterrupt:
        pass
    finally:
        pad.close()
        dev.close()
        if log_file:
            log_file.close()
        print("\nStopped.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="PS3/PS4/PS5 controller driver for PC")
    ap.add_argument("--raw", action="store_true", help="print raw HID bytes instead of driving a virtual pad")
    ap.add_argument("--list", action="store_true", help="list connected controllers and exit")
    args = ap.parse_args()

    print("=== Console Control — PlayStation controller driver ===\n")

    if args.list:
        return cmd_list()

    name, gen, info = _wait_for_controller()
    if args.raw:
        run_raw(name, gen, info)
        return 0
    return run_virtual_pad(name, gen, info)


def cli_main() -> int:
    """Wraps main() with a last-resort safety net: hid_reader.read_loop only
    wraps dev.read() in try/except, not the on_report callback it invokes
    (see read_loop's docstring/source) - so anything raised from deeper in
    the pipeline (e.g. a vgamepad/ViGEmBus hiccup from pad.update(), not the
    ValueError already caught for short/garbage reports) would otherwise
    crash the packaged .exe with a raw traceback instead of a message a
    non-technical user can act on."""
    try:
        return main()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"\nSomething went wrong: {exc}", file=sys.stderr)
        print("Try unplugging/replugging the controller and running again.", file=sys.stderr)
        print("If it keeps happening, please open an issue with this message.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(cli_main())
