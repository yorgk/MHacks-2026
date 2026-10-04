"""Hardware layer: everything that touches the FREE-WILi lives here.

Two implementations with the same interface:
  - FreeWiliProbe: the real device over USB, running OG firmware (ogfw), via the `onewili` package
  - MockProbe:     a fake device so the agent/tests run without hardware (PROBE_MOCK=1)

Every method returns plain Python data (or raises ProbeError) so the agent layer never
has to know about the onewili library's Result types.

The old `freewili` pip package only speaks the deprecated v73 firmware and hangs on OG firmware,
so it is not used any more.
"""

from __future__ import annotations

import os
import queue
import time
from typing import Protocol

# Header pins exposed on the FREE-WILi 1 connector.
HEADER_PINS: dict[int, str] = {
    8: "GPIO8 / UART1 TX (out)",
    9: "GPIO9 / UART1 RX (in)",
    10: "GPIO10 / UART1 CTS (in)",
    11: "GPIO11 / UART1 RTS (out)",
    12: "GPIO12 / SPI1 RX (in)",
    13: "GPIO13 / SPI1 CS (out)",
    14: "GPIO14 / SPI1 SCLK (out)",
    15: "GPIO15 / SPI1 TX (out)",
    16: "GPIO16 / I2C0 SDA",
    17: "GPIO17 / I2C0 SCL",
    25: "GPIO25 (out)",
    26: "GPIO26 (in)",
    27: "GPIO27 (out)",
}
OUTPUT_PINS = {8, 11, 13, 14, 15, 25, 27}
NUM_BOARD_LEDS = 7
BEEP_MS = 80
BEEP_AMPLITUDE = 0.05
BUTTONS = ("gray", "yellow", "green", "blue", "red")  # order of the firmware's button report
# The firmware's text overlay shows ONE line in a large proportional font. Measured on the real
# screen: 8 digits, 8 lowercase letters or 7 capitals fit ("PROBE RE" was the visible part of
# "PROBE READY"); the rest is cut off, and a newline would end the serial command.
SCREEN_WIDTH = 8.0  # in lowercase-letter widths


def text_width(text: str) -> float:
    """Estimated width of `text` on the device, in lowercase-letter widths."""
    width = 0.0
    for char in text:
        if char in " .,:;!'|il":
            width += 0.5
        elif char in "MW":
            width += 1.5
        elif char.isupper():
            width += 1.07
        elif char in "mw":
            width += 1.3
        else:
            width += 1.0
    return width


def fit_screen(text: str, width: float = SCREEN_WIDTH) -> str:
    """Make `text` a single line and cut it to what the screen can show."""
    line = " ".join(text.split())
    while line and text_width(line) > width:
        line = line[:-1].rstrip()
    return line


STATUS_COLORS: dict[str, tuple[int, int, int]] = {
    "ok": (0, 60, 0),
    "fail": (60, 0, 0),
    "working": (0, 0, 60),
    "warn": (60, 40, 0),
    "off": (0, 0, 0),
}


class ProbeError(RuntimeError):
    pass


class Probe(Protocol):
    def scan_i2c(self) -> list[int]: ...
    def read_i2c(self, address: int, register: int, length: int) -> bytes: ...
    def write_i2c(self, address: int, register: int, data: bytes) -> None: ...
    def read_pins(self) -> dict[int, int]: ...
    def set_pin(self, pin: int, state: str) -> None: ...
    def show_text(self, text: str) -> None: ...
    def set_status(self, status: str) -> None: ...
    def beep(self, ok: bool) -> None: ...
    def uart_listen(self, seconds: float) -> bytes: ...
    def read_buttons(self) -> dict[str, bool]: ...
    def close(self) -> None: ...


def _unwrap(result, what: str):
    """Convert an onewili `result.Result` into a value or a ProbeError."""
    if result.is_ok():
        return result.unwrap()
    raise ProbeError(f"{what} failed: {result.unwrap_err()}")


