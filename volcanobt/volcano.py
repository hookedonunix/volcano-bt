import logging
import asyncio
import struct

from connection import BTLEConnection

logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

_LOGGER = logging.getLogger(__name__)

VOLCANO_STAT_SERVICE_UUID = "10100000-5354-4f52-5a26-4249434b454c"
VOLCANO_HW_SERVICE_UUID = "10110000-5354-4f52-5a26-4249434b454c"

VOLCANO_TEMP_CURR_UUID = "10110001-5354-4f52-5a26-4249434b454c"
VOLCANO_TEMP_TARGET_UUID = "10110003-5354-4f52-5a26-4249434b454c"

VOLCANO_HEATER_ON_UUID = "1011000f-5354-4f52-5a26-4249434b454c"
VOLCANO_HEATER_OFF_UUID = "10110010-5354-4f52-5a26-4249434b454c"

VOLCANO_PUMP_ON_UUID = "10110013-5354-4f52-5a26-4249434b454c"
VOLCANO_PUMP_OFF_UUID = "10110014-5354-4f52-5a26-4249434b454c"

VOLCANO_AUTO_OFF_TIME_UUID = "1011000c-5354-4f52-5a26-4249434b454c"
VOLCANO_OPERATION_HOURS_UUID = "10110015-5354-4f52-5a26-4249434b454c"

VOLCANO_SERIAL_NUMBER_UUID = "10100008-5354-4f52-5a26-4249434b454c"
VOLCANO_FIRMWARE_VERSION_UUID = "10100003-5354-4f52-5a26-4249434b454c"
VOLCANO_BLE_FIRMWARE_VERSION_UUID = "10100004-5354-4f52-5a26-4249434b454c"

VOLCANO_STATUS_REGISTER_UUID = "1010000c-5354-4f52-5a26-4249434b454c"

VOLCANO_HEATER_ON_MASK = b"\x00\x20"
VOLCANO_PUMP_ON_MASK = b"\x20\x00"

class Volcano():
    """Volcano entity class"""

    def __init__(self, mac: str):
        self._mac = mac

        self._temperature = 0
        self._target_temperature = 0
        self._heater_on = False
        self._pump_on = False
        self._auto_off_time = None
        self._operation_hours = None
        self._serial_number = None
        self._firmware_version = None
        self._ble_firmware_version = None

    async def connect(self):
        self._conn = BTLEConnection(self._mac)
        await self._conn.connect()
        await self.initialize_values()
        await self.register_notifications()

    async def initialize_values(self):
        _LOGGER.info('Initializing values')

        self._temperature = await self.read_temperature()
        self._target_temperature = await self.read_target_temperature()

        _LOGGER.info(self._temperature)
        _LOGGER.info(self._target_temperature)

    async def register_notifications(self):
        await self._conn.start_notify(VOLCANO_TEMP_CURR_UUID, self.temperature_changed)
        await self._conn.start_notify(VOLCANO_TEMP_TARGET_UUID, self.target_temperature_changed)
        _LOGGER.info('Notifications registered')

    @property
    def temperature(self):
        return self._temperature

    def temperature_changed(self, sender, data):
        temperature = struct.unpack('<I', data)[0] / 10

        self._temperature = round(temperature)

    async def read_temperature(self):
        _LOGGER.debug('Reading current temperature')

        result = await self._conn.read_gatt_char(VOLCANO_TEMP_CURR_UUID)

        return round(int(struct.unpack('<I', result)[0] / 10))

    @property
    def target_temperature(self):
        return self._target_temperature

    async def set_target_temperature(self, temperature):
        data = struct.pack('<I', temperature * 10)

        # self._target_temperature = temperature

        _LOGGER.info(self._target_temperature)

        await self._conn.write_gatt_char(VOLCANO_TEMP_TARGET_UUID, data)

    def target_temperature_changed(self, sender, data):
        temperature = struct.unpack('<I', data)[0] / 10

        _LOGGER.debug(f"Target temperature changed: {temperature}")

        self._target_temperature = round(temperature)

    async def read_target_temperature(self):
        _LOGGER.debug('Reading target temperature')

        result = await self._conn.read_gatt_char(VOLCANO_TEMP_TARGET_UUID)

        return round(int(struct.unpack('<I', result)[0] / 10))

    @property
    def heater_on(self):
        return self._heater_on

    @property
    def pump_on(self):
        return self._pump_on

    def toggle_heater(self):
        self._heater_on = not self._heater_on

    def toggle_pump(self):
        self._pump_on = not self._pump_on
