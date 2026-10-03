# Research from the planning session

Everything below was gathered before building. Web sources are listed at the end. Things marked
"estimate" are judgment calls, not data.

## Event facts (MHacks 2026)
- Hacking Sat Oct 3 12 PM to Sun Oct 4 12 PM. Venue: Duderstadt Center, North Campus. Teams of 1-4.
- Judging criteria (handbook): innovation, technical complexity, usability, presentation quality.
- Main tracks, $2,500 each: Sustainability, Actually Intelligent (AI), FinTech, Beyond the Code (Hardware). Grand prize $5,000.
- Side quests: Useless AI (mystery prize), Dumbest Idea (a Bop It), Judged by an LLM.
- Sponsor prizes: Notability (Pro + merch; build with Notability Pro, tag it, 2 screenshots);
  FinchNode (healthcare API with synthetic records; Apple Watch / $500 / dev plan);
  Fetch.ai ASI:One agent ($1,250/$750/$500; register on Agentverse, discoverable via ASI:One, extra submission);
  ElevenLabs (Scale tier for the best use); Photon iMessage agents via Spectrum ($700/$300);
  Neon backend (AI Gateway credits); **Best Use of FREE-WILi (FREE-WILi kits for each member, up to 4)**;
  Relay interactive agents (SF trip); SpaceXAI (needs Cursor + Grok API); Figma Best Design;
  Spacetime real-time backend ($1,000/$500/$200); Capital One Nessie; MLH: ElevenLabs, Gemini,
  Solana, Tiger Data, Presage (truncated in the PDF).
- The "How to Win a Hackathon" deck the user shared is from **A2Tech360/JacHacks (Sept 26-27)**:
  its IBM rubric and Jac requirement do NOT apply here; its method does (real user, existing
  solutions, gap, one-sentence value prop, KISS MVP, backup video, anticipate questions).

## The user's hardware
- **FREE-WILi 1** (a.k.a. OG / Black): 2x RP2040 (display CPU + main CPU), iCE40UP5K FPGA with
  8 MB SRAM, FT232H high-speed USB, 320x240 color LCD (ST7789), 5 colored buttons, 7 RGB LEDs,
  IR TX/RX, PDM mic, I2S speaker, LIS3DH accelerometer (+temp), MCP7940 RTC, battery,
  2x CC1101 sub-GHz radios (300-348 / 387-464 / 779-928 MHz), 11 GPIO with programmable voltage
  1.1-5.5V (UART, SPI, I2C, PWM), logic analyzer via FPGA, WASM scripts on device.
- **WILEye camera Orca** (rev 1, 9/4/2025): ESP32-P4, 2 MP camera, 640x480/720p/1080p, photo
  and video to storage (then copy to PC; not a live stream), zoom 1-4, flash, on-device AI
  detection events (pedestrian, face), own 1.54" LCD, microSD.
- **Bottlenose Orca** (rev 1, 5/30/2025): ESP32 Wi-Fi/BLE; WebSocket terminal bridge, BLE terminal, Wi-Fi/BLE scans.
- **Maestro Orca**: debug/development tool. **Antennas**: 315, 433, 915 MHz. Orca whale tail badge. Male-to-male jumpers.
- FREE-WILi 2 (released Sept 2026; NOT what the user has): RP2350s, ESP32-C5, CM0 Linux, touchscreen, NFC, LoRa, CAN FD.

## Past FREE-WILi hackathon projects (don't repeat)
| Project | Event | What | Result |
|---|---|---|---|
| **Wattson** | MHacks 2025 | Tamagotchi-style pet, sad when lights left on; Pillow image-splicing engine because the API only pushes static images | **Won Best Use of FREE-WiLi** + an MHacks main track + a sponsor track |
| **Gestura** | MHacks 2025 | Accelerometer air-mouse + offline Vosk voice commands for amputees / limited mobility; fixed integration drift with a deadband; inspired by the FREE-WILi workshop demo | **Won Best Use of FREE-WiLi** |
| celestaisle | MHacks | Shopping list + in-store compass | |
| Wolf Hunt | SpartaHack 11 | Duck-Hunt clone aiming the WILEye camera | |
| Wili-Pass | GrizzHacks 7 | Exchange "passports" over radio when devices meet | |
| M3SH | hackathon | Offline mesh network over the radios | |
| AI Social Intrigue | hackathon | Mafia with AI players; ElevenLabs voices through the FREE-WILi speaker; Gemini | |
| MeyesAI | Hack Dearborn | Monocular-depth navigation aid for the visually impaired | |
| DriveGuard | Hack Dearborn | OpenCV/MediaPipe distraction detection; FREE-WILi LEDs red/green | |
| RoadPulse | Hack Dearborn | Road sensing with accelerometer + mic | |
| Agent Unblind | Hack Dearborn | AI agent: emails, invoices, photographs intruders on motion | |
| OmniComm | 2026 | Assistive communicator (STT/TTS) bridging blind/deaf/non-verbal users | |
| Reality Check | 2026 | Real-time AI fact checking | |
| thereMINI | hackathon | Wearable theremin, accelerometer to MIDI | |
| FreeWil-iR | hackathon | IR + accelerometer entertainment | |
| WiLi-Party | hackathon | Two-player LED minigames | |
| Tracker Detector | hackathon | AirTag/Tile detection (ended up on a Raspberry Pi) | |
| BluQ | hackathon | Started on FREE-WILi, switched to Raspberry Pi | |

