"""First-hour hardware check. Run this BEFORE writing any more code.

    python scripts/smoke_test.py            # all steps
    python scripts/smoke_test.py --i2c      # only the I2C scan (after wiring a sensor)
    python scripts/smoke_test.py --loopback # jumper GPIO25->GPIO26 and GPIO8->GPIO9 first (no parts)
    python scripts/smoke_test.py --watch    # live I2C scan mirrored on the device while you fix wiring

Needs OG firmware (ogfw) on the FREE-WILi; see CLAUDE.md "Firmware". Every device step goes
through probe/hw.py, so a PASS here means the code the agent uses works on the real device.

Each step prints PASS/FAIL. Paste the full output to Claude if anything fails.
"""

import argparse
import sys
import time
import traceback
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

results: list[tuple[str, bool, str]] = []


def step(name: str):
    def decorator(fn):
        def run(*args):
            print(f"\n=== {name} ===", flush=True)
            try:
                detail = fn(*args) or ""
                results.append((name, True, str(detail)))
                print(f"PASS {detail}")
                return True
            except Exception as ex:  # noqa: BLE001 - we want every failure reported
                results.append((name, False, f"{type(ex).__name__}: {ex}"))
                print(f"FAIL {type(ex).__name__}: {ex}")
                traceback.print_exc()
                return False

        return run

    return decorator


@step("1. onewili package installed")
def check_install():
    try:
        return f"onewili {version('onewili')}"
    except PackageNotFoundError as ex:
        raise RuntimeError("Run: pip install -r requirements.txt") from ex


@step("2. find the FREE-WILi over USB")
def find_device():
    import onewili

    found = onewili.find_devices()
    if not found:
        raise RuntimeError(
            "No FREE-WILi found. Check: USB cable is a DATA cable, device is powered on, no other "
            "program (serial monitor, App Explorer) has the port open. On Linux you may need to add "
            "your user to the dialout group."
        )
    names = [str(u.name).split(" (")[0] for u in found[0].usb_devices if "Serial" in str(u.kind)]
    if not any(name.startswith("FWOG main ogfw") for name in names):
        raise RuntimeError(
            f"Found {found[0]} but it is not running OG firmware (USB names: {names}). "
            "Flash it: see CLAUDE.md 'Firmware'."
        )
    return f"found {len(found)}: {found[0]} ({', '.join(names)})"


@step("3. open + firmware version")
def open_device(holder):
    from probe.hw import FreeWiliProbe

    holder.append(FreeWiliProbe())
    return holder[0].firmware()


@step("4. board LEDs (watch the device: they should cycle red, green, blue, off)")
def leds(probe):
    for status in ("fail", "ok", "working", "off"):
        probe.set_status(status)
        time.sleep(0.4)


@step("5. display text (watch the screen)")
def display(probe):
    probe.show_text("Probe smoke test OK")


@step("6. speaker tone")
def tone(probe):
    probe.beep(True)


@step("7. read header pins")
def pins(probe):
    return ", ".join(f"GPIO{pin}={value}" for pin, value in probe.read_pins().items())


@step("8. I2C scan (wire a sensor first: SDA->GPIO16, SCL->GPIO17, VCC, GND)")
def i2c(probe):
    found = probe.scan_i2c()
    if not found:
        return "bus scanned OK but NOTHING answered (expected if no sensor is wired yet)"
    return "found " + ", ".join(f"0x{a:02X}" for a in found)


@step("9. pin loopback (jumper GPIO25 -> GPIO26)")
def pin_loopback(probe):
    seen = []
    for state, want in (("high", 1), ("low", 0)):
        probe.set_pin(25, state)
        time.sleep(0.05)
        got = probe.read_pins()[26]
        seen.append(got)
        if got != want:
            raise RuntimeError(f"drove GPIO25={want} but GPIO26 read {got}: jumper missing/loose or wrong pins")
    return f"GPIO26 followed GPIO25 {seen}"


@step("10. UART loopback (jumper GPIO8 TX -> GPIO9 RX)")
def uart_loopback(probe):
    import threading

    message = b"probe loopback"
    threading.Timer(0.3, probe.uart_write, args=(message,)).start()
    received = probe.uart_listen(1.5)
    if message not in received:
        raise RuntimeError(f"sent {message!r}, received {received!r}: check the 8->9 jumper and UART baud settings")
    return f"echoed {message!r}"


def watch(probe, seconds: float, until: set[int]) -> None:
    """Rescan the bus about once a second and mirror the result on the device (silent).

    For fixing wiring without looking at the laptop: red LEDs + "I2C: none" while nothing
    answers, green LEDs + the addresses as soon as something does.
    """
    print(f"\n=== watching the I2C bus for {seconds:.0f} s (Ctrl-C to stop) ===", flush=True)
    start = time.monotonic()
    last: list[int] | None = None
    stable = 0
    try:
        while time.monotonic() - start < seconds:
            found = probe.scan_i2c()
            if found != last:
                text = " ".join(f"0x{a:02X}" for a in found) or "none"
                print(f"[{time.monotonic() - start:5.1f}s] I2C: {text}", flush=True)
                probe.set_status("ok" if found else "fail")
                probe.show_text(f"I2C: {text}")
                last, stable = found, 0
            stable += 1
            if until and until <= set(found) and stable >= 3:
                print("all expected addresses answered 3 scans in a row", flush=True)
                return
            time.sleep(0.7)
    except KeyboardInterrupt:
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--i2c", action="store_true", help="only run the I2C scan")
    parser.add_argument("--loopback", action="store_true", help="only run pin + UART loopback tests")
    parser.add_argument("--watch", type=float, nargs="?", const=180.0, metavar="SECONDS",
                        help="rescan I2C continuously and show the result on the device (default 180 s)")
    parser.add_argument("--until", default="", metavar="ADDRS",
                        help="with --watch: stop early once these answer, e.g. 0x14,0x44")
    args = parser.parse_args()

    holder: list = []
    if not check_install() or not find_device() or not open_device(holder):
        summary()
        sys.exit(1)
    probe = holder[0]
    try:
        if args.watch:
            watch(probe, args.watch, {int(a, 16) for a in args.until.split(",") if a})
        elif args.loopback:
            pin_loopback(probe)
            uart_loopback(probe)
        else:
            if not args.i2c:
                leds(probe)
                display(probe)
                tone(probe)
                pins(probe)
            i2c(probe)
    finally:
        probe.close()
    summary()
    if not all(ok for _, ok, _ in results):
        sys.exit(1)


def summary() -> None:
    print("\n=== SUMMARY ===")
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


if __name__ == "__main__":
    main()
