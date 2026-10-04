"""Runs without hardware or API keys: PROBE_MOCK scenarios through the diagnostics + tools."""

import pathlib

import pytest

from probe import diagnose
from probe.agent import build_tools
from probe.hw import MockProbe


def test_ok_scenario_identifies_adxl345():
    probe = MockProbe("ok")
    report = diagnose.full_report(probe)
    assert report["scan"]["addresses_found"] == ["0x53"]
    assert report["identify"][0]["identified_as"] == "ADXL345"
    assert diagnose.overall_status(report) == "ok"


def test_wrong_address_gives_pcf8574_hint():
    probe = MockProbe("wrong_address")
    check = diagnose.check_expected_address(probe, 0x27)
    assert check["verdict"] == "mismatch"
    assert check["addresses_found"] == ["0x3F"]
    assert "PCF8574" in check["hint"]


def test_empty_bus_lists_causes():
    report = diagnose.full_report(MockProbe("empty"), expected_address=0x53)
    assert report["scan"]["verdict"] == "nothing_answered"
    assert any("SDA and SCL" in c for c in report["scan"]["likely_causes"])
    assert diagnose.overall_status(report) == "fail"


def test_stuck_bus_detected():
    report = diagnose.full_report(MockProbe("stuck_bus"))
    assert report["scan"]["verdict"] == "bus_fault"
    assert report["pins"]["warnings"]


@pytest.mark.parametrize("text,value", [("0x3F", 0x3F), ("3F", 0x3F), ("63", 63), (0x27, 0x27)])
def test_parse_int(text, value):
    assert diagnose.parse_int(text) == value


def test_tools_run_against_mock(tmp_path: pathlib.Path):
    sketch = tmp_path / "sketch.ino"
    sketch.write_text("LiquidCrystal_I2C lcd(0x27, 16, 2);")
    probe = MockProbe("wrong_address")
    tools = {t.__name__: t for t in build_tools(probe, [sketch], verbose=False)}
    assert tools["scan_i2c_bus"]()["addresses_found"] == ["0x3F"]
    assert "0x27" in tools["read_user_code"]("sketch.ino")["content_with_line_numbers"]
    assert tools["check_code_address"]("0x27")["verdict"] == "mismatch"
    assert "error" in tools["read_i2c_register"]("0x27", "0x00", 1)  # no device there
    assert "error" in tools["set_header_pin"](16, "high")  # SDA is not an output
    shown = tools["show_result"]("Use 0x3F, not 0x27", "fail")
    assert shown["status"] == "fail" and probe.status == "fail"


def test_grove_lcd_copy_paste_bug():
    """Student copied a generic LiquidCrystal_I2C tutorial (0x27) but rented a Grove LCD (0x3E)."""
    check = diagnose.check_expected_address(MockProbe("grove_lcd"), 0x27)
    assert check["verdict"] == "mismatch"
    assert check["addresses_found"] == ["0x3E", "0x62"]
    assert "rgb_lcd" in check["hint"]


def test_grove_baro_identified_as_bmp280():
    report = diagnose.full_report(MockProbe("grove_baro"))
    assert report["identify"][0]["identified_as"] == "BMP280"


def test_freewili_kit_identifies_bmm350_through_dummy_bytes():
    report = diagnose.full_report(MockProbe("freewili_kit"))
    assert report["scan"]["addresses_found"] == ["0x14", "0x44"]
    bmm = report["identify"][0]
    assert bmm["identified_as"] == "BMM350"
    assert any("SHT40" in c for c in report["identify"][1]["candidates"])


def test_bmm150_tutorial_bug():
    """Student copied a BMM150 tutorial (0x13) but has a BMM350 at 0x14."""
    check = diagnose.check_expected_address(MockProbe("freewili_kit"), 0x13)
    assert check["verdict"] == "mismatch"
    assert "BMM350" in check["hint"]


class FlakyProbe(MockProbe):
    """Answers only on some scans, like a sensor with an unsoldered pin."""

    def __init__(self, pattern: list[bool]) -> None:
        super().__init__("freewili_kit")
        self._pattern = iter(pattern)

    def scan_i2c(self) -> list[int]:
        return [0x14] if next(self._pattern) else []


def test_stability_stable_device():
    result = diagnose.stability(MockProbe("freewili_kit"), scans=10, interval=0)
    assert result["verdict"] == "stable"
    assert result["answered"] == {"0x14": "10 of 10", "0x44": "10 of 10"}


def test_stability_flags_loose_connection():
    result = diagnose.stability(FlakyProbe([True, False, False, True, False] * 4), scans=20, interval=0)
    assert result["verdict"] == "intermittent"
    assert result["answered"] == {"0x14": "8 of 20"}
    assert "loose" in result["likely_causes"][0].lower()


def test_stability_nothing_answered():
    assert diagnose.stability(MockProbe("empty"), scans=5, interval=0)["verdict"] == "nothing_answered"


def test_headlines_for_the_three_demo_bugs():
    from probe.hw import SCREEN_WIDTH, text_width

    def checkup(probe, expected):
        report = diagnose.full_report(probe, expected)
        report["connection_stability"] = diagnose.stability(probe, scans=6, interval=0)
        return diagnose.headline(report)

    results = {
        "code": checkup(MockProbe("freewili_kit"), 0x13),
        "wiring": checkup(MockProbe("empty"), 0x13),
        # full_report scans a few times before the stability check starts
        "loose": checkup(FlakyProbe([True] * 3 + [True, False] * 3), None),
        "good": checkup(MockProbe("freewili_kit"), 0x14),
        "stuck": checkup(MockProbe("stuck_bus"), None),
    }
    status, pages = results["code"]
    assert status == "fail" and pages[0] == "CODE BUG"
    assert pages[1:4] == ["wire ok", "BMM350", "at 0x14"] and pages[-3:] == ["code has", "0x13", "use 0x14"]
    assert results["wiring"][1][:2] == ["WIRING", "BUG"]
    assert results["loose"][0] == "warn" and results["loose"][1][:2] == ["LOOSE", "WIRE"]
    assert results["good"][0] == "ok" and results["good"][1][0] == "ALL GOOD"
    assert results["stuck"][1][:2] == ["BUS", "FAULT"]
    for status, pages in results.values():  # every page must fit the measured screen width
        assert all(text_width(page) <= SCREEN_WIDTH for page in pages), pages


def test_address_from_code_and_screen_fit():
    from probe.agent import READY_PAGES
    from probe.hw import SCREEN_WIDTH, fit_screen, text_width

    sketch = pathlib.Path("demo/bmm350_sketch.ino").read_text()
    assert diagnose.address_from_code(sketch) == 0x13
    assert diagnose.address_from_code("int x = 5;") is None
    # measured on the device: these fit ...
    for fits in ("PROBE RE", "abcdefgh", "01234567", "ABCDEFG", "CODE BUG", "ALL GOOD", *READY_PAGES):
        assert fit_screen(fits) == fits, fits
    # ... and these were cut off
    assert fit_screen("PROBE READY") == "PROBE RE"
    assert fit_screen("ABCDEFGHIJ") == "ABCDEFG"
    assert text_width(fit_screen("Wrong chip & address: BMM350 at 0x14")) <= SCREEN_WIDTH
    assert chr(10) not in fit_screen("two" + chr(10) + "lines")
