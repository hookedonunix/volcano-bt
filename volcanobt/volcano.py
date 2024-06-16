import logging
import asyncio
import struct
from typing import Callable, Union, Final

from volcanobt.connection import BTLEConnection

_LOGGER = logging.getLogger(__name__)

TEMP_CELSIUS: Final = "°C"
TEMP_FAHRENHEIT: Final = "°F"

VOLCANO_STAT_SERVICE_UUID = "10100000-5354-4f52-5a26-4249434b454c"
VOLCANO_HW_SERVICE_UUID = "10110000-5354-4f52-5a26-4249434b454c"

VOLCANO_TEMP_CURR_UUID = "10110001-5354-4f52-5a26-4249434b454c"
VOLCANO_TEMP_TARGET_UUID = "10110003-5354-4f52-5a26-4249434b454c"

VOLCANO_HEAT_ON_UUID = "1011000f-5354-4f52-5a26-4249434b454c"
VOLCANO_HEAT_OFF_UUID = "10110010-5354-4f52-5a26-4249434b454c"

VOLCANO_PUMP_ON_UUID = "10110013-5354-4f52-5a26-4249434b454c"
VOLCANO_PUMP_OFF_UUID = "10110014-5354-4f52-5a26-4249434b454c"

VOLCANO_AUTO_OFF_TIME_UUID = "1011000c-5354-4f52-5a26-4249434b454c"
VOLCANO_SHUT_OFF_TIME_UUID = "1011000d-5354-4f52-5a26-4249434b454c"
VOLCANO_OPERATION_HOURS_UUID = "10110015-5354-4f52-5a26-4249434b454c"

VOLCANO_LED_BRIGHTNESS_UUID = "10110005-5354-4f52-5a26-4249434b454c"

VOLCANO_SERIAL_NUMBER_UUID = "10100008-5354-4f52-5a26-4249434b454c"
VOLCANO_FIRMWARE_VERSION_UUID = "10100003-5354-4f52-5a26-4249434b454c"
VOLCANO_BLE_FIRMWARE_VERSION_UUID = "10100004-5354-4f52-5a26-4249434b454c"

VOLCANO_STAT1_REGISTER_UUID = "1010000c-5354-4f52-5a26-4249434b454c"
VOLCANO_STAT2_REGISTER_UUID = "1010000d-5354-4f52-5a26-4249434b454c"
VOLCANO_STAT3_REGISTER_UUID = "1010000e-5354-4f52-5a26-4249434b454c"

VOLCANO_STAT1_HEATER_ON_MASK = 0x0020
VOLCANO_STAT1_PUMP_ON_MASK = 0x2000
VOLCANO_STAT1_AUTO_OFF_ENABLED_MASK = 0x200

VOLCANO_STAT2_FAHRENHEIT_ENABLED_MASK = 0x200
VOLCANO_STAT2_DISPLAY_ON_COOLING_MASK = 0x1000
VOLCANO_STAT3_VIBRATION_ENABLED_MASK = 0x400

VOLCANO_STAT1_ERROR_MASK = 0x4018
VOLCANO_STAT2_ERROR_MASK = 0x003B

def celsius_to_fahrenheit(temperature: int) -> int:
    return (temperature * 1.8) + 32

def fahrenheit_to_celsius(temperature: int) -> int:
    return (temperature - 32) / 1.8

