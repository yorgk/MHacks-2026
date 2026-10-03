// Demo "student" sketch with a planted bug, built for the parts from the FREE-WILi table:
// a DFRobot SEN0622 (Bosch BMM350 magnetometer, I2C 0x14) + an SHT40 (I2C 0x44).
// The student followed a popular BMM150 compass tutorial: address 0x13 and BMM150 code.
// The board is a BMM350: different chip ID (0x33), registers and library (DFRobot_BMM350).
// Probe should catch both the wrong address and the wrong chip/library.
#include <Wire.h>

#define MAG_ADDR 0x13          // <-- bug: BMM150 tutorial address; the BMM350 is at 0x14
#define MAG_CHIP_ID_REG 0x40   // <-- bug: BMM150 register; BMM350 CHIP_ID is register 0x00
#define SHT40_ADDR 0x44

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.beginTransmission(MAG_ADDR);
  Wire.write(MAG_CHIP_ID_REG);
  if (Wire.endTransmission() != 0) {
    Serial.println("Compass not found!");   // this is all the student sees
  }
}

void loop() {}
