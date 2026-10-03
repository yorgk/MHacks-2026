# CLAUDE.md: MHacks 2026, "Probe" (FREE-WILi AI lab partner)

This file is the full hand-off from the planning session (a cloud Claude session that could
not reach the hardware). You are now running **on the user's laptop with the FREE-WILi plugged
in**, so you can run the hardware scripts directly. Read this whole file plus the two imported
docs before doing anything.

@docs/PLAN.md
@docs/RESEARCH.md

## Who you're helping and how
- Solo hacker at **MHacks 2026** (University of Michigan, Ann Arbor). Use they/them for the user.
- Their words: "my goal is to win something, not be the best. I know I'm not cracked."
  So: target **less-competitive prizes**, keep scope small, explain things simply.
- They asked to be told the truth: **be brutally honest, don't automatically side with them.**
  Push back on scope creep and on ideas that already exist.
- Their teammates are building a separate project (predictive trash pickup around Ann Arbor
  events) in `jaydenhuang9/mhacks`. Don't touch that repo.

## Hard deadlines (Eastern time)
| When | What |
|---|---|
| Sat Oct 3, 8:00 PM | **Duderstadt Center doors lock.** If they leave (e.g. to get parts), get back before 8 or arrange re-entry. |
| Sun Oct 4, 9:00 AM | Feature freeze. Record the backup demo video. |
| Sun Oct 4, **12:00 PM** | **Devpost submission deadline. No late submissions, no exceptions.** |
| Sun Oct 4, 12:30-2:30 PM | Judging at the Duderstadt: 3-minute pitch + Q&A, possibly several judges. **Must be present** to be judged for any track. |

## The project in one paragraph
**Probe** is an AI lab partner that is physically wired into your breadboard. Today a student
with a broken circuit asks ChatGPT, which can't see the hardware and guesses. Probe uses a
FREE-WILi to **measure** the circuit (scan the I2C bus, read chip ID registers, read pin
states, listen to serial output) and then explains, in plain English, what's wrong and the one
most likely fix. Its most useful trick is separating **"your wiring/hardware is wrong"** from
**"your code is wrong"**, e.g. "your sensor is at 0x3F but your sketch uses 0x27, change line 8".
The verdict also shows on the FREE-WILi screen with green/red LEDs and a beep.

- **User:** an embedded-systems student (e.g. UMich EECS 373) or Arduino hobbyist (~33M active
  Arduino users) debugging alone at 2 a.m. when office hours are closed.
- **Problem statement:** "Embedded students struggle to debug circuits alone because chatbots
  can't see their hardware, which costs them hours and late-night office-hour queues."
- **Prize targets (in order):** Best Use of FREE-WILi (few entrants, multiple winners in past
  years) > Beyond the Code (Hardware) track > cheap add-ons: Notability (use Notability Pro for
  ideation + 2 screenshots), Judged by an LLM / Useless AI / Dumbest Idea side quests, MLH Best
  Use of Gemini (we already use Gemini). Optional stretch: ElevenLabs (voice), Fetch.ai.