Saturated themes: accelerometer gestures (4), games (4), camera AI for accessibility (3),
voice AI through the device (3), radio device-to-device (2).
**Untouched:** the FREE-WILi's identity as an electronics test tool (I2C/SPI/UART probing,
logic analyzer, FPGA). Probe is built there on purpose.
What both MHacks winners shared: the device itself was the product, a specific user and story,
and one honest technical struggle they could explain.
FREE-WILi prize had 2 winners at MHacks 2025 and 3 at SpartaHack 11 and GrizzHacks 8.

## Competition estimate per prize (estimate)
Low: Best Use of FREE-WILi (needs a kit), FinchNode, Notability (effort-only).
Low-medium: Hardware track (fewer entries, higher bar), Photon (needs a Mac), Spacetime/Neon.
Medium-high: Fetch.ai (cash). High: ElevenLabs, MLH Gemini (everyone uses them). Side quests: luck.

## Ideas considered and why they lost
| Idea | Existing products | Verdict |
|---|---|---|
| Voice agent via ElevenLabs that acts physically through FREE-WILi (user's first idea) | Alexa+, Gemini for Home, Home Assistant MCP servers (85+ tools), ElevenLabs+ESP32 tutorials, BroadLink/SwitchBot IR hubs | A capability, not a product ("who is the user?"). Kept as the *interface* of Probe |
| Legacy-gear "Puppeteer" (IR/RF replay + button fingers) | BroadLink RM4 Pro (~$40, IR + 315/433 RF, Home Assistant), SwitchBot Bot (~$30 button pusher), Flipper Zero | Overlaps; needs a target device at the venue; never replay rolling-code garage/car signals |
| Distraction Brake (physical friction against doomscrolling) | Brick (physical NFC blocker), one sec (friction app; ~57% less social media use in a study) | Mechanical version needs solenoids/3D printing: not feasible solo. Simplified version is weak for the FREE-WILi prize |
| AI sorting bin (camera + Gemini) | Oscar Sort (Intuitive AI) at UW-Madison, SFU | Product exists; competes with teammates in Sustainability |
| Medication companion -> FinchNode | AdhereTech (~$1,210/patient/yr), Pillsy, Hero Health; adherence ~50% | **Fallback** if Probe's hardware path fails (FinchNode prize is low-competition) |
| Fall/check-in monitor | Apple Watch, Life Alert, Medical Guardian | Saturated |
| FREE-WILi Bop It + ElevenLabs insults | Bop It | Side-quest-only backup |
| Join teammates as hardware person (bin sensor via Bottlenose Wi-Fi) | n/a | Strategically strong alternative to going solo |

## Probe competitive landscape
- ChatGPT/Claude chat: can't see the circuit, guesses from descriptions.
- Saleae Logic analyzers: excellent capture/decoding, $500+, no conversational diagnosis. A
  Claude Code skill (Jan 2026) analyzes *exported* Saleae captures offline, not live.
- Bus Pirate: powerful but a steep command-line tool for experts.
- Flux Copilot: AI for PCB *design*, not live debugging.
- Claude Code + the user's own MCU + I2C-scanner sketch: possible for advanced devs; requires a
  working board and reflashing. Probe is independent of the user's board and code.

## Sources
- FREE-WILi code: https://github.com/freewili/freewili-python · https://github.com/freewili/onewili · https://github.com/freewili/wiliOGbsp · https://github.com/freewili/wilibsp
- FREE-WILi docs: https://docs.freewili.com (GPIO, Orcas, WILEye, Bottlenose) · project blog: https://docs.freewili.com/blog/tags/hackathon/
- Gestura: https://docs.freewili.com/blog/gestura/ · MHacks 2025 gallery: https://mhacks-2025.devpost.com/project-gallery · https://freewili.com/event/mhacks/
- FREE-WILi 2: https://www.cnx-software.com/2026/09/09/free-wili-2-portable-hacking-multitool-features-two-rp2350-mcus-esp32-c5-ice40-fpga-and-raspberry-pi-cm0/
- ElevenLabs hardware control: https://www.hackster.io/gabogiraldo/control-hardware-using-generative-voice-ai-3465c0
- Home Assistant MCP: https://dev.co/ai/mcp/ha-mcp
- Harmony discontinued: https://www.xda-developers.com/harmony-logitech-discontinue-universal-remotes/ · BroadLink RM4 Pro: https://techtactician.com/broadlink-rm4-pro-home-assistant-quick-setup-guide/
- Brick: https://www.healthline.com/health/brick-phone-lock-review · Oscar Sort: https://sustainability.wisc.edu/what-uw-madisons-ai-recycling-assistant-is-revealing-about-how-we-sort-waste/
- Saleae skill: https://blog.adafruit.com/2026/01/30/a-claude-code-skill-to-analyze-saleae-logic-mso-signals/ · Flux Copilot: https://flux.ai/p/blog/flux-copilot-the-first-ai-powered-hardware-design-assistant
- Arduino 33M users: https://www.eenewseurope.com/en/arduino-open-source-report-2025-ecosystem-growth/ · EECS 373: https://ece.engin.umich.edu/?p=1911
- MLH hardware lab list: https://guide.mlh.io/organizer-resources/hardware-lab-contents
- Medication adherence: https://www.mobihealthnews.com/news/study-adheretechs-smart-pill-bottle-intervention-improves-adherence-without-major-additional
