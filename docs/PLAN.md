# Build plan, parts, demo and pitch

Hand-off written Sat Oct 3, ~5:30 PM. About 18 hours to the noon deadline, minus sleep.

## Timeline with go/no-go checkpoints
| By (Sat/Sun) | Done when | If not |
|---|---|---|
| Sat 7:45 PM | ~~Parts in hand~~ **DONE**: BMM350 + SHT40 from the FREE-WILi table. Next: solder (or jury-rig) their header pins. | |
| Sat 8:00 PM | `smoke_test.py` steps 1-7 PASS | Go to the FREE-WILi table with the output (firmware/driver) |
| **Sat 9:30 PM: GO/NO-GO** | Sensor wired and `smoke_test.py --i2c` finds its address | Pivot: drop I2C, demo pins + UART only, or switch to fallback idea (see RESEARCH.md) |
| Sun 12:30 AM | Typed AI chat works end-to-end on the real device (scan, identify, verdict) | Demo the `--no-ai` report instead |
| Sun 2:30 AM | Demo circuit with 2 planted bugs + `show_result` on device screen/LEDs. Then sleep. | |
| Sun 8:00 AM | Stretch (pick at most one): ElevenLabs voice, or Pillow status images on screen | Skip it |
| **Sun 9:00 AM** | **Feature freeze.** Record 60-90 s backup demo video (screen + phone video of device) | |
| Sun 10:30 AM | Devpost draft submitted (can edit until noon) | |
| Sun 11:30 AM | Final Devpost + Notability screenshots + repo link | |
| **Sun 12:00 PM** | **Deadline** | |
| Sun 12:30-2:30 PM | Judging; stay at the table | |

