"""The bluetooth connection."""
import logging
import asyncio

from bleak import BleakScanner, BleakClient
from bleak.backends.service import BleakGATTServiceCollection, BleakGATTService

_LOGGER = logging.getLogger(__name__)

class BTLEConnection():
    """BTLE Connection class"""

    def __init__(self, mac: str):
        self._mac = mac

    async def connect(self) -> bool:
        device = await BleakScanner.find_device_by_address(self._mac, timeout=20.0)

        _LOGGER.info(device)

        self._conn = BleakClient(device, disconnected_callback=self._disconnected_callback)
        result = await self._conn.connect()
        self._services = await self._conn.get_services()

        return result
    
    async def disconnect(self) -> bool:
        return await self._conn.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._conn.is_connected

    async def get_service(self, service_uuid: str) -> BleakGATTService:
        return self.services.get_service(service_uuid)

    async def start_notify(self, char_uuid, callback) -> None:
        return await self._conn.start_notify(char_uuid, callback)

    async def stop_notify(self, char_uuid) -> None:
        return await self._conn.stop_notify(char_uuid)

    async def write_gatt_char(self, service, val) -> None:
        return await self._conn.write_gatt_char(service, val)

    async def read_gatt_char(self, service) -> bytearray:
        return await self._conn.read_gatt_char(service)

    def _disconnected_callback(self, client: BleakClient) -> None:
        _LOGGER.error("DISCONNECTED FOR SOME REASON")
        _LOGGER.error(client)

    @property
    def services(self) -> BleakGATTServiceCollection:
        return self._services
