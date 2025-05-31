// FarmGuard_V2/SubUnit_LoRa/SubUnit_Firmware/SubUnit_Firmware.ino
/*
 * Placeholder for ESP32 + LoRa + RFID (e.g., MFRC522) Sub Unit Firmware.
 * This will require LoRaWAN libraries (like MCCI LMIC) and RFID libraries.
 */

// TODO: Include necessary libraries
// #include <lmic.h>
// #include <hal/hal.h>
// #include <SPI.h>
// #include <MFRC522.h> // For MFRC522 example

// TODO: Define LoRaWAN Keys (OTAA or ABP) - store these securely!
// static const u1_t PROGMEM APPEUI[8]= { 0x00, ... };
// static const u1_t PROGMEM DEVEUI[8]= { 0x00, ... };
// static const u1_t PROGMEM APPKEY[16] = { 0x00, ... };

// TODO: Define RFID reader pins
// #define SS_PIN  5  // ESP32 typical SS pin for SPI
// #define RST_PIN 27 // ESP32 typical RST pin

// MFRC522 mfrc522(SS_PIN, RST_PIN); // Create MFRC522 instance

// TODO: LoRaWAN job and pin mapping
// const lmic_pinmap lmic_pins = { ... };

void setup() {
    Serial.begin(115200);
    while (!Serial); // Wait for serial port to connect
    Serial.println("FarmGuard SubUnit Booting...");

    // TODO: Initialize SPI
    // SPI.begin();

    // TODO: Initialize MFRC522
    // mfrc522.PCD_Init();
    // Serial.println("RFID Reader Initialized.");

    // TODO: Initialize LoRaWAN (os_init, setup channels, join)
    // os_init();
    // LMIC_reset();
    // LMIC_setClockError(MAX_CLOCK_ERROR * 1 / 100); // Example
    // LMIC_startJoining();

    Serial.println("Setup complete. Entering loop.");
}

void loop() {
    // TODO: Handle LoRaWAN (os_runloop_once)
    // os_runloop_once();

    // TODO: Implement logic to:
    // 1. Periodically wake up (if using deep sleep)
    // 2. Scan for RFID tags
    //    if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    //        String tagId = "";
    //        for (byte i = 0; i < mfrc522.uid.size; i++) {
    //            tagId += String(mfrc522.uid.uidByte[i], HEX);
    //        }
    //        Serial.print("Tag detected: "); Serial.println(tagId);
    //        // TODO: Prepare and send LoRaWAN payload with tagId
    //        // Example: LMIC_setTxData2(1, (uint8_t*)tagId.c_str(), tagId.length(), 0);
    //        mfrc522.PICC_HaltA(); // Halt PICC
    //        mfrc522.PCD_StopCrypto1(); // Stop encryption on PCD
    //    }
    // 3. If tag found, prepare and send LoRaWAN packet
    // 4. Go back to deep sleep to save power

    delay(10000); // Placeholder delay
    Serial.println("Looping... (Replace with actual logic)");
}

// TODO: Add LoRaWAN event handlers (onEvent)
/*
void onEvent (ev_t ev) {
    // ...
}
*/