// Compass project - reads the magnetometer and prints the heading.
// Based on a compass tutorial I found online.
#include <Wire.h>

#define MAG_ADDR 0x13
#define MAG_CHIP_ID_REG 0x40

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.beginTransmission(MAG_ADDR);
  Wire.write(MAG_CHIP_ID_REG);
  if (Wire.endTransmission() != 0) {
    Serial.println("Compass not found!");
    while (1) {}
  }
  Serial.println("Compass ready");
}

void loop() {}
