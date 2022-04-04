"""The bluetooth connection."""
import logging

from bleak import BleakScanner, BleakClient

_LOGGER = logging.getLogger(__name__)

class BTLEConnection():
    """BTLE Connection class"""

    def __init__(self, mac: str):
        self._mac = mac

    async def connect(self):
        device = await BleakScanner.find_device_by_address(self._mac, timeout=20.0)

        self._conn = BleakClient(device)
        await self._conn.connect()
        self._services = await self._conn.get_services()
    
    async def disconnect(self):
        await self._conn.disconnect()

    async def is_connected(self):
        return await self._conn.is_connected()

    async def get_service(self, service_uuid: str):
        return await self.services.get_service(service_uuid)

    async def start_notify(self, char_uuid, callback):
        return await self._conn.start_notify(char_uuid, callback)

    async def write_gatt_char(self, service_uuid: str, val):
        return await self._conn.write_gatt_char(service_uuid, val, True)

    async def read_gatt_char(self, service_uuid: str):
        return await self._conn.read_gatt_char(service_uuid)

    @property
    def services(self):
        return self._services
