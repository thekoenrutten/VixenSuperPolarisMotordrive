// ESP32-C3 SuperMini as a USB-serial bridge to the LilyGO T-Motor (header P3), for the first upload.
// Arduino IDE: board "ESP32C3 Dev Module", Tools -> USB CDC On Boot: Enabled.
// Wiring: C3 GPIO10 (TX) -> P3 hole 2 (RX), C3 GPIO20 (RX) -> P3 hole 1 (TX), GND -> P3 hole 5.
// Leave 3.3 V unconnected: the T-Motor is powered from its PD trigger only.
// TX is on GPIO10 because GPIO21 on the board used here only reached 1.5 V when high.
// Uploading with the IDE button does not work through this bridge (the reset hits the C3);
// flash the exported .merged.bin with esptool --before no-reset --after no-reset.
//
// Copyright (c) 2026 Koen Rutten. MIT licence.

const int BRIDGE_RX = 20;
const int BRIDGE_TX = 10;
const uint32_t BAUD = 115200;

void setup() {
  Serial.setRxBufferSize(4096);
  Serial.begin(BAUD);                                    // USB to the computer
  Serial1.setRxBufferSize(4096);
  Serial1.begin(BAUD, SERIAL_8N1, BRIDGE_RX, BRIDGE_TX); // to P3
}

void loop() {
  uint8_t buf[256];
  size_t n = Serial.available();                         // computer -> T-Motor
  if (n) { if (n > sizeof(buf)) n = sizeof(buf); n = Serial.read(buf, n); Serial1.write(buf, n); }
  n = Serial1.available();                               // T-Motor -> computer
  if (n) { if (n > sizeof(buf)) n = sizeof(buf); n = Serial1.read(buf, n); Serial.write(buf, n); }
}
