"""Hardware layer: everything that touches the FREE-WILi lives here.

Two implementations with the same interface:
  - FreeWiliProbe: the real device over USB (pip package `freewili`)
  - MockProbe:     a fake device so the agent/tests run without hardware (PROBE_MOCK=1)

Every method returns plain Python data (or raises ProbeError) so the agent layer never
has to know about the freewili library's Result types.
"""

from __future__ import annotations

import os
import time
from typing import Protocol

# Header pins exposed on the FREE-WILi 1 connector (from freewili.types.GPIO_MAP).
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
    def close(self) -> None: ...


def _unwrap(result, what: str):
    """Convert a freewili `result.Result` into a value or a ProbeError."""
    if result.is_ok():
        return result.unwrap()
    raise ProbeError(f"{what} failed: {result.unwrap_err()}")


class FreeWiliProbe:
    """The real FREE-WILi 1 over USB."""

    def __init__(self) -> None:
        try:
            from freewili import FreeWili
        except ImportError as ex:  # pragma: no cover - depends on local install
            raise ProbeError("The `freewili` package is not installed. Run: pip install -r requirements.txt") from ex
        found = FreeWili.find_first()
        if found.is_err():
            raise ProbeError(
                f"No FREE-WILi found over USB ({found.unwrap_err()}). Is it plugged in, powered on, "
                "and not open in another program (serial monitor, another script)?"
            )
        self._fw = found.unwrap()
        _unwrap(self._fw.open(), "Opening the FREE-WILi")

    def scan_i2c(self) -> list[int]:
        return sorted(int(a) for a in _unwrap(self._fw.poll_i2c(), "I2C scan"))

    def read_i2c(self, address: int, register: int, length: int) -> bytes:
        return bytes(_unwrap(self._fw.read_i2c(address, register, length), f"I2C read 0x{address:02X}"))

    def write_i2c(self, address: int, register: int, data: bytes) -> None:
        _unwrap(self._fw.write_i2c(address, register, data), f"I2C write 0x{address:02X}")

    def read_pins(self) -> dict[int, int]:
        values = _unwrap(self._fw.get_io(), "Reading pins")
        return {pin: values[pin] for pin in HEADER_PINS}

    def set_pin(self, pin: int, state: str) -> None:
        from freewili.types import IOMenuCommand

        commands = {"high": IOMenuCommand.High, "low": IOMenuCommand.Low, "toggle": IOMenuCommand.Toggle}
        if state not in commands:
            raise ProbeError(f"state must be one of {sorted(commands)}")
        _unwrap(self._fw.set_io(pin, commands[state]), f"Setting GPIO{pin} {state}")

    def show_text(self, text: str) -> None:
        _unwrap(self._fw.show_text_display(text), "Showing text on the display")

    def set_status(self, status: str) -> None:
        r, g, b = STATUS_COLORS.get(status, STATUS_COLORS["off"])
        for led in range(NUM_BOARD_LEDS):
            _unwrap(self._fw.set_board_leds(led, r, g, b), "Setting LEDs")

    def beep(self, ok: bool) -> None:
        freq = 1320 if ok else 220
        _unwrap(self._fw.play_audio_tone(freq, 0.2, 0.5), "Playing a tone")

    def uart_listen(self, seconds: float) -> bytes:
        """Capture whatever arrives on UART1 RX (GPIO9) for `seconds`. Experimental."""
        from freewili.types import UART1Data

        received = bytearray()

        def on_event(_event_type, _frame, data) -> None:
            if isinstance(data, UART1Data):
                received.extend(data.data)

        self._fw.set_event_callback(on_event)
        # Note from the freewili examples: on v54 firmware enable_uart_events is a toggle.
        _unwrap(self._fw.enable_uart_events(True), "Enabling UART events")
        try:
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                self._fw.process_events()
                time.sleep(0.05)
        finally:
            self._fw.enable_uart_events(False)
            self._fw.set_event_callback(None)
        return bytes(received)

    def close(self) -> None:
        self._fw.close()


class MockProbe:
    """A fake FREE-WILi for building/testing without hardware.

    Scenarios (PROBE_MOCK_SCENARIO):
      ok             ADXL345 at 0x53 answers correctly
      wrong_address  a PCF8574A LCD backpack at 0x3F (user's code usually says 0x27)
      empty          nothing answers (unpowered sensor, SDA/SCL swapped, missing pull-ups)
      stuck_bus      every address "answers" (SDA shorted low / floating bus)
      grove_lcd      MLH Grove LCD RGB Backlight: text at 0x3E + backlight at 0x62
      grove_baro     MLH Grove Temperature and Barometer (BMP280) at 0x77
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
        self.display = text

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
