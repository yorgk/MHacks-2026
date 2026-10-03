"""Deterministic diagnostics. No AI here: these are the measurements the agent reasons over,
and they also power the offline `--no-ai` demo mode if the internet or API keys fail.
"""

from __future__ import annotations

from . import devices
from .hw import HEADER_PINS, Probe, ProbeError

I2C_ADDRESS_RANGE = range(0x08, 0x78)  # valid 7-bit addresses


def parse_int(value: str | int) -> int:
    """Accept 0x3F, 3F, 63 or an int."""
    if isinstance(value, int):
        return value
    text = value.strip().lower()
    if text.startswith("0x"):
        return int(text, 16)
    if any(c in "abcdef" for c in text):
        return int(text, 16)
    return int(text, 10)


def hexb(value: int) -> str:
    return f"0x{value:02X}"


def scan(probe: Probe) -> dict:
    """Scan the I2C bus and explain the result."""
    found = probe.scan_i2c()
    result: dict = {"addresses_found": [hexb(a) for a in found], "devices": []}
    if not found:
        result["verdict"] = "nothing_answered"
        result["likely_causes"] = [
            "Sensor has no power or no shared ground with the FREE-WILi (check VCC and GND first).",
            "SDA and SCL are swapped (FREE-WILi SDA = GPIO16, SCL = GPIO17).",
            "Missing pull-up resistors on SDA/SCL (add ~4.7k from each line to VCC if the breakout has none).",
            "FREE-WILi I/O voltage does not match the sensor (3.3V vs 5V).",
            "Loose jumper or wrong breadboard row.",
        ]
        return result
    if len(found) > 40 or set(found) >= set(range(0x08, 0x30)):
        result["verdict"] = "bus_fault"
        result["likely_causes"] = [
            "Almost every address answers, which a real bus never does: SDA is probably shorted to ground, "
            "or the lines are floating without pull-ups.",
        ]
        return result
    result["verdict"] = "devices_found"
    for address in found:
        result["devices"].append({"address": hexb(address), "candidates": devices.candidates_for(address)})
    return result


def identify(probe: Probe, address: int) -> dict:
    """Read known ID registers to confirm which chip is at `address`."""
    checks = devices.ID_CHECKS.get(address, [])
    out: dict = {"address": hexb(address), "candidates": devices.candidates_for(address), "id_checks": []}
    for check in checks:
        try:
            value = probe.read_i2c(address, check.register, check.offset + 1)[check.offset]
        except ProbeError as ex:
            out["id_checks"].append({"part": check.part, "error": str(ex)})
            continue
        match = value == check.expected
        out["id_checks"].append(
            {
                "part": check.part,
                "register": hexb(check.register),
                "read": hexb(value),
                "expected": hexb(check.expected),
                "match": match,
            }
        )
        if match:
            out["identified_as"] = check.part
            break
    if not checks:
        out["note"] = "No ID register known for this address; identification is by address only."
    return out


def check_expected_address(probe: Probe, expected: int) -> dict:
    """Compare the address the user's code uses with what is really on the bus."""
    found = probe.scan_i2c()
    out: dict = {"expected": hexb(expected), "addresses_found": [hexb(a) for a in found]}
    if expected in found:
        out["verdict"] = "match"
        return out
    out["verdict"] = "mismatch" if found else "nothing_answered"
    hints = [h for a in found if (h := devices.mixup_hint(expected, a))]
    if hints:
        out["hint"] = hints[0]
    return out


def pins(probe: Probe) -> dict:
    """Read every header pin and flag suspicious I2C line states."""
    values = probe.read_pins()
    out: dict = {"pins": {HEADER_PINS[p]: ("HIGH" if v else "LOW") for p, v in values.items()}}
    warnings = []
    if values.get(16) == 0:
        warnings.append("SDA (GPIO16) reads LOW while idle. An idle I2C line should be HIGH: check pull-ups or a short.")
    if values.get(17) == 0:
        warnings.append("SCL (GPIO17) reads LOW while idle. An idle I2C line should be HIGH: check pull-ups or a short.")
    if warnings:
        out["warnings"] = warnings
    return out


def full_report(probe: Probe, expected_address: int | None = None) -> dict:
    """Everything at once; used by the offline demo mode."""
    report: dict = {"pins": pins(probe), "scan": scan(probe)}
    if report["scan"]["verdict"] == "devices_found":
        report["identify"] = [identify(probe, parse_int(d["address"])) for d in report["scan"]["devices"]]
    if expected_address is not None:
        report["expected_address_check"] = check_expected_address(probe, expected_address)
    return report


def overall_status(report: dict) -> str:
    """Map a full report to an LED status: ok / warn / fail."""
    if report["scan"]["verdict"] != "devices_found":
        return "fail"
    check = report.get("expected_address_check")
    if check and check["verdict"] != "match":
        return "fail"
    if report["pins"].get("warnings"):
        return "warn"
    return "ok"
