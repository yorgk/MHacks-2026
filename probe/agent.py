"""The AI lab partner: a Gemini chat whose tools are real measurements from the FREE-WILi.

Run (from the freewili-probe folder):
    python -m probe.agent                      # chat, typed
    python -m probe.agent --code path/to/sketch.ino   # also let it read your code
    python -m probe.agent --no-ai --expect 0x27       # offline report, no API key needed
    PROBE_MOCK=1 python -m probe.agent         # no hardware: fake FREE-WILi

Note: no `from __future__ import annotations` here on purpose. google-genai builds the
tool schemas from the real type hints of the functions below.
"""

import argparse
import functools
import json
import os
import pathlib
import re
import sys
import time

from . import diagnose
from .hw import HEADER_PINS, OUTPUT_PINS, Probe, ProbeError, open_probe

SYSTEM_PROMPT = """\
You are Probe, a patient lab partner for students debugging electronics on a breadboard.
You are physically wired into the user's circuit through a FREE-WILi test tool, so you can
MEASURE instead of guessing. Rules:
- Before answering any "why doesn't my circuit work" question, call your tools and base the
  answer on what you measured. Say what you measured ("I scanned the I2C bus and found...").
- Separate hardware problems (wiring, power, pull-ups, address pins) from code problems
  (wrong address, wrong register). That split is the most useful thing you do.
- Be efficient: if the user shared code, first call read_user_code, then call run_full_checkup
  once with the address from that code. That single checkup usually gives you everything.
  Only use the smaller tools for follow-up questions.
- A chip that differs from what the code assumes (wrong part, wrong ID register, wrong library)
  is a code problem even when the address is fixed: say so.
- If connection_stability is "intermittent", the problem is a loose wire or unsoldered pin, not
  the code: say how often the device answered.
- Give ONE most likely fix first, as a concrete action ("move the yellow wire from row 12 to
  row 14", "change 0x27 to 0x3F on line 8"), then a short list of other things to check.
- Keep answers short and friendly: a beginner at 2 a.m. is reading this.
- When you reach a verdict, call show_result so the FREE-WILi screen and LEDs show it, then
  ALWAYS write the explanation to the user as text. Never end a turn with only a tool call.
- Never invent measurements. If a tool fails, say so and suggest the physical check.
FREE-WILi wiring facts: I2C SDA = GPIO16, SCL = GPIO17. UART1 TX = GPIO8, RX = GPIO9.
"""


