"""The bluetooth connection."""
import logging
import asyncio

from bleak import BleakScanner, BleakClient

_LOGGER = logging.getLogger(__name__)

class BTLEConnection():
    """BTLE Connection class"""

    def __init__(self, mac: str):
        self._mac = mac

    async def connect(self):
        device = await BleakScanner.find_device_by_address(self._mac, timeout=20.0, adapter="hci0")

        _LOGGER.info(device)

        _LOGGER.info('Before client initialization')
        self._conn = BleakClient(device)
        _LOGGER.info('Before client connect')
        await self._conn.connect()
        _LOGGER.info('After client connect')
        await asyncio.sleep(2.0)
        self._services = await self._conn.get_services()
    
    async def disconnect(self):
        await self._conn.disconnect()

    async def is_connected(self):
        return await self._conn.is_connected()

    async def get_service(self, service_uuid: str):
        return self.services.get_service(service_uuid)

    async def start_notify(self, char_uuid, callback):
        return await self._conn.start_notify(char_uuid, callback)

    async def stop_notify(self, char_uuid):
        return await self._conn.stop_notify(char_uuid)

    async def write_gatt_char(self, service, val):
        return await self._conn.write_gatt_char(service, val)

    async def read_gatt_char(self, service):
        return await self._conn.read_gatt_char(service)

    @property
    def services(self):
        return self._services