class Volcano:
    """Volcano entity class"""

    def __init__(self, mac: str):
        self._mac = mac

        self._temperature = 0
        self._target_temperature = 0
        self._operation_hours = None
        self._serial_number = None
        self._firmware_version = None
        self._ble_firmware_version = None
        self._auto_off_time = None
        self._shut_off_time = None
        self._led_brightness = None

        self._heater_on = False
        self._pump_on = False
        self._auto_off_enabled = False

        self._temperature_unit = None
        self._display_on_cooling = False
        self._vibration_enabled = False

        self._temperature_changed_callback = None
        self._target_temperature_changed_callback = None
        self._heater_changed_callback = None
        self._pump_changed_callback = None
        self._temperature_unit_changed_callback = None
        self._display_on_cooling_changed_callback = None

    async def connect(self) -> bool:
        self._conn = BTLEConnection(self._mac)
        result = await self._conn.connect()
        await self.register_notifications()

        return result

    async def disconnect(self) -> bool:
        return await self._conn.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._conn.is_connected

    async def read_attributes(self) -> None:
        _LOGGER.debug('Reading BLE GATT attributes')

        await asyncio.gather(
            self.read_temperature(),
            self.read_target_temperature(),
            self.read_operation_hours(),
            self.read_serial_number(),
            self.read_firmware_version(),
            self.read_ble_firmware_version(),
            self.read_auto_off_time(),
            self.read_shut_off_time(),
            self.read_led_brightness(),

            self.read_stat1_register(),
            self.read_stat2_register(),
            self.read_stat3_register(),
        )

    async def register_notifications(self) -> None:
        _LOGGER.info('Notifications registered')
        await self._conn.start_notify(VOLCANO_TEMP_CURR_UUID, self._parse_temperature)
        await self._conn.start_notify(VOLCANO_TEMP_TARGET_UUID, self._parse_target_temperature)

        await self._conn.start_notify(VOLCANO_STAT1_REGISTER_UUID, self._parse_stat1_register)
        await self._conn.start_notify(VOLCANO_STAT2_REGISTER_UUID, self._parse_stat2_register)
        await self._conn.start_notify(VOLCANO_STAT3_REGISTER_UUID, self._parse_stat3_register)

    @property
    def temperature(self) -> int:
        return self.convert_temp_unit(self._temperature)

    async def read_temperature(self) -> None:
        result = await self._conn.read_gatt_char(VOLCANO_TEMP_CURR_UUID)

        self._parse_temperature(10, result)

    def _parse_temperature(self, sender: int, data: bytearray) -> None:
        temperature = round(struct.unpack('<I', data)[0] / 10)

        _LOGGER.debug(f"Received current temperature: {temperature}")

        # Check for a uint16 overflow caused by BLE implementation
        if temperature < 6536:
            self._temperature = temperature
            if self._temperature_changed_callback:
                self._temperature_changed_callback(temperature)

    def on_temperature_changed(self, callback: Callable[[int], None]) -> None:
        self._temperature_changed_callback = callback

    @property
    def target_temperature(self) -> int:
        return self.convert_temp_unit(self._target_temperature)

    async def set_target_temperature(self, temperature: int) -> None:
        # Volcano temps are always sent in celsius, then converted if displayed
        if self.temperature_unit == TEMP_FAHRENHEIT:
            temperature = fahrenheit_to_celsius(temperature)

        data = struct.pack("<I", temperature * 10)

        await self._conn.write_gatt_char(VOLCANO_TEMP_TARGET_UUID, data)

        self._target_temperature = round(temperature)

    async def read_target_temperature(self) -> None:
        result = await self._conn.read_gatt_char(VOLCANO_TEMP_TARGET_UUID)

        self._parse_target_temperature(10, result)

    def _parse_target_temperature(self, sender: int, data: bytearray) -> None:
        temperature = round(struct.unpack("<I", data)[0] / 10)

        _LOGGER.debug(f"Received target temperature: {temperature}")

        self._target_temperature = temperature
        if self._target_temperature_changed_callback:
            self._target_temperature_changed_callback(temperature)

    def on_target_temperature_changed(self, callback: Callable[[int], None]) -> None:
        self._target_temperature_changed_callback = callback

    @property
    def operation_hours(self) -> Union[int, None]:
        return self._operation_hours

    async def read_operation_hours(self) -> None:
        result = await self._conn.read_gatt_char(VOLCANO_OPERATION_HOURS_UUID)

        self._operation_hours = int(struct.unpack("I", result)[0])

        _LOGGER.debug(f"Received target temperature: {self.operation_hours}")

    @property
    def serial_number(self) -> Union[str, None]:
        return self._serial_number

    async def read_serial_number(self) -> None:
        result = await self._conn.read_gatt_char(VOLCANO_SERIAL_NUMBER_UUID)

        self._serial_number = result.decode("utf-8")

        _LOGGER.debug(f"Received serial number: {self.serial_number}")

    @property
    def firmware_version(self) -> Union[str, None]:
        return self._firmware_version

    async def read_firmware_version(self) -> None:
        result = await self._conn.read_gatt_char(VOLCANO_FIRMWARE_VERSION_UUID)

        self._firmware_version = result.decode('utf-8')

        _LOGGER.debug(f"Received firmware version: {self.firmware_version}")

    @property
    def ble_firmware_version(self) -> Union[str, None]:
        return self._ble_firmware_version

    async def read_ble_firmware_version(self) -> None:
        result = await self._conn.read_gatt_char(VOLCANO_BLE_FIRMWARE_VERSION_UUID)

        self._ble_firmware_version = result.decode('utf-8')
        _LOGGER.debug(f"Received ble firmware version: {self.ble_firmware_version}")

    @property
    def auto_off_time(self) -> Union[int, None]:
        return self._auto_off_time

    async def read_auto_off_time(self) -> None:
        result = await self._conn.read_gatt_char(VOLCANO_AUTO_OFF_TIME_UUID)

        self._auto_off_time = int(struct.unpack('H', result)[0])

        _LOGGER.debug(f"Received auto off time: {self.auto_off_time}")

    @property
    def shut_off_time(self) -> Union[int, None]:
        return self._shut_off_time

    async def read_shut_off_time(self) -> None:

        result = await self._conn.read_gatt_char(VOLCANO_SHUT_OFF_TIME_UUID)

        self._shut_off_time = int(struct.unpack('H', result)[0])
        _LOGGER.debug(f"Received shut off time: {self.shut_off_time}")

    @property
    def led_brightness(self) -> Union[int, None]:
        return self._led_brightness

    async def set_led_brightness(self, brightness: int) -> None:
        data = struct.pack('H', brightness)

        await self._conn.write_gatt_char(VOLCANO_LED_BRIGHTNESS_UUID, data)

        self._led_brightness = round(brightness)

    async def read_led_brightness(self) -> None:

        result = await self._conn.read_gatt_char(VOLCANO_LED_BRIGHTNESS_UUID)

        self._led_brightness = int(struct.unpack('H', result)[0] / 10)

        _LOGGER.debug(f"Received led brightness: {self.led_brightness}")

    @property
    def heater_on(self) -> bool:
        return self._heater_on

    async def set_heater(self,  state: bool) -> None:
        heater_uuid = VOLCANO_HEAT_ON_UUID if state else VOLCANO_HEAT_OFF_UUID
        
        data = struct.pack('B', 0)

        await self._conn.write_gatt_char(heater_uuid, data)

        self._heater_on = state

    async def toggle_heater(self) -> None:
        await self.set_heater(not self.heater_on)

    def on_heater_changed(self, callback: Callable[[bool], None]) -> None:
        self._heater_changed_callback = callback

    @property
    def pump_on(self) -> bool:
        return self._pump_on

    async def set_pump(self,  state: bool) -> None:
        pump_uuid = VOLCANO_PUMP_ON_UUID if state else VOLCANO_PUMP_OFF_UUID
        
        data = struct.pack('B', 0)

        await self._conn.write_gatt_char(pump_uuid, data)

        self._pump_on = state

    async def toggle_pump(self) -> None:
        await self.set_pump(not self.pump_on)

    def on_pump_changed(self, callback: Callable[[bool], None]) -> None:
        self._pump_changed_callback = callback

    @property
    def auto_off_enabled(self) -> bool:
        return self._auto_off_enabled

    async def read_stat1_register(self) -> None:
        result = await self._conn.read_gatt_char(VOLCANO_STAT1_REGISTER_UUID)

        _LOGGER.info(result)

        self._parse_stat1_register(10, result)

    def _parse_stat1_register(self, sender: int, data: bytearray) -> None:
        data = int.from_bytes(data, byteorder="little")

        self._heater_on = (data & VOLCANO_STAT1_HEATER_ON_MASK) != 0
        self._pump_on = (data & VOLCANO_STAT1_PUMP_ON_MASK) != 0
        self._auto_off_enabled = (data & VOLCANO_STAT1_AUTO_OFF_ENABLED_MASK) == 0

        _LOGGER.debug("Received stat1 register update:")
        _LOGGER.debug(f"  - Pump      {self._heater_on}")
        _LOGGER.debug(f"  - Heater    {self._pump_on}")
        _LOGGER.debug(f"  - Auto off  {self._auto_off_enabled}")

        if self._heater_changed_callback:
            self._heater_changed_callback(self._heater_on)

        if self._pump_changed_callback:
            self._pump_changed_callback(self._pump_on)

    @property
    def temperature_unit(self) -> Union[str, None]:
        return self._temperature_unit

    async def set_temperature_unit(self, unit: str) -> None:
        data = self.encode_bit_mask(VOLCANO_STAT2_FAHRENHEIT_ENABLED_MASK, unit == TEMP_CELSIUS)

        await self._conn.write_gatt_char(VOLCANO_STAT2_REGISTER_UUID, data)

        self._temperature_unit = unit

    def on_temperature_unit_changed(self, callback: Callable[[str], None]) -> None:
        self._temperature_unit_changed_callback = callback

    @property
    def display_on_cooling(self) -> bool:
        return self._display_on_cooling

    async def set_display_on_cooling(self, state: bool) -> None:
        data = self.encode_bit_mask(VOLCANO_STAT2_DISPLAY_ON_COOLING_MASK, state)

        await self._conn.write_gatt_char(VOLCANO_STAT2_REGISTER_UUID, data)

        self._display_on_cooling = state
    
    def on_display_on_cooling_changed(self, callback: Callable[[bool], None]) -> None:
        self._display_on_cooling_changed_callback = callback

    async def read_stat2_register(self) -> None:
        result = await self._conn.read_gatt_char(VOLCANO_STAT2_REGISTER_UUID)

        self._parse_stat2_register(10, result)

    def _parse_stat2_register(self, sender: int, data: bytearray) -> None:
        data = int.from_bytes(data[1:3], byteorder="big")

        #if (data & VOLCANO_STAT2_FAHRENHEIT_ENABLED_MASK) == 0:
        #    self._temperature_unit = TEMP_CELSIUS
        #else:
        #    self._temperature_unit = TEMP_FAHRENHEIT

        # Stat2 register triggers on temperature change while cooling
        # even if no value has changed, so check if values change before callback
        temperature_unit = TEMP_CELSIUS if (data & VOLCANO_STAT2_FAHRENHEIT_ENABLED_MASK) == 0 else TEMP_FAHRENHEIT

        if self._temperature_unit != temperature_unit:
            self._temperature_unit = temperature_unit
            if self._temperature_unit_changed_callback:
                self._temperature_unit_changed_callback(self._temperature_unit)

        #self._display_on_cooling = (data & VOLCANO_STAT2_DISPLAY_ON_COOLING_MASK) == 0

        display_on_cooling = (data & VOLCANO_STAT2_DISPLAY_ON_COOLING_MASK) == 0

        if self._display_on_cooling != display_on_cooling:
            self._display_on_cooling = display_on_cooling
            if self._display_on_cooling_changed_callback:
                self._display_on_cooling_changed_callback(self._display_on_cooling)

        _LOGGER.debug("Received stat2 register update:")
        _LOGGER.debug(f"  - Temperature unit   {self.temperature_unit}")
        _LOGGER.debug(f"  - Display on cooling {self.display_on_cooling}")

        # self._temperature_unit_changed_callback(self._temperature_unit)
        # self._display_on_cooling_callback(self._display_on_cooling)

    @property
    def vibration_enabled(self) -> bool:
        return self._vibration_enabled

    async def set_vibration_enabled(self,  state: bool) -> None:
        data = self.encode_bit_mask(VOLCANO_STAT3_VIBRATION_ENABLED_MASK, state)

        await self._conn.write_gatt_char(VOLCANO_STAT3_REGISTER_UUID, data)

        self._vibration_enabled = state

    async def read_stat3_register(self) -> None:
        _LOGGER.debug("Reading stat3 register")

        result = await self._conn.read_gatt_char(VOLCANO_STAT3_REGISTER_UUID)

        self._parse_stat3_register(10, result)

    def _parse_stat3_register(self, sender: int, data: bytearray) -> None:
        data = int.from_bytes(data[1:3], byteorder="big")

        if (data & VOLCANO_STAT3_VIBRATION_ENABLED_MASK) == 0:
            self._vibration_enabled = True
        else:
            self._vibration_enabled = False

        _LOGGER.debug("Received stat3 register update:")
        _LOGGER.debug(f"  - Vibration {self.vibration_enabled}")

    def encode_bit_mask(self, mask: int, state: bool):
        return struct.pack("I", mask if state else mask + 0x10000)

    def convert_temp_unit(self, temperature: int) -> int:
        return temperature if self.temperature_unit != TEMP_FAHRENHEIT else (temperature * 1.8) + 32