def build_tools(probe: Probe, code_paths: list[pathlib.Path], verbose: bool = True) -> list:
    """Create the functions the model may call. Each returns a JSON-serialisable dict."""

    def traced(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if verbose:
                shown = ", ".join([*map(repr, args), *(f"{k}={v!r}" for k, v in kwargs.items())])
                print(f"  [probe] {fn.__name__}({shown})", flush=True)
            try:
                return fn(*args, **kwargs)
            except (ProbeError, ValueError) as ex:
                return {"error": str(ex)}

        return wrapper

    @traced
    def run_full_checkup(code_address: str) -> dict:
        """START HERE. One call that measures everything: header pin levels, an I2C bus scan,
        the chip-ID check for every device found, a repeated scan to catch loose connections,
        and (if code_address is given) a comparison with the address the user's code uses.
        code_address: the I2C address from the user's code like "0x27", or "" if unknown."""
        probe.set_status("working")
        expected = diagnose.parse_int(code_address) if code_address.strip() else None
        report = diagnose.full_report(probe, expected)
        report["connection_stability"] = diagnose.stability(probe, scans=12, interval=0.2)
        return report

    @traced
    def scan_i2c_bus() -> dict:
        """Scan the I2C bus (SDA=GPIO16, SCL=GPIO17) and list every device address that answers,
        with likely part names. Use this first for any sensor/display that is not responding."""
        probe.set_status("working")
        return diagnose.scan(probe)

    @traced
    def identify_i2c_device(address: str) -> dict:
        """Confirm which chip is at an I2C address by reading its ID (WHO_AM_I) register.
        address: 7-bit address like "0x53"."""
        return diagnose.identify(probe, diagnose.parse_int(address))

    @traced
    def check_code_address(expected_address: str) -> dict:
        """Compare the I2C address the user's code uses (e.g. "0x27") with what is really on the bus."""
        return diagnose.check_expected_address(probe, diagnose.parse_int(expected_address))

    @traced
    def check_connection_stability() -> dict:
        """Scan the bus 20 times and report how often each device answered. Use this when a device
        shows up only sometimes, or the user says it "works on and off": an intermittent result
        means a loose wire or unsoldered pin, not a code problem."""
        return diagnose.stability(probe)

    @traced
    def read_i2c_register(address: str, register: str, length: int) -> dict:
        """Read `length` bytes (1-32) starting at `register` from the device at `address`.
        Example: address "0x53", register "0x32", length 6 reads ADXL345 acceleration."""
        length = max(1, min(int(length), 32))
        data = probe.read_i2c(diagnose.parse_int(address), diagnose.parse_int(register), length)
        return {"address": address, "register": register, "bytes": [f"0x{b:02X}" for b in data]}

    @traced
    def write_i2c_register(address: str, register: str, data_hex: str) -> dict:
        """Write bytes to a device register, e.g. to wake a sensor up. data_hex like "08" or "08 00".
        Only use this when the user agrees or when a datasheet step clearly requires it."""
        payload = bytes.fromhex(data_hex.replace("0x", "").replace(",", " "))
        probe.write_i2c(diagnose.parse_int(address), diagnose.parse_int(register), payload)
        return {"written": data_hex, "address": address, "register": register}

    @traced
    def read_header_pins() -> dict:
        """Read HIGH/LOW on every FREE-WILi header pin. Idle I2C lines (GPIO16/17) should read HIGH."""
        return diagnose.pins(probe)

    @traced
    def set_header_pin(pin: int, state: str) -> dict:
        """Drive an output pin "high", "low" or "toggle" (e.g. to test an LED or a relay input).
        Output-capable pins: 8, 11, 13, 14, 15, 25, 27."""
        if pin not in OUTPUT_PINS:
            return {"error": f"GPIO{pin} is not an output pin. Outputs: {sorted(OUTPUT_PINS)}"}
        probe.set_pin(pin, state)
        return {"pin": HEADER_PINS[pin], "state": state}

    @traced
    def listen_uart(seconds: float) -> dict:
        """Capture serial text the user's microcontroller sends to FREE-WILi UART1 RX (GPIO9)
        for a few seconds (max 10). Useful when the board prints error messages."""
        raw = probe.uart_listen(max(0.5, min(float(seconds), 10.0)))
        return {"text": raw.decode("utf-8", errors="replace"), "byte_count": len(raw)}

    @traced
    def read_user_code(file_name: str) -> dict:
        """Read one of the user's source files that they shared with you (Arduino sketch, Python, C)."""
        for path in code_paths:
            if path.name == file_name or str(path) == file_name:
                lines = path.read_text(errors="replace")[:20000].splitlines()
                numbered = "\n".join(f"{n}: {line}" for n, line in enumerate(lines, 1))
                return {"file": path.name, "content_with_line_numbers": numbered}
        return {"error": f"Not shared. Available files: {[p.name for p in code_paths]}"}

    @traced
    def show_result(headline: str, status: str) -> dict:
        """Show the verdict on the FREE-WILi: headline (max ~60 chars) on screen, LEDs by status
        ("ok" = green, "fail" = red, "warn" = yellow), plus a beep."""
        probe.show_text(headline[:60])
        probe.set_status(status if status in ("ok", "fail", "warn") else "warn")
        probe.beep(status == "ok")
        return {"shown": headline[:60], "status": status}

    tools = [
        run_full_checkup,
        scan_i2c_bus,
        identify_i2c_device,
        check_code_address,
        check_connection_stability,
        read_i2c_register,
        write_i2c_register,
        read_header_pins,
        set_header_pin,
        listen_uart,
        show_result,
    ]
    if code_paths:
        tools.append(read_user_code)
    return tools


def _send(chat, message: str, retries: int = 2):
    """Send a message, waiting out free-tier rate limits (HTTP 429) instead of crashing."""
    for attempt in range(retries + 1):
        try:
            return chat.send_message(message)
        except Exception as ex:  # noqa: BLE001 - google-genai raises ClientError for 429
            found = re.search(r"retry in ([\d.]+)s", str(ex))
            if getattr(ex, "code", None) != 429 or attempt == retries or not found:
                raise
            wait = min(float(found.group(1)) + 1, 60)
            print(f"  [probe] AI rate limit reached, waiting {wait:.0f} s...", flush=True)
            time.sleep(wait)


def run_chat(probe: Probe, code_paths: list[pathlib.Path]) -> None:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.exit("google-genai is not installed. Run: pip install -r requirements.txt")

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        sys.exit("Set GEMINI_API_KEY (see .env.example), or run with --no-ai for the offline report.")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

    client = genai.Client(api_key=api_key)
    system = SYSTEM_PROMPT
    if code_paths:
        system += f"\nThe user shared these files you can read with read_user_code: {[p.name for p in code_paths]}\n"
    chat = client.chats.create(
        model=model,
        config=types.GenerateContentConfig(
            system_instruction=system,
            tools=build_tools(probe, code_paths),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(maximum_remote_calls=15),
        ),
    )
    print(f"Probe is listening (model: {model}). Describe your problem. Ctrl+C to quit.\n")
    while True:
        try:
            question = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not question:
            continue
        try:
            response = _send(chat, question)
            if not response.text:  # the model sometimes stops right after its last tool call
                response = _send(chat, "Now explain what you measured and the fix, in plain English.")
        except Exception as ex:  # noqa: BLE001 - keep the chat alive; the offline report still works
            print(f"\nprobe> The AI service failed ({type(ex).__name__}: {str(ex)[:200]}).")
            print("       Run with --no-ai for the measured report.\n")
            continue
        print(f"\nprobe> {response.text or '(no answer from the model; run with --no-ai for the raw report)'}\n")


def run_offline(probe: Probe, expected: str | None) -> None:
    report = diagnose.full_report(probe, diagnose.parse_int(expected) if expected else None)
    status = diagnose.overall_status(report)
    print(json.dumps(report, indent=2))
    headline = {"ok": "All checks passed", "warn": "Works, but check warnings", "fail": "Problem found - see laptop"}[status]
    probe.show_text(headline)
    probe.set_status(status)
    probe.beep(status == "ok")
    print(f"\nOverall: {status.upper()}  ({headline})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe: an AI lab partner wired into your circuit.")
    parser.add_argument("--code", nargs="*", default=[], help="source files the AI may read")
    parser.add_argument("--no-ai", action="store_true", help="offline diagnostic report, no API key")
    parser.add_argument("--expect", help="I2C address your code uses, e.g. 0x27 (offline mode)")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    code_paths = [pathlib.Path(p).expanduser().resolve() for p in args.code]
    missing = [str(p) for p in code_paths if not p.is_file()]
    if missing:
        sys.exit(f"Code file(s) not found: {missing}")

    try:
        probe = open_probe()
    except ProbeError as ex:
        sys.exit(str(ex))
    try:
        if args.no_ai:
            run_offline(probe, args.expect)
        else:
            run_chat(probe, code_paths)
    finally:
        probe.close()


if __name__ == "__main__":
    main()