class FreeWiliProbe:
    """The real FREE-WILi 1 over USB (OG firmware, OneWili API)."""

    def __init__(self) -> None:
        try:
            import onewili
        except ImportError as ex:  # pragma: no cover - depends on local install
            raise ProbeError("The `onewili` package is not installed. Run: pip install -r requirements.txt") from ex
        try:
            # PROBE_SERIAL picks one unit when two are plugged in (e.g. the stand-in sensor rig).
            self._dev = onewili.connect(serial=os.environ.get("PROBE_SERIAL") or None)
        except Exception as ex:  # RuntimeError (not found) or serial.SerialException (port busy)
            raise ProbeError(
                f"No FREE-WILi found over USB ({ex}). Is it plugged in, powered on, "
                "and not open in another program (serial monitor, App Explorer, another script)?"
            ) from ex
        self._transport = self._dev._transport

    def _raw(self, command: str, what: str) -> str:
        """Send a menu command and return the response text.

        Used where the generated onewili binding drops the arguments or the reply
        (`i2c_read()` takes no address, `i2c_poll()` returns None).
        """
        self._transport.flush_queues()
        self._transport.send(command)
        frame = self._transport.wait_frame()
        if frame is None:
            raise ProbeError(f"{what} failed: no reply from the FREE-WILi")
        if not frame.success:
            raise ProbeError(f"{what} failed: {frame.response or 'no ACK'}")
        return frame.response

    def firmware(self) -> str:
        return self._raw("?", "Reading the firmware version")

    def scan_i2c(self) -> list[int]:
        # Reply is hex bytes: a count, then one byte per address that answered.
        found = [int(token, 16) for token in self._raw("i\\i\\p", "I2C scan").split()]
        return sorted(found[1:])

    def read_i2c(self, address: int, register: int, length: int) -> bytes:
        reply = self._raw(f"i\\i\\r {address:02X} {register:02X} {length}", f"I2C read 0x{address:02X}")
        return bytes(int(token, 16) for token in reply.split())

    def write_i2c(self, address: int, register: int, data: bytes) -> None:
        _unwrap(self._dev.io.i2c.i2c_write(address, register, data), f"I2C write 0x{address:02X}")

    def read_pins(self) -> dict[int, int]:
        bitfield = _unwrap(self._dev.io.gpio.read_all(), "Reading pins")
        return {pin: (bitfield >> pin) & 1 for pin in HEADER_PINS}

    def set_pin(self, pin: int, state: str) -> None:
        gpio = self._dev.io.gpio
        commands = {"high": gpio.set_io_high, "low": gpio.set_io_low, "toggle": gpio.set_io_toggle}
        if state not in commands:
            raise ProbeError(f"state must be one of {sorted(commands)}")
        _unwrap(commands[state](pin), f"Setting GPIO{pin} {state}")

    def show_text(self, text: str) -> None:
        _unwrap(self._dev.gui.show_text(fit_screen(text)), "Showing text on the display")

    def read_buttons(self) -> dict[str, bool]:
        states = self._raw("g\\u", "Reading buttons").split()
        return {name: state == "1" for name, state in zip(BUTTONS, states)}

    def set_status(self, status: str) -> None:
        r, g, b = STATUS_COLORS.get(status, STATUS_COLORS["off"])
        for led in range(NUM_BOARD_LEDS):
            _unwrap(self._dev.gui.set_led_color(led, r, g, b, 0, 0), "Setting LEDs")

    def beep(self, ok: bool) -> None:
        # Deliberately a short, quiet blip: this runs in shared rooms and at a judging table.
        freq = 1320 if ok else 440
        _unwrap(self._dev.io.audio.tone(freq, BEEP_MS, BEEP_AMPLITUDE), "Playing a tone")

    def uart_write(self, data: bytes) -> None:
        _unwrap(self._dev.io.uart.u_art_write(data), "UART write")

    def uart_listen(self, seconds: float) -> bytes:
        """Capture whatever arrives on UART1 RX (GPIO9) for `seconds`. Experimental."""
        received = bytearray()
        events = self._transport.events
        # "Enable UART Read Events" is a toggle; received bytes arrive as [*uart1 ...] event frames.
        _unwrap(self._dev.io.uart.toggle_stream(), "Enabling UART events")
        try:
            end = time.monotonic() + seconds
            while (remaining := end - time.monotonic()) > 0:
                try:
                    frame = events.get(timeout=min(remaining, 0.05))
                except queue.Empty:
                    continue
                if frame.path == "*uart1":
                    received.extend(int(token, 16) for token in frame.response.split())
        finally:
            self._dev.io.uart.toggle_stream()
        return bytes(received)

    def close(self) -> None:
        self._dev.close()


