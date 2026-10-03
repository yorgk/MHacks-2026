"""First-hour hardware check. Run this BEFORE writing any more code.

    cd freewili-probe
    python scripts/smoke_test.py            # all steps
    python scripts/smoke_test.py --i2c      # only the I2C scan (after wiring a sensor)

Each step prints PASS/FAIL. Paste the full output to Claude if anything fails.
"""

import argparse
import sys
import time
import traceback
from importlib.metadata import PackageNotFoundError, version

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


@step("1. freewili package installed")
def check_install():
    try:
        return f"freewili {version('freewili')}"
    except PackageNotFoundError as ex:
        raise RuntimeError("Run: pip install -r requirements.txt") from ex


@step("2. find the FREE-WILi over USB")
def find_device():
    from freewili import FreeWili

    found = FreeWili.find_all()
    if not found:
        raise RuntimeError(
            "No FREE-WILi found. Check: USB cable is a DATA cable, device is powered on, no other "
            "program (serial monitor, FREE-WILi GUI) has the port open. On Linux you may need to add "
            "your user to the dialout group."
        )
    return f"found {len(found)}: {found[0]}"


@step("3. open + firmware versions")
def open_device(fw):
    fw.open().expect("open failed")
    from freewili.types import FreeWiliProcessorType as P

    info = []
    for proc in (P.Main, P.Display):
        r = fw.get_app_info(proc)
        info.append(str(r.unwrap()) if r.is_ok() else f"{proc.name}: {r.unwrap_err()}")
    return "; ".join(info)


@step("4. board LEDs (watch the device: they should cycle red, green, blue, off)")
def leds(fw):
    for color in ((60, 0, 0), (0, 60, 0), (0, 0, 60), (0, 0, 0)):
        for led in range(7):
            fw.set_board_leds(led, *color).expect(f"LED {led} failed")
        time.sleep(0.4)


@step("5. display text (watch the screen)")
def display(fw):
    fw.show_text_display("Probe smoke test OK").expect("show_text_display failed")


@step("6. speaker tone")
def tone(fw):
    fw.play_audio_tone(880, 0.3, 0.5).expect("play_audio_tone failed")


@step("7. read header pins")
def pins(fw):
    from freewili.types import GPIO_MAP

    values = fw.get_io().expect("get_io failed")
    return ", ".join(f"{GPIO_MAP[p].split('/')[0]}={values[p]}" for p in GPIO_MAP)


@step("8. I2C scan (wire a sensor first: SDA->GPIO16, SCL->GPIO17, VCC, GND)")
def i2c(fw):
    found = fw.poll_i2c().expect("poll_i2c failed")
    if not found:
        return "bus scanned OK but NOTHING answered (expected if no sensor is wired yet)"
    return "found " + ", ".join(f"0x{a:02X}" for a in found)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--i2c", action="store_true", help="only run the I2C scan")
    args = parser.parse_args()

    if not check_install() or not find_device():
        summary()
        sys.exit(1)
    from freewili import FreeWili

    fw = FreeWili.find_first().unwrap()
    try:
        if not open_device(fw):
            summary()
            sys.exit(1)
        if not args.i2c:
            leds(fw)
            display(fw)
            tone(fw)
            pins(fw)
        i2c(fw)
    finally:
        fw.close()
    summary()


def summary() -> None:
    print("\n=== SUMMARY ===")
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


if __name__ == "__main__":
    main()