## Honest risks (say these out loud when relevant)
1. **"Why not just have Claude Code / an Arduino run an I2C-scanner sketch?"** Partly fair: a
   dev with Claude Code + an ESP32 can flash a scanner and read serial. Our answer: Probe is an
   **independent, known-good instrument**. It works when your board won't boot or your code is
   the thing that's broken, needs no reflashing, sets its own I/O voltage (1.1-5.5V), and is
   aimed at beginners who don't use agentic coding tools. Doctors ask the patient how they feel
   (that's reading your board's serial) but still use a stethoscope (that's Probe).
2. The strongest differentiator, **passively sniffing** the bus between the user's MCU and the
   sensor (logic analyzer via the FPGA), is probably **not reachable from the Python API in
   time**. Don't promise it in the demo; pitch it as "next step".
3. The hardware path is unproven until `scripts/smoke_test.py` passes on the real device.
   **Prove hardware first, then build AI on top.**

## Code map
```
probe/hw.py        FreeWiliProbe (real, via `freewili`) + MockProbe (fake device). Only file that imports freewili.
probe/devices.py   I2C address -> likely parts, ID-register checks, classic address mix-ups (0x27 vs 0x3F etc.)
probe/diagnose.py  Deterministic checks (no AI): scan, identify, expected-address check, pin sanity, full report
probe/agent.py     Gemini chat whose tools wrap diagnose/hw; also `--no-ai` offline report mode (demo fallback)
scripts/smoke_test.py  First-hour hardware check: install, find, firmware, LEDs, display, tone, pins, I2C scan
tests/test_mock.py     9 tests against MockProbe scenarios (no hardware, no API key). All passing at hand-off.
```

### Run it
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # add GEMINI_API_KEY (free key: https://aistudio.google.com/apikey)
python scripts/smoke_test.py                      # FIRST. Real hardware check.
python scripts/smoke_test.py --i2c                # re-scan after wiring a sensor
python -m probe.agent --no-ai --expect 0x27       # offline report on the real device
python -m probe.agent --code path/to/sketch.ino   # AI chat, may read the sketch
PROBE_MOCK=1 PROBE_MOCK_SCENARIO=wrong_address python -m probe.agent   # no hardware
python -m pytest -q tests
```
Mock scenarios: `ok` (ADXL345 at 0x53), `wrong_address` (LCD backpack at 0x3F), `empty`
(nothing answers), `stuck_bus` (every address answers / SDA low).

## FREE-WILi library facts (verified by reading freewili-python 0.0.51 source)
- `FreeWili.find_first()` returns a `result.Result`; use `.expect()`/`.unwrap()`; `fw.open()` / `fw.close()`
  or `with fw:`. Every call returns `Result`, never raises on device errors. `hw._unwrap` converts.
- I2C: `poll_i2c()` -> tuple of found addresses; `read_i2c(addr, reg, n)` -> bytes;
  `write_i2c(addr, reg, data)`. Pins: `get_io()` -> 32 bit values; `set_io(pin, IOMenuCommand.High/Low/Toggle/Pwm, freq, duty)`.
- Header pins (GPIO_MAP): 8 UART1 TX, 9 UART1 RX, 10 CTS, 11 RTS, 12 SPI RX, 13 SPI CS,
  14 SPI SCLK, 15 SPI TX, **16 I2C0 SDA, 17 I2C0 SCL**, 25 out, 26 in, 27 out.
- Display (FREE-WILi 1): only `show_text_display(text)` or `show_gui_image(path.fwi)`. No dynamic UI.
  MHacks 2025 winner "Wattson" composited images with Pillow, converted with `fwi-convert`,
  uploaded with `send_file`, shown with `show_gui_image`. Only do this if core is done.
- LEDs: `set_board_leds(index 0-6, r, g, b)`. Tone: `play_audio_tone(hz, seconds, amplitude)`.
- UART: `enable_uart_events(True)` + `set_event_callback` + `process_events()`; v54 firmware:
  max ~22 bytes per UART write and `enable_uart_events` acts as a toggle.
- CLIs installed with the package: `fwi-serial`, `fwi-convert`.
- **Only one program can hold the serial port.** Close the FREE-WILi GUI / serial monitors.
- Dependency trap: `freewili` pins `typing-extensions==4.12.2`; google-genai >=1.67 crashes on
  import with it, so requirements pin `google-genai<1.67`. Don't "fix" by upgrading.
- Gemini model is `GEMINI_MODEL` (default `gemini-2.5-flash`). If it errors as retired, list
  current models in AI Studio and change the env var.

## Unknowns to verify on the real hardware (ask the user / FREE-WILi table)
- Physical location of GPIO16/17, GND and the VCC/IO-voltage pin on the header (docs:
  https://docs.freewili.com, GPIO page). Male-to-male jumpers fit a female header + breadboard.
- Whether the I/O voltage must be set (3.3V for most breakouts) and whether internal pull-ups exist.
- Firmware version (smoke test step 3). If calls fail oddly, ask the FREE-WILi table to update firmware.

## Working rules for this session
- Commit early and often with clear messages; judges check that code was written during the event.
- Never commit `.env` or API keys.
- After any hardware-facing change, have the user run the smoke test or the agent on the device.
- Keep the demo path working at all times; the `--no-ai` mode is the fallback if Wi-Fi/API dies.
- Scope discipline: no new features after 9 AM Sunday.
