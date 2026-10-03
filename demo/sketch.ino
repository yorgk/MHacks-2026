// Demo "student" sketch with a planted bug for the Probe demo.
// The I2C LCD backpack on the demo board is a PCF8574A at 0x3F, but this says 0x27,
// which is the most common beginner mistake with these LCDs.
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);  // <-- bug: should be 0x3F

void setup() {
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Hello, EECS 373!");
}

void loop() {}