class MockProbe:
    """A fake FREE-WILi for building/testing without hardware.

    Scenarios (PROBE_MOCK_SCENARIO):
      ok             ADXL345 at 0x53 answers correctly
      wrong_address  a PCF8574A LCD backpack at 0x3F (user's code usually says 0x27)
      empty          nothing answers (unpowered sensor, SDA/SCL swapped, missing pull-ups)
      stuck_bus      every address "answers" (SDA shorted low / floating bus)
      grove_lcd      MLH Grove LCD RGB Backlight: text at 0x3E + backlight at 0x62
      grove_baro     MLH Grove Temperature and Barometer (BMP280) at 0x77
      freewili_kit   the parts actually in hand: BMM350 (DFRobot SEN0622) at 0x14 + SHT40 at 0x44
    """

    def __init__(self, scenario: str | None = None) -> None:
        self.scenario = scenario or os.environ.get("PROBE_MOCK_SCENARIO", "ok")
        self.display = ""
        self.status = "off"
        self.pins = {pin: 0 for pin in HEADER_PINS}
        self.pins[16] = self.pins[17] = 0 if self.scenario == "stuck_bus" else 1
        self.registers: dict[int, dict[int, int]] = {
            "ok": {0x53: {0x00: 0xE5, 0x2D: 0x08, 0x32: 0x10, 0x33: 0x00, 0x34: 0xF0, 0x35: 0xFF, 0x36: 0x00, 0x37: 0x01}},
            "wrong_address": {0x3F: {}},
            "empty": {},
            "stuck_bus": {a: {} for a in range(0x08, 0x78)},
            "grove_lcd": {0x3E: {}, 0x62: {}},
            "grove_baro": {0x77: {0xD0: 0x58}},
            # BMM350 I2C reads return 2 dummy bytes first, so CHIP_ID (0x33) arrives as the 3rd byte.
            "freewili_kit": {0x14: {0x00: 0x00, 0x01: 0x00, 0x02: 0x33}, 0x44: {}},
        }.get(self.scenario, {})

    def scan_i2c(self) -> list[int]:
        return sorted(self.registers)

    def read_i2c(self, address: int, register: int, length: int) -> bytes:
        if address not in self.registers:
            raise ProbeError(f"I2C read 0x{address:02X} failed: no ACK")
        regs = self.registers[address]
        return bytes(regs.get(register + i, 0x00) for i in range(length))

    def write_i2c(self, address: int, register: int, data: bytes) -> None:
        if address not in self.registers:
            raise ProbeError(f"I2C write 0x{address:02X} failed: no ACK")
        for i, byte in enumerate(data):
            self.registers[address][register + i] = byte

    def read_pins(self) -> dict[int, int]:
        return dict(self.pins)

    def set_pin(self, pin: int, state: str) -> None:
        if state not in ("high", "low", "toggle"):
            raise ProbeError("state must be one of ['high', 'low', 'toggle']")
        self.pins[pin] = {"high": 1, "low": 0}.get(state, 1 - self.pins[pin])

    def show_text(self, text: str) -> None:
        self.display = fit_screen(text)

    def read_buttons(self) -> dict[str, bool]:
        return dict.fromkeys(BUTTONS, False)

    def set_status(self, status: str) -> None:
        self.status = status

    def beep(self, ok: bool) -> None:
        pass

    def uart_listen(self, seconds: float) -> bytes:
        return b"Sensor init failed!\r\n" if self.scenario != "ok" else b"accel x=12 y=-3 z=256\r\n"

    def close(self) -> None:
        pass


def open_probe() -> Probe:
    """Real device by default; set PROBE_MOCK=1 to use the fake one."""
    if os.environ.get("PROBE_MOCK", "").lower() in ("1", "true", "yes"):
        return MockProbe()
    return FreeWiliProbe()
