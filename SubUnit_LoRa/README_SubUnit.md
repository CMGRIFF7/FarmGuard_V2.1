# FarmGuard - LoRaWAN Sub Unit

Firmware and information for the ESP32-based LoRaWAN field sub-units.

## Hardware
*   ESP32 with LoRa module (e.g., Heltec WiFi LoRa 32)
*   RFID Reader (e.g., MFRC522 for HF tags)
*   Battery & optional solar

## Firmware
Located in `SubUnit_Firmware/`.
Uses MCCI LoRaWAN LMIC library.

## Payload Format
(TODO: Define the LoRaWAN payload structure, e.g., Cayenne LPP or custom binary)
Example: `[NodeID_Byte][TagPresence_Byte][TagID_Bytes...]`