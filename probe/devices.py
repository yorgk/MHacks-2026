"""Common I2C devices: which addresses they live at and how to confirm their identity.

Most I2C sensors have an "ID" (a.k.a. WHO_AM_I / CHIP_ID) register that always returns
the same value. Reading it is the fastest way to prove *which* chip answered at an address.
Addresses below are the common defaults; many parts have a pin that moves them to an
alternate address. Treat matches as candidates, not certainties.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IdCheck:
    part: str
    register: int
    expected: int
    # Some chips return dummy bytes before the real data (BMM350 sends 2 over I2C).
    offset: int = 0


# address -> list of likely parts (human-readable)
CANDIDATES: dict[int, list[str]] = {
    0x0D: ["QMC5883L magnetometer"],
    0x10: ["BMM150 magnetometer (CSB/SDO low)"],
    0x13: ["BMM150 magnetometer (common tutorial default)"],
    0x14: ["BMM350 magnetometer (DFRobot SEN0622, ADSEL low = default)"],
    0x15: ["BMM350 magnetometer (ADSEL high)"],
    0x18: ["LIS3DH accelerometer (SDO low)"],
    0x19: ["LIS3DH accelerometer (SDO high)"],
    0x1D: ["ADXL345 accelerometer (ALT high)"],
    0x1E: ["HMC5883L magnetometer", "LSM303 magnetometer"],
    0x23: ["BH1750 light sensor"],
    0x27: ["PCF8574 I2C LCD backpack (16x2/20x4 LCD)"],
    0x29: ["TCS34725 color sensor (Grove I2C Color Sensor v2)", "VL53L0X distance sensor", "TSL2591 light sensor"],
    0x30: ["Grove LCD RGB Backlight: backlight driver (v5)"],
    0x36: ["MAX17048 fuel gauge"],
    0x38: ["AHT10/AHT20 temp/humidity"],
    0x3C: ["SSD1306 OLED display"],
    0x3D: ["SSD1306 OLED display (alt)"],
    0x39: ["TCS3414 color sensor (older Grove I2C Color Sensor)"],
    0x3E: ["Grove LCD RGB Backlight: text controller (AIP31068)"],
    0x3F: ["PCF8574A I2C LCD backpack (16x2/20x4 LCD)"],
    0x40: ["INA219 current sensor", "HDC1080 temp/humidity", "PCA9685 PWM driver", "Si7021"],
    0x44: ["SHT40/SHT4x temp/humidity", "SHT3x temp/humidity"],
    0x45: ["SHT3x temp/humidity (alt)", "SHT40-BD1B variant"],
    0x4C: ["MMA7660 accelerometer (Grove 3-Axis Digital Accelerometer 1.5g)"],
    0x48: ["ADS1115 ADC", "TMP102 temperature", "PCF8591 ADC"],
    0x50: ["AT24Cxx EEPROM"],
    0x53: ["ADXL345 accelerometer (Grove 3-axis digital accelerometer)"],
    0x5A: ["MLX90614 IR thermometer", "CCS811 air quality"],
    0x5C: ["BH1750 light sensor (alt)"],
    0x62: ["Grove LCD RGB Backlight: backlight driver (PCA9633, v4)"],
    0x68: ["MPU-6050 IMU", "ICM-20948 IMU", "DS3231 RTC"],
    0x69: ["MPU-6050 IMU (AD0 high)", "ICM-20948 IMU (SparkFun 9DoF default)"],
    0x6A: ["LSM6DS3/LSM6DSO IMU"],
    0x6B: ["LSM6DS3/LSM6DSO IMU (alt)"],
    0x70: ["HT16K33 LED driver (Grove Quad Alphanumeric Display)", "TCA9548A I2C multiplexer"],
    0x71: ["HT16K33 LED driver (alt address)"],
    0x76: ["BME280/BMP280/BME680 environmental sensor"],
    0x77: ["BMP280 (Grove Temperature and Barometer Sensor default)", "BME280/BME680 environmental sensor (alt)"],
}

# address -> ID-register checks to try (first match wins)
ID_CHECKS: dict[int, list[IdCheck]] = {
    # BMM350: CHIP_ID register 0x00 = 0x33, but I2C reads start with 2 dummy bytes.
    0x14: [IdCheck("BMM350", 0x00, 0x33, offset=2), IdCheck("BMM350", 0x00, 0x33)],
    0x15: [IdCheck("BMM350", 0x00, 0x33, offset=2), IdCheck("BMM350", 0x00, 0x33)],
    # BMM150 (often confused with BMM350): CHIP_ID register 0x40 = 0x32 (needs power-on bit first).
    0x13: [IdCheck("BMM150", 0x40, 0x32)],
    # TCS34725: ID register 0x12, but every register access needs the 0x80 command bit -> 0x92
    0x29: [IdCheck("TCS34725", 0x92, 0x44), IdCheck("TCS34727", 0x92, 0x4D)],
    0x18: [IdCheck("LIS3DH", 0x0F, 0x33)],
    0x19: [IdCheck("LIS3DH", 0x0F, 0x33)],
    0x1D: [IdCheck("ADXL345", 0x00, 0xE5)],
    0x53: [IdCheck("ADXL345", 0x00, 0xE5)],
    0x68: [IdCheck("MPU-6050", 0x75, 0x68), IdCheck("ICM-20948", 0x00, 0xEA)],
    0x69: [IdCheck("MPU-6050", 0x75, 0x68), IdCheck("ICM-20948", 0x00, 0xEA)],
    0x6A: [IdCheck("LSM6DS3", 0x0F, 0x69), IdCheck("LSM6DSO", 0x0F, 0x6C)],
    0x6B: [IdCheck("LSM6DS3", 0x0F, 0x69), IdCheck("LSM6DSO", 0x0F, 0x6C)],
    0x76: [IdCheck("BME280", 0xD0, 0x60), IdCheck("BMP280", 0xD0, 0x58), IdCheck("BME680", 0xD0, 0x61)],
    0x77: [IdCheck("BME280", 0xD0, 0x60), IdCheck("BMP280", 0xD0, 0x58), IdCheck("BME680", 0xD0, 0x61)],
}

# Classic beginner mix-ups: the address you wrote vs. the address the part is really at.
COMMON_ADDRESS_MIXUPS: dict[frozenset[int], str] = {
    frozenset({0x13, 0x14}): "BMM150 tutorials and libraries use 0x13. The DFRobot SEN0622 is a BMM350 at 0x14 (or 0x15), and BMM150 code will not work on it even at the right address: different chip, registers and library (DFRobot_BMM350).",
    frozenset({0x13, 0x15}): "BMM150 tutorials use 0x13. A BMM350 sits at 0x14/0x15 and needs the BMM350 library, not BMM150 code.",
    frozenset({0x14, 0x15}): "BMM350 moves between 0x14 and 0x15 with the ADSEL pin/jumper.",
    frozenset({0x44, 0x45}): "SHT4x/SHT3x parts sit at 0x44 or 0x45 depending on the variant or ADDR pin.",
    frozenset({0x27, 0x3E}): "Generic I2C-LCD tutorials use 0x27 (PCF8574 backpack). A Grove LCD RGB Backlight is a different chip at 0x3E and needs the Grove rgb_lcd library, not LiquidCrystal_I2C.",
    frozenset({0x3F, 0x3E}): "Generic I2C-LCD tutorials use 0x3F (PCF8574A backpack). A Grove LCD RGB Backlight is a different chip at 0x3E and needs the Grove rgb_lcd library, not LiquidCrystal_I2C.",
    frozenset({0x27, 0x3F}): "PCF8574 vs PCF8574A LCD backpacks ship at 0x27 or 0x3F depending on the chip variant.",
    frozenset({0x68, 0x69}): "MPU-6050/ICM-20948 move between 0x68 and 0x69 with the AD0 pin.",
    frozenset({0x76, 0x77}): "BME280/BMP280 move between 0x76 and 0x77 with the SDO pin.",
    frozenset({0x3C, 0x3D}): "SSD1306 OLEDs use 0x3C or 0x3D depending on a solder jumper.",
    frozenset({0x1D, 0x53}): "ADXL345 uses 0x53 (ALT low) or 0x1D (ALT high).",
    frozenset({0x18, 0x19}): "LIS3DH uses 0x18 or 0x19 depending on SDO.",
}


def candidates_for(address: int) -> list[str]:
    return CANDIDATES.get(address, ["Unknown device (not in the built-in table)"])


def mixup_hint(expected: int, found: int) -> str | None:
    return COMMON_ADDRESS_MIXUPS.get(frozenset({expected, found}))