## Parts IN HAND (Sat ~7 PM, from the FREE-WILi sponsor table; MLH desk never came back)
| Part | Bus / address | Notes |
|---|---|---|
| **DFRobot SEN0622: Bosch BMM350 3-axis magnetometer** (Fermion board) | I2C **0x14** (ADSEL low, default) or 0x15 | CHIP_ID register 0x00 = **0x33**, but BMM350 I2C reads start with **2 dummy bytes** (Probe handles this: `IdCheck(offset=2)`). Use **3.3V**. |
| **SHT40 temp/humidity breakout** | I2C **0x44** | Command-based chip (no registers). Probe identifies it by address. Reading real temperature needs "write 0xFD, wait ~10 ms, read 6 bytes", which `read_i2c(addr, reg, n)` probably can't do (no delay between write and read); treat as an experiment, not a demo dependency. 3.3V is safe. |
| Female-to-female + female-to-male jumpers (+ the user's male-to-male) | | Enough to wire both sensors straight to the FREE-WILi header without a breadboard. |
| ST X-NUCLEO-NFC08A1 (ST25R3916B NFC reader board) | **SPI by default** (I2C needs hardware mods), Arduino Uno R3 / Nucleo connector | **Skip tonight.** Different bus, complex chip init, meant to stack on an STM32 Nucleo. At most a "next step: SPI support" slide. |

**Header pins are NOT soldered** on the two sensor boards ("solder kind" pins). Loose pins make
flaky contacts, which is the worst thing for a live demo. Fix, in order:
1. Ask the FREE-WILi table for a soldering iron (they handed out unsoldered parts; they or
   MHacks/MLH staff likely have one). 4 pins per board, ~5 minutes.
2. No iron: push the header pins through the board holes and put the female jumper ends on
   them, angled so the pins press against the hole walls; tape it down. OK for testing, risky on stage.
**Both sensors can share the bus:** SDA to SDA, SCL to SCL, VCC to VCC, GND to GND. A scan should
show 0x14 and 0x44. That's a nicer demo than one device.

**Demo bug for this hardware:** `demo/bmm350_sketch.ino`. A student followed a BMM150 compass
tutorial (address 0x13, chip-ID register 0x40), but the board is a BMM350 at 0x14 (CHIP_ID
register 0x00 = 0x33, needs the DFRobot_BMM350 library). Probe should catch the wrong address
**and** the wrong chip. Mock: `PROBE_MOCK_SCENARIO=freewili_kit`.

## Original parts list (written before we knew what was available)
| Item | Why | Have? |
|---|---|---|
| FREE-WILi 1 + USB data cable | The instrument | Yes |
| Male-to-male jumpers | Breadboard <-> FREE-WILi header (works if the FREE-WILi header is female; if it has male pins you need female-to-male) | Yes |
| Breadboard | Demo circuit | Need |
| 1-2 I2C sensors/displays | The "broken" circuit. Best: a 16x2 LCD with I2C backpack (classic 0x27 vs 0x3F bug), BME280, MPU-6050, ADXL345, or SparkFun 9DoF (freewili has an example for it) | Need |
| 2x 4.7 kΩ resistors (2.2k-10k OK) | I2C pull-ups (many breakouts have them built in) | Need |
| Optional: LED + 220 Ω | Pin-driving demo | Optional |
| Optional: Grove-to-jumper cable | Only if the sensor is a Grove module | If Grove |
| Not needed | WILEye camera, Bottlenose, Maestro, antennas, whale tail badge | Leave in bag |

### MLH Hardware Lab menu (NOT obtained: desk was unstaffed; kept for reference)
All MLH modules are **Grove** (4-pin plug: black GND, red VCC, white SDA, yellow SCL). Most
Grove I2C boards already have pull-up resistors, so the 4.7k resistors are probably not needed.
| Rent | Bus / address | Why |
|---|---|---|
| **LCD RGB Backlight** (top pick) | I2C, 0x3E (text) + 0x62 or 0x30 (backlight) | Visible output, two addresses on one board, and a very realistic bug: students copy a generic `LiquidCrystal_I2C` 0x27 tutorial, but Grove needs `rgb_lcd` at 0x3E. Demo: `demo/grove_lcd_sketch.ino`. Some versions want 5V. |
| **Temperature and Barometer Sensor** | I2C, BMP280 at 0x77 (ID reg 0xD0 = 0x58) | Has an ID register, so `identify` can prove which chip it is |
| Optional: I2C Color Sensor | I2C, TCS34725 at 0x29 (ID via 0x92 = 0x44) | Second device on the bus for a richer scan |
| Optional: 3-Axis Digital Accelerometer | I2C, 0x4C (MMA7660) or 0x53 (ADXL345), depends on version | Scan tells you which |
| Skip | Light, UV, sound, air quality, rotary, moisture (analog); ultrasonic, buttons (digital); NFC (complex); motors/servos | Not I2C, or off-scope |

Also ask for: **Grove-to-male-jumper cables** (or Grove-to-female; male jumpers can be pushed
into a Grove plug's sockets as a hack), and a breadboard if they have one.

### Where to get parts (in order)
1. **MLH Hardware Lab (MHacks hardware checkout).** The hacker handbook says MLH provides
   hardware first-come-first-served. Ask the MHacks help desk (Central Collaboration Area of the
   Duderstadt, people in MHacks Team shirts) or MLH staff where checkout is; usually you leave
   an ID. MLH's published lab list includes Grove sensors (a "3-axis digital" accelerometer,
   likely an ADXL345 at 0x53, and a Grove LCD, which is I2C), Arduinos and Raspberry Pis, but
   only a few of each, so go early. Grove parts need a Grove-to-jumper cable.
2. **FREE-WILi sponsor table.** They want people building with it, likely have sensors,
   breadboards and pinout knowledge, and they are the judges for the FREE-WILi prize.
3. **Discord / other hackers.** Ask in the MHacks Discord.
4. **EECS / BBB labs** (Beyster Building, next to the Duderstadt). Weekend access may need an
   MCard; mind the 8 PM door lock.
5. Last resort: Micro Center, Madison Heights (~45 min drive). Check hours first. Not worth
   missing the 8 PM door lock.

### No-parts contingency (if MLH is unstaffed or out of stock)
Probe needs **any one I2C device**. Don't wait at the MLH desk more than 10-15 minutes; run
`python scripts/smoke_test.py` (steps 1-7 need no parts) while waiting. Then, in order:
1. **FREE-WILi sponsor table.** Their examples use a SparkFun 9DoF IMU, so they likely have one.
   Ask: "I'm building an AI debugger on the FREE-WILi's I2C. Can I borrow any I2C sensor?"
2. **Other hackers / MHacks Discord.** Arduino starter kits often include an MPU-6050, BME280 or
   an I2C LCD.
3. **The user's own Orcas.** Plug in the Bottlenose or WILEye and run
   `python scripts/smoke_test.py --i2c`; if an address shows up, that's a free target (untested idea).
4. **The FREE-WILi's internal I2C bus** (display CPU: LIS3DH accelerometer, MCP7940 RTC,
   PCAL6416 expander): (The `--onboard` smoke-test option was removed in the OneWili port: OG firmware hosts I2C on MAIN only.)
   If it lists addresses, the whole AI path can be built and tested tonight with zero parts
   (not a breadboard demo, but it unblocks development). Unverified whether firmware supports it.
