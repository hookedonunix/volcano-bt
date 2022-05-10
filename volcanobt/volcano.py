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

VOLCANO_STATUS_REGISTER_UUID = "1010000c-5354-4f52-5a26-4249434b454c"
VOLCANO_TEMP_UNIT_REGISTER_UUID = "1010000d-5354-4f52-5a26-4249434b454c"

VOLCANO_VIBRATION_REGISTER_UUID = "1010000e-5354-4f52-5a26-4249434b454c"

VOLCANO_HEATER_ON_MASK = b"\x00\x20"
VOLCANO_PUMP_ON_MASK = b"\x20\x00"

VOLCANO_AUTO_OFF_ENABLED_MASK = b"\x02\x00"
VOLCANO_VIBRATION_ENABLED_MASK = b"\x04\x00"
VOLCANO_TEMP_UNIT_FAHRENHEIT_ENABLED_MASK = b"\x02\x00"

class Volcano:
    """Volcano entity class"""

    def __init__(self, mac: str):
        self._mac = mac

        self._temperature = 0
        self._target_temperature = 0
        self._heater_on = False
        self._pump_on = False
        self._auto_off_time = None
        self._shut_off_time = None
        self._operation_hours = None
        self._serial_number = None
        self._firmware_version = None
        self._ble_firmware_version = None
        self._led_brightness = None
        self._temperature_unit = None

        self._auto_off_enabled = False
        self._vibration_enabled = False


        self._temperature_changed_callback = None
        self._target_temperature_changed_callback = None
        self._heater_changed_callback = None
        self._pump_changed_callback = None

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
        _LOGGER.debug('Reading attributes')

        await asyncio.gather(
            self.read_temperature(),
            self.read_target_temperature(),
            self.read_auto_off_time(),
            self.read_shut_off_time(),
            self.read_operation_hours(),
            self.read_vibration_status_register(),
            self.read_led_brightness(),
            self.read_serial_number(),
            self.read_firmware_version(),
            self.read_ble_firmware_version(),
            self.read_temperature_unit_register(),
            self.read_status_register(),
        )

    async def initialize_metrics(self) -> None:
        _LOGGER.info('Initializing values')

        await self.read_temperature()
        await self.read_target_temperature()
        await self.read_auto_off_time()
        await self.read_shut_off_time()
        await self.read_operation_hours()
        await self.read_vibration_status_register()
        await self.read_led_brightness()
        await self.read_serial_number()
        await self.read_firmware_version()
        await self.read_ble_firmware_version()
        await self.read_temperature_unit_register()
        await self.read_status_register()

    async def register_notifications(self) -> None:
        hw_service = await self._conn.get_service(VOLCANO_HW_SERVICE_UUID)
        stat_service = await self._conn.get_service(VOLCANO_STAT_SERVICE_UUID)

        temp_curr_char = hw_service.get_characteristic(VOLCANO_TEMP_CURR_UUID)
        temp_target_char = hw_service.get_characteristic(VOLCANO_TEMP_TARGET_UUID)
        status_char = stat_service.get_characteristic(VOLCANO_STATUS_REGISTER_UUID)

        await self._conn.start_notify(temp_curr_char, self._temperature_changed)
        await self._conn.start_notify(temp_target_char, self._target_temperature_changed)
        await self._conn.start_notify(status_char, self._status_changed)
        _LOGGER.info('Notifications registered')

    @property
    def temperature(self) -> int:
        return self._temperature

    def on_temperature_changed(self, callback: Callable[[int], None]) -> None:
        self._temperature_changed_callback = callback

    def _temperature_changed(self, sender: int, data: bytearray) -> None:
        temperature = round(struct.unpack('<I', data)[0] / 10)

        self._temperature = temperature
        self._temperature_changed_callback(temperature)

    async def read_temperature(self) -> None:
        _LOGGER.debug('Reading current temperature')

        result = await self._conn.read_gatt_char(VOLCANO_TEMP_CURR_UUID)

        self._temperature = round(int(struct.unpack('<I', result)[0] / 10))

    @property
    def target_temperature(self) -> int:
        return self._target_temperature

    async def set_target_temperature(self, temperature: int) -> None:
        data = struct.pack('<I', temperature * 10)

        hw_service = await self._conn.get_service(VOLCANO_HW_SERVICE_UUID)

        characteristic = hw_service.get_characteristic(VOLCANO_TEMP_TARGET_UUID)

        await self._conn.write_gatt_char(characteristic, data)

        self._target_temperature = round(temperature)

    def _target_temperature_changed(self, sender: int, data: bytearray) -> None:
        temperature = round(struct.unpack('<I', data)[0] / 10)

        self._target_temperature = temperature
        self._target_temperature_changed_callback(temperature)

    def on_target_temperature_changed(self, callback: Callable[[int], None]) -> None:
        self._target_temperature_changed_callback = callback

    async def read_target_temperature(self) -> None:
        _LOGGER.debug('Reading target temperature')

        result = await self._conn.read_gatt_char(VOLCANO_TEMP_TARGET_UUID)

        self._target_temperature = round(int(struct.unpack('<I', result)[0] / 10))

    @property
    def serial_number(self) -> Union[str, None]:
        return self._serial_number

    async def read_serial_number(self) -> None:
        _LOGGER.debug('Reading serial number')

        result = await self._conn.read_gatt_char(VOLCANO_SERIAL_NUMBER_UUID)

        self._serial_number = result.decode('utf-8')

    @property
    def firmware_version(self) -> Union[str, None]:
        return self._firmware_version

    async def read_firmware_version(self) -> None:
        _LOGGER.debug('Reading firmware version')

        result = await self._conn.read_gatt_char(VOLCANO_FIRMWARE_VERSION_UUID)

        self._firmware_version = result.decode('utf-8')

    @property
    def ble_firmware_version(self) -> Union[str, None]:
        return self._ble_firmware_version

    async def read_ble_firmware_version(self) -> None:
        _LOGGER.debug('Reading BLE firmware version')

        result = await self._conn.read_gatt_char(VOLCANO_BLE_FIRMWARE_VERSION_UUID)

        self._ble_firmware_version = result.decode('utf-8')

    @property
    def auto_off_time(self) -> Union[int, None]:
        return self._auto_off_time

    async def read_auto_off_time(self) -> None:
        _LOGGER.debug('Reading auto off time')

        result = await self._conn.read_gatt_char(VOLCANO_AUTO_OFF_TIME_UUID)

        self._auto_off_time = int(struct.unpack('H', result)[0])

    @property
    def shut_off_time(self) -> Union[int, None]:
        return self._shut_off_time

    async def read_shut_off_time(self) -> None:
        _LOGGER.debug('Reading shutoff time')

        result = await self._conn.read_gatt_char(VOLCANO_SHUT_OFF_TIME_UUID)

        self._shut_off_time = int(struct.unpack('H', result)[0])

    @property
    def operation_hours(self) -> Union[int, None]:
        return self._operation_hours

    async def read_operation_hours(self) -> None:
        _LOGGER.debug('Reading operation hours')

        result = await self._conn.read_gatt_char(VOLCANO_OPERATION_HOURS_UUID)

        self._operation_hours = int(struct.unpack('I', result)[0])

    @property
    def led_brightness(self) -> Union[int, None]:
        return self._led_brightness

    async def read_led_brightness(self) -> None:
        _LOGGER.debug('Reading led brightness')

        result = await self._conn.read_gatt_char(VOLCANO_LED_BRIGHTNESS_UUID)

        self._led_brightness = int(struct.unpack('H', result)[0] / 10)

    async def set_led_brightness(self, brightness: int) -> None:
        data = struct.pack('H', brightness)

        hw_service = await self._conn.get_service(VOLCANO_HW_SERVICE_UUID)

        characteristic = hw_service.get_characteristic(VOLCANO_LED_BRIGHTNESS_UUID)

        await self._conn.write_gatt_char(characteristic, data)

        self._led_brightness = round(brightness)

    @property
    def vibration_enabled(self) -> bool:
        return self._vibration_enabled

    async def read_vibration_status_register(self) -> None:
        _LOGGER.debug('Reading vibration enabled')

        result = await self._conn.read_gatt_char(VOLCANO_VIBRATION_REGISTER_UUID)

        data = int.from_bytes(result, byteorder="little")

        vibration_mask = int.from_bytes(VOLCANO_VIBRATION_ENABLED_MASK, byteorder="big")

        if (data & vibration_mask) == 0:
            self._vibration_enabled = False
        else:
            self._vibration_enabled = True

    async def set_vibration_enabled(self,  state: bool) -> None:
        vibration_mask = int.from_bytes(VOLCANO_VIBRATION_ENABLED_MASK, byteorder="big")

        data = struct.pack('I', vibration_mask if state else vibration_mask + 65536)

        await self._conn.write_gatt_char(VOLCANO_VIBRATION_REGISTER_UUID, data)

        self._heater_on = state

    @property
    def temperature_unit(self) -> Union[str, None]:
        return self._temperature_unit

    async def read_temperature_unit_register(self) -> None:
        _LOGGER.debug('Reading temperature unit register')

        result = await self._conn.read_gatt_char(VOLCANO_TEMP_UNIT_REGISTER_UUID)

        data = int.from_bytes(result[-2:], byteorder="big")

        temp_unit_mask = int.from_bytes(VOLCANO_TEMP_UNIT_FAHRENHEIT_ENABLED_MASK, byteorder="big")

        if (data & temp_unit_mask) == 0:
            self._temperature_unit = TEMP_CELSIUS
        else:
            self._temperature_unit = TEMP_FAHRENHEIT

    async def set_temperature_unit(self, unit: str) -> None:
        temp_unit_mask = int.from_bytes(VOLCANO_TEMP_UNIT_FAHRENHEIT_ENABLED_MASK, byteorder="big")

        data = struct.pack('<L', temp_unit_mask if unit == TEMP_CELSIUS else temp_unit_mask + 65536)

        await self._conn.write_gatt_char(VOLCANO_TEMP_UNIT_REGISTER_UUID, data)

        self._temperature_unit = unit

    @property
    def heater_on(self) -> bool:
        return self._heater_on

    @property
    def pump_on(self) -> bool:
        return self._pump_on

    async def set_heater(self,  state: bool) -> None:
        heater_uuid = VOLCANO_HEAT_ON_UUID if state else VOLCANO_HEAT_OFF_UUID
        
        data = struct.pack('B', 0)

        await self._conn.write_gatt_char(heater_uuid, data)

        self._heater_on = state

    async def set_pump(self,  state: bool) -> None:
        pump_uuid = VOLCANO_PUMP_ON_UUID if state else VOLCANO_PUMP_OFF_UUID
        
        data = struct.pack('B', 0)

        await self._conn.write_gatt_char(pump_uuid, data)

        self._pump_on = state

    async def toggle_heater(self) -> None:
        await self.set_heater(not self.heater_on)

    async def toggle_pump(self) -> None:
        await self.set_pump(not self.pump_on)

    async def read_status_register(self) -> None:
        _LOGGER.debug('Reading status register')

        result = await self._conn.read_gatt_char(VOLCANO_VIBRATION_REGISTER_UUID)

        data = int.from_bytes(result[-2:], byteorder="big")

        heater_mask = int.from_bytes(VOLCANO_HEATER_ON_MASK, byteorder="big")
        pump_mask = int.from_bytes(VOLCANO_PUMP_ON_MASK, byteorder="big")
        auto_off_mask = int.from_bytes(VOLCANO_AUTO_OFF_ENABLED_MASK, byteorder="big")

        if (data & heater_mask) == 0:
            self._heater_on = False
        else:
            self._heater_on = True

        if (data & pump_mask) == 0:
            self._pump_on = False
        else:
            self._pump_on = True

        if (data & auto_off_mask) == 0:
            self._auto_off_enabled = True
        else:
            self._auto_off_enabled = False

        self._heater_changed_callback(self._heater_on)
        self._pump_changed_callback(self._pump_on)


    def on_heater_changed(self, callback: Callable[[bool], None]) -> None:
        self._heater_changed_callback = callback

    def on_pump_changed(self, callback: Callable[[bool], None]) -> None:
        self._pump_changed_callback = callback

    def _status_changed(self, sender: int, data: bytearray) -> None:
        _LOGGER.debug("Connection status update")
        data = int.from_bytes(data, byteorder="little")

        heater_mask = int.from_bytes(VOLCANO_HEATER_ON_MASK, byteorder="big")
        pump_mask = int.from_bytes(VOLCANO_PUMP_ON_MASK, byteorder="big")

        if (data & heater_mask) == 0:
            self._heater_on = False
        else:
            self._heater_on = True

        if (data & pump_mask) == 0:
            self._pump_on = False
        else:
            self._pump_on = True

        self._heater_changed_callback(self._heater_on)
        self._pump_changed_callback(self._pump_on)
