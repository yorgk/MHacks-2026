# Probe: an AI lab partner wired into your circuit

MHacks 2026 · FREE-WILi track · built solo.

When a student's breadboard doesn't work, chatbots guess because they can't see the hardware.
Probe plugs a **FREE-WILi** into the circuit, **measures** it (I2C bus scan, chip ID registers,
pin states, serial output), and explains what's wrong in plain English. It separates
"your wiring is wrong" from "your code is wrong". The verdict appears on the FREE-WILi's screen with
green/red LEDs.

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # add GEMINI_API_KEY
python scripts/smoke_test.py                          # check the hardware first
python -m probe.agent --code demo/sketch.ino          # chat with Probe
python -m probe.agent --no-ai --expect 0x27           # offline report, no API key
PROBE_MOCK=1 python -m probe.agent --no-ai            # no hardware at all
python -m pytest -q tests
```

## How it works
`probe/hw.py` talks to the FREE-WILi (or a mock), `probe/diagnose.py` turns raw measurements
into findings, and `probe/agent.py` gives those findings to Gemini as tools, so every answer is
grounded in something that was actually measured.

See `CLAUDE.md` and `docs/` for the full plan, research and pitch.
