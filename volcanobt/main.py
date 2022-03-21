import asyncio
import sys
from bleak import BleakScanner, BleakClient

ADDRESS = "FB:17:6B:85:5B:C2"

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

async def main(ble_address: str):
    print(ble_address)
    device = await BleakScanner.find_device_by_address(ble_address, timeout=20.0)
    print(device)
    print("FUCK")
    if not device:
        raise BleakError(f"A device with address {ble_address} could not be found.")
    async with BleakClient(device) as client:
        print(client)
        await asyncio.sleep(2)
        result = await client.read_gatt_char(VOLCANO_TEMP_TARGET_UUID)
        print(result)
        print("Services:")
        for service in svcs:
            print(service)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) == 2 else ADDRESS))