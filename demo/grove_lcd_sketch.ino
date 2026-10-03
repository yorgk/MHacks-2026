// Demo "student" sketch with a planted bug, built for the MLH Grove LCD RGB Backlight.
// The student followed a generic "I2C LCD" tutorial: LiquidCrystal_I2C at 0x27.
// The Grove LCD is a different chip (AIP31068 text controller at 0x3E + backlight at 0x62)
// and needs Seeed's rgb_lcd library. Probe should catch both the address and the library.
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);  // <-- bug: Grove LCD lives at 0x3E (use rgb_lcd)

void setup() {
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Hello, EECS 373!");
}

void loop() {}
