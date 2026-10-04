"""Turn a second FREE-WILi into a stand-in I2C sensor, so bugs can be planted on demand.

    python scripts/fake_sensor.py --serial FW5171                 # BMM350 look-alike at 0x14
    python scripts/fake_sensor.py --serial FW5171 --address 0x3F  # move it (the "wrong address" bug)
    python scripts/fake_sensor.py --serial FW5171 --chip-id 0x32  # wrong chip at the right address
    python scripts/fake_sensor.py --serial FW5171 --off           # unplugged sensor

Wiring (male-to-male jumpers): on EACH unit, its own pin 6 -> its own pin 4. Between the units:
pin 19 <-> 19 (GND), pin 10 <-> 10 (SDA), pin 8 <-> 8 (SCL). Each unit on its own USB cable.
Run Probe on the other unit with PROBE_SERIAL=<its serial>.
"""

import argparse

import onewili


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", required=True, help="serial of the unit that plays the sensor, e.g. FW5171")
    parser.add_argument("--address", type=lambda s: int(s, 0), default=0x14)
    parser.add_argument("--chip-id", type=lambda s: int(s, 0), default=0x33)
    parser.add_argument("--off", action="store_true", help="stop answering on the bus")
    args = parser.parse_args()

    dev = onewili.connect(serial=args.serial)
    try:
        i2c = dev.io.i2c
        i2c.i2c_slave_enable(0).expect("disabling slave mode failed")
        if args.off:
            dev.gui.show_text("OFF")
            print("stand-in sensor is off")
            return
        # Like a BMM350: a read from register 0 returns 2 dummy bytes, then the chip ID.
        i2c.i2c_slave_set_data(bytes([0x00, 0x00, 0x00, args.chip_id])).expect("loading registers failed")
        i2c.i2c_slave_enable(args.address).expect("enabling slave mode failed")
        dev.gui.show_text(f"at 0x{args.address:02X}")
        print(f"stand-in sensor at 0x{args.address:02X}, chip ID 0x{args.chip_id:02X}")
    finally:
        dev.close()


if __name__ == "__main__":
    main()