5. **Zero-parts loopback demo** with the male-to-male jumpers:
   `python scripts/smoke_test.py --loopback` drives GPIO25 and reads GPIO26 (jumper 25->26),
   and sends UART on GPIO8 and listens on GPIO9 (jumper 8->9). Reframes Probe as "is this wire /
   connection actually working?" Weaker than the sensor demo, but real.
**9:30 PM go/no-go still applies.** With no I2C device by then: demo loopbacks + onboard bus
(if #4 works) and show sensor support via the mock scenarios, or switch to a fallback idea from
RESEARCH.md.

### Wiring (verify pin locations on the physical header first)
```
For the BMM350 + SHT40 in hand: both on the same bus, both at 3.3V.
FREE-WILi pin 6 (3.3V out) -> breadboard + rail -> FREE-WILi pin 4 (IO voltage in) AND each sensor VCC
FREE-WILi pin 19 or 20 (GND) -> breadboard - rail -> each sensor GND
Sensor SDA -> pin 10 (GPIO16, I2C0 SDA)
Sensor SCL -> pin 8 (GPIO17, I2C0 SCL)
(+ 4.7k from SDA to VCC and from SCL to VCC if the breakout has no pull-ups)
Optional UART demo: user's Arduino TX -> GPIO9 (UART1 RX), grounds tied together
```

## Demo script (aim for under 90 s inside the 3-minute pitch)
1. "This is Sam, an EECS 373 student. It's 2 a.m., their compass project just prints
   'Compass not found!', and office hours are closed."
2. Show the two sensors wired to the FREE-WILi. Run `python -m probe.agent --code demo/bmm350_sketch.ino`.
3. Type or say "why can't my sketch find the compass?" The terminal shows `[probe] scan_i2c_bus()`,
   `identify_i2c_device('0x14')`, `check_code_address('0x13')`, `read_user_code(...)` as it measures.
4. Probe answers: "Your magnetometer is a BMM350 at 0x14 (I read its chip ID: 0x33). Your sketch
   uses 0x13 and BMM150 registers from a BMM150 tutorial. Change the address to 0x14 and switch to
   the DFRobot_BMM350 library." The FREE-WILi screen shows the headline, LEDs go red, low beep.
5. "Fixed" version: ask again with the corrected expectation: green LEDs, high beep.
6. Second bug for depth: pull the SDA jumper and ask again: "Nothing answered. Check SDA (GPIO16) first."
   (Plug it back in: both 0x14 and 0x44 reappear.)

## Pitch outline (3 minutes, from the workshop deck's structure)
1. Hook + user (15 s): Sam at 2 a.m.
2. Problem + 2 data points (20 s): ~33M Arduino users; chatbots can't see hardware so they guess.
3. Solution (20 s): an AI lab partner that measures before it answers.
4. Live demo (90 s).
5. Why FREE-WILi (15 s): independent, known-good instrument with adjustable I/O voltage, I2C/UART/GPIO in one box.
6. Next steps (15 s): passive bus sniffing via the FPGA logic analyzer, more protocols, voice.
Close with one line: "Stop guessing. Measure."

## Likely judge questions
- *Why not ChatGPT?* It can't measure; it guesses from your description.
- *Why not Claude Code + an I2C scanner sketch?* That needs a working board and reflashing.
  Probe is an independent instrument for when your board/code is the problem, and it's for beginners.
- *Why not a Saleae logic analyzer?* Great tool, $500+, no conversational diagnosis; you
  still need to know what you're looking at.
- *What if the AI is wrong?* Every claim is backed by a shown measurement; tool calls print live;
  `--no-ai` mode gives the raw report.
- *Business?* Lab-kit add-on for university courses / makerspaces; software for FREE-WILi owners.

## Submission checklist
- [ ] Devpost: title, problem, solution, how it works, built with (FREE-WILi, Python, Gemini), repo link, video
- [ ] Opt into: Best Use of FREE-WILi, Beyond the Code (Hardware), MLH Gemini, Notability, side quests
      (check Devpost for a cap on how many prizes you can enter)
- [ ] Notability: tag "Notability", note how Notability Pro was used + at least 2 screenshots
- [ ] Teammate list correct (solo); table number filled in
- [ ] Backup video recorded before 9:30 AM
