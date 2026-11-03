/*
 * vixen_sp_ra.ino - Vixen SP RA drive, firmware 3.2
 * LilyGO T-Motor (ESP32-PICO-D4 + TMC2209), NEMA 17 with GT2 belt 20T : 44T.
 *
 * Controlled with the three buttons on the board (through the push pins in the back plate).
 * Seen from the back: left arrow = KEY1, round = KEY2, right arrow = KEY3.
 *
 *   nothing pressed                 track at 1x (sidereal)
 *   right / left arrow              5x with the stars / against them
 *   round + arrow                   100x
 *   both arrows for 3 s             reverse the tracking direction (stored)
 *   round held at power-up          WiFi + OTA on
 *
 * A button that is already pressed at power-up, or held longer than MAX_HOLD_S
 * (a sticking push pin), is ignored until it has been released.
 *
 * Serial monitor (115200), optional:
 *   x = driver off   a = driver on   w = WiFi + OTA on   d = reverse direction
 *
 * Arduino IDE: board "ESP32 PICO-D4", default partition scheme (with OTA),
 * core "esp32 by Espressif Systems" 3.x.
 *
 * Copyright (c) 2026 Koen Rutten. MIT licence, see LICENSE.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoOTA.h>
#include <Preferences.h>
#include "soc/gpio_reg.h"

// ===============================================================
// Settings
// ===============================================================

// Drive train
static const float PULLEY_MOTOR  = 20.0f;      // teeth on the motor
static const float PULLEY_WORM   = 44.0f;      // teeth on the worm shaft
static const float MICROSTEPS    = 51200.0f;   // per motor revolution (200 x 256)
static const float WORM_PERIOD_S = 598.36f;    // sidereal day / 144 (worm wheel teeth); calibrate on a star
static const float SIDEREAL_HZ   = MICROSTEPS * (PULLEY_WORM / PULLEY_MOTOR) / WORM_PERIOD_S;

// Tracking direction as long as nothing is stored (both arrows for 3 s reverses it).
static const bool  DIR_HIGH_WHEN_TRACKING = true;

// Speeds in x sidereal
static const float SPEED_SLOW   = 5.0f;
static const float SPEED_FAST   = 100.0f;
static const float RAMP_TIME_S  = 0.5f;        // from 0 to SPEED_FAST

// Buttons
static const uint32_t DEBOUNCE_MS = 30;
static const uint32_t REVERSE_MS  = 3000;
static const uint32_t MAX_HOLD_S  = 90;

// Current. VSENSE 1, Rsense 0.12: I_rms = (CS+1)/32 x 0.18 V / 0.14 ohm / sqrt 2
//   CS 16 = 0.48 A (~0.9 W in the NEMA 17)   CS 22 = 0.65 A
static const uint8_t  CS_TRACK         = 16;     // tracking and 5x
static const uint8_t  CS_FAST          = 22;     // above FAST_THRESHOLD
static const float    FAST_THRESHOLD   = 10.0f;  // |x sidereal|
static const uint32_t BACK_AFTER_MS    = 2000;   // this long below the threshold -> CS_TRACK
static const uint32_t MAX_FAST_CURRENT_S = 120;  // longer than this continuously -> CS_TRACK (heat)
static const bool     SPREADCYCLE      = false;  // false = StealthChop (silent)

// WiFi and OTA - change these if you like
static const char *WIFI_SSID     = "VixenSP-RA";
static const char *WIFI_PASSWORD = "vixensp-ra";
static const char *OTA_HOSTNAME  = "vixen-sp-ra";
static const char *OTA_PASSWORD  = "vixen";

// ===============================================================
// Hardware (LilyGO T-Motor)
// ===============================================================

static const int PIN_STEP   = 23;
static const int PIN_DIR    = 18;
static const int PIN_EN     = 2;    // active low; strapping pin
static const int PIN_SPREAD = 4;    // low: the register selects the chopper
static const int PIN_CLK    = 19;   // low: internal clock
static const int PIN_TX     = 27;   // through 1 kOhm to PDN_UART
static const int PIN_RX     = 26;
static const int PIN_KEY1   = 36;   // GPIO34-36: input only, pull-up on the board
static const int PIN_KEY2   = 34;
static const int PIN_KEY3   = 35;

static const uint8_t  DRIVER_ADDR    = 3;     // MS1 = MS2 = 1 (DIP switches in factory position)
static const uint32_t TMC_BAUD       = 115200;
static const uint8_t  REG_GCONF      = 0x00;
static const uint8_t  REG_IFCNT      = 0x02;
static const uint8_t  REG_IOIN       = 0x06;
static const uint8_t  REG_IHOLD_IRUN = 0x10;
static const uint8_t  REG_TPOWERDOWN = 0x11;
static const uint8_t  REG_CHOPCONF   = 0x6C;

// Types live at the top: the Arduino IDE inserts prototypes of all functions
// before the first function, and the types must be known there.
struct Button {
  int         pin;
  const char *name;
  bool        raw;           // last reading, true = pressed
  bool        stable;        // after debouncing
  bool        blocked;       // ignored until released
  uint32_t    tChange;
  uint32_t    tPressed;
};

enum State { WAIT_FOR_DRIVER, ACTIVE, MANUAL_OFF, OTA_BUSY };

HardwareSerial &TMC = Serial1;
static Preferences prefs;

// ===============================================================
// Step generator
// 50 kHz timer with a 31-bit phase accumulator. After every pulse STEP stays
// low for one tick, so at most 25 kHz; 100x is 18.8 kHz with 44T.
// ===============================================================

static const uint32_t F_TICK = 50000;
static const float    MAX_HZ = F_TICK * 0.45f;

static hw_timer_t      *stepTimer  = nullptr;
static volatile int32_t g_inc      = 0;      // + = tracking direction
static volatile int32_t g_position = 0;
static volatile bool    g_dirHigh  = DIR_HIGH_WHEN_TRACKING;
static volatile bool    g_dirSet   = true;

static void ARDUINO_ISR_ATTR onTick() {
  static uint32_t phase     = 0;
  static bool     pulseHigh = false;
  static int8_t   direction = 0;

  if (pulseHigh) {                           // end the pulse of the previous tick
    REG_WRITE(GPIO_OUT_W1TC_REG, 1UL << PIN_STEP);
    pulseHigh = false;
    return;
  }

  int32_t inc = g_inc;
  if (inc == 0) return;

  int8_t r = (inc > 0) ? 1 : -1;
  if (r != direction || g_dirSet) {          // set DIR first, pulse on the next tick
    bool high = (r > 0) ? g_dirHigh : !g_dirHigh;
    REG_WRITE(high ? GPIO_OUT_W1TS_REG : GPIO_OUT_W1TC_REG, 1UL << PIN_DIR);
    direction = r;
    g_dirSet  = false;
    return;
  }

  phase += (inc > 0) ? (uint32_t)inc : (uint32_t)(-inc);
  if (phase & 0x80000000UL) {
    phase &= 0x7FFFFFFFUL;
    REG_WRITE(GPIO_OUT_W1TS_REG, 1UL << PIN_STEP);
    pulseHigh = true;
    g_position += r;
  }
}

// factor in x sidereal, + = with the stars
static void setSpeed(float factor) {
  float maxF = MAX_HZ / SIDEREAL_HZ;
  factor = constrain(factor, -maxF, maxF);
  double hz   = (double)factor * SIDEREAL_HZ;
  double avail = (double)F_TICK - fabs(hz);   // the tick after each pulse does not count
  g_inc = (int32_t)llround(hz * 2147483648.0 / avail);
}

static void setDirection(bool high, bool store) {
  g_dirHigh = high;
  g_dirSet  = true;
  if (store) {
    prefs.putBool("dirHoog", high);           // key name kept for compatibility with earlier builds
    Serial.printf(">> tracking direction reversed and stored (DIR %s).\n", high ? "high" : "low");
  }
}

// ===============================================================
// TMC2209 over UART
// ===============================================================

static uint8_t tmcCRC(const uint8_t *data, uint8_t len) {
  uint8_t crc = 0;
  for (uint8_t i = 0; i < len; i++) {
    uint8_t b = data[i];
    for (uint8_t j = 0; j < 8; j++) {
      crc = ((crc >> 7) ^ (b & 0x01)) ? (uint8_t)((crc << 1) ^ 0x07) : (uint8_t)(crc << 1);
      b >>= 1;
    }
  }
  return crc;
}

static bool tmcRead(uint8_t reg, uint32_t &value) {
  while (TMC.available()) TMC.read();
  uint8_t req[4] = { 0x05, DRIVER_ADDR, (uint8_t)(reg & 0x7F), 0 };
  req[3] = tmcCRC(req, 3);
  TMC.write(req, 4);
  TMC.flush();

  uint8_t  buf[24];
  uint8_t  n  = 0;
  uint32_t t0 = millis();
  while ((millis() - t0) < 20) {
    if (!TMC.available()) continue;
    uint8_t b = (uint8_t)TMC.read();
    if (n >= sizeof(buf)) continue;
    buf[n++] = b;
    if (n < 12) continue;                    // echo (4) + reply (8)
    for (uint8_t i = 0; i + 8 <= n; i++) {
      if (buf[i] != 0x05 || buf[i + 1] != 0xFF || buf[i + 2] != reg) continue;
      if (tmcCRC(&buf[i], 7) != buf[i + 7]) continue;
      value = ((uint32_t)buf[i + 3] << 24) | ((uint32_t)buf[i + 4] << 16) |
              ((uint32_t)buf[i + 5] <<  8) |  (uint32_t)buf[i + 6];
      return true;
    }
  }
  return false;
}

static void tmcWrite(uint8_t reg, uint32_t value) {
  uint8_t d[8] = { 0x05, DRIVER_ADDR, (uint8_t)(reg | 0x80),
                   (uint8_t)(value >> 24), (uint8_t)(value >> 16),
                   (uint8_t)(value >> 8),  (uint8_t)value, 0 };
  d[7] = tmcCRC(d, 7);
  TMC.write(d, 8);
  TMC.flush();
  delay(2);
  while (TMC.available()) TMC.read();
}

static bool readIfcnt(uint8_t &counter) {
  uint32_t v;
  if (!tmcRead(REG_IFCNT, v)) return false;
  counter = (uint8_t)v;
  return true;
}

static void writeCurrentRegister(uint8_t cs) {
  tmcWrite(REG_IHOLD_IRUN, (uint32_t)cs | ((uint32_t)cs << 8));   // IHOLD = IRUN
}

// Configures the driver; true only if IFCNT proves that all 4 writes arrived.
static bool configure() {
  uint32_t v;
  if (!tmcRead(REG_IOIN, v) || (v >> 24) != 0x21) return false;
  Serial.printf("Driver found at address %u (version 0x21).\n", DRIVER_ADDR);

  uint8_t count0;
  if (!readIfcnt(count0)) return false;

  uint32_t gconf;
  if (!tmcRead(REG_GCONF, gconf)) return false;
  gconf &= ~(1UL << 0);                      // I_scale_analog off: the VREF trimmer does nothing
  gconf |=  (1UL << 6) | (1UL << 7);         // pdn_disable, mstep_reg_select
  if (SPREADCYCLE) gconf |= (1UL << 2); else gconf &= ~(1UL << 2);
  tmcWrite(REG_GCONF, gconf);

  uint32_t chop;
  if (!tmcRead(REG_CHOPCONF, chop)) return false;
  chop &= ~(0xFUL << 24);                    // MRES 0 = 1/256
  chop |=  (1UL << 28) | (1UL << 17);        // intpol, VSENSE
  tmcWrite(REG_CHOPCONF, chop);

  writeCurrentRegister(CS_TRACK);
  tmcWrite(REG_TPOWERDOWN, 20);

  delay(10);
  uint8_t count1;
  if (!readIfcnt(count1)) return false;
  if (count1 != (uint8_t)(count0 + 4)) {
    Serial.printf("IFCNT %u -> %u, expected +4. Configuration NOT confirmed.\n", count0, count1);
    return false;
  }
  Serial.printf("Configuration OK, CS %u/%u, %s.\n", CS_TRACK, CS_FAST,
                SPREADCYCLE ? "SpreadCycle" : "StealthChop");
  return true;
}

static bool driverHealthy() {
  uint32_t v;
  return tmcRead(REG_GCONF, v) && ((v >> 7) & 1);   // mstep_reg_select still set
}

// ===============================================================
// Current per speed
// ===============================================================

static uint8_t  csNow          = CS_TRACK;
static uint32_t tBelowThresh   = 0;
static uint32_t tFastSince     = 0;
static bool     fastBlocked    = false;

static void setCurrent(uint8_t cs) {
  if (cs == csNow) return;
  writeCurrentRegister(cs);
  csNow = cs;
}

static void regulateCurrent(uint32_t now, float factor) {
  if (fabsf(factor) > FAST_THRESHOLD) {
    tBelowThresh = now;
    if (csNow != CS_FAST && !fastBlocked) { tFastSince = now; setCurrent(CS_FAST); }
    if (csNow == CS_FAST && (now - tFastSince) >= MAX_FAST_CURRENT_S * 1000UL) {
      setCurrent(CS_TRACK);
      fastBlocked = true;
      Serial.println(">> fast for too long: current back to tracking level (heat).");
    }
  } else if ((now - tBelowThresh) >= BACK_AFTER_MS) {
    setCurrent(CS_TRACK);
    fastBlocked = false;
  }
}

// ===============================================================
// Buttons
// ===============================================================

static Button btnL = { PIN_KEY1, "left arrow (KEY1)",  false, false, false, 0, 0 };
static Button btnM = { PIN_KEY2, "round (KEY2)",       false, false, false, 0, 0 };
static Button btnR = { PIN_KEY3, "right arrow (KEY3)", false, false, false, 0, 0 };

static void buttonInit(Button &b, uint32_t now) {
  pinMode(b.pin, INPUT);
  b.raw = b.stable = b.blocked = (digitalRead(b.pin) == LOW);
  b.tChange = b.tPressed = now;
  if (b.blocked)
    Serial.printf("%s pressed at power-up: ignored until released.\n", b.name);
}

static void buttonRead(Button &b, uint32_t now) {
  bool r = (digitalRead(b.pin) == LOW);
  if (r != b.raw) { b.raw = r; b.tChange = now; }

  if (b.stable != b.raw && (now - b.tChange) >= DEBOUNCE_MS) {
    b.stable = b.raw;
    if (b.stable) {
      b.tPressed = now;
    } else if (b.blocked) {
      b.blocked = false;
      Serial.printf("%s released: active again.\n", b.name);
    }
  }

  if (b.stable && !b.blocked && (now - b.tPressed) >= MAX_HOLD_S * 1000UL) {
    b.blocked = true;
    Serial.printf("!! %s held for %lu s: sticking pin? Ignored until released.\n",
                  b.name, (unsigned long)MAX_HOLD_S);
  }
}

static bool active(const Button &b) { return b.stable && !b.blocked; }

// Target speed in x sidereal
static uint32_t tBothArrows = 0;      // 0 = not both pressed
static bool     reversed    = false;  // wait until both arrows are released

static float targetSpeed(uint32_t now) {
  bool L = active(btnL), R = active(btnR);

  if (L && R) {                          // both arrows: 1x, after 3 s reverse
    if (tBothArrows == 0) tBothArrows = now | 1;
    if (!reversed && (now - tBothArrows) >= REVERSE_MS) {
      setDirection(!g_dirHigh, true);
      reversed = true;
    }
    return 1.0f;
  }
  tBothArrows = 0;

  if (reversed) {
    if (!btnL.stable && !btnR.stable) reversed = false;
    return 1.0f;
  }

  float speed = active(btnM) ? SPEED_FAST : SPEED_SLOW;
  if (R) return  speed;
  if (L) return -speed;
  return 1.0f;
}

// ===============================================================
// State, WiFi and OTA
// ===============================================================

static State    state         = WAIT_FOR_DRIVER;
static float    currentFactor = 0.0f;
static uint32_t tAttempt = 0, tCheck = 0, tControl = 0, tStatus = 0;
static bool     wifiOn = false;

static void driverOff() {
  g_inc = 0;
  digitalWrite(PIN_EN, HIGH);
  currentFactor = 0.0f;
}

static void driverOn() {
  g_inc = 0;
  currentFactor = 0.0f;
  csNow         = CS_TRACK;              // set by configure()
  fastBlocked   = false;
  digitalWrite(PIN_EN, LOW);
  delay(200);                            // StealthChop first measures the motor
  tControl = tCheck = millis();
}

static void startWifi() {
  if (wifiOn) return;
  WiFi.mode(WIFI_AP);
  WiFi.softAP(WIFI_SSID, WIFI_PASSWORD);
  delay(100);

  ArduinoOTA.setHostname(OTA_HOSTNAME);
  ArduinoOTA.setPassword(OTA_PASSWORD);
  ArduinoOTA.onStart([]() {
    driverOff();
    state = OTA_BUSY;
    Serial.println("OTA: update started, driver off.");
  });
  ArduinoOTA.onEnd([]() { Serial.println("\nOTA: done, restarting."); });
  ArduinoOTA.onProgress([](unsigned int done, unsigned int total) {
    static unsigned int prev = 101;
    unsigned int pct = total ? (done * 100U / total) : 0;
    if (pct / 10 != prev / 10) { prev = pct; Serial.printf("OTA: %u%%\n", pct); }
  });
  ArduinoOTA.onError([](ota_error_t e) {
    Serial.printf("OTA: error %u. Driver stays off; type a to restart it.\n", (unsigned)e);
    state = MANUAL_OFF;
  });
  ArduinoOTA.begin();

  wifiOn = true;
  Serial.printf("WiFi ON: \"%s\" / \"%s\", address %s; OTA port \"%s\", password \"%s\"\n",
                WIFI_SSID, WIFI_PASSWORD, WiFi.softAPIP().toString().c_str(),
                OTA_HOSTNAME, OTA_PASSWORD);
}

static void readSerial(uint32_t now) {
  while (Serial.available()) {
    switch (Serial.read()) {
      case 'x': case 'X':
        driverOff();
        state = MANUAL_OFF;
        Serial.println(">> driver switched off manually. Type a to switch it on again.");
        break;
      case 'a': case 'A':
        if (state == MANUAL_OFF) { state = WAIT_FOR_DRIVER; tAttempt = now - 2000; }
        break;
      case 'w': case 'W': startWifi(); break;
      case 'd': case 'D': setDirection(!g_dirHigh, true); break;
    }
  }
}

static void printStatus() {
  Serial.printf("speed %7.2fx | buttons %c%c%c | position %ld | CS %u | DIR %s | wifi %s\n",
                currentFactor,
                active(btnL) ? 'L' : '-', active(btnM) ? 'M' : '-', active(btnR) ? 'R' : '-',
                (long)g_position, csNow, g_dirHigh ? "high" : "low", wifiOn ? "on" : "off");
}

// ===============================================================

void setup() {
  digitalWrite(PIN_EN, HIGH);            // driver off, even before pinMode
  pinMode(PIN_EN, OUTPUT);
  digitalWrite(PIN_EN, HIGH);
  for (int p : { PIN_STEP, PIN_DIR, PIN_SPREAD, PIN_CLK }) {
    pinMode(p, OUTPUT);
    digitalWrite(p, LOW);
  }

  Serial.begin(115200);
  delay(500);
  TMC.begin(TMC_BAUD, SERIAL_8N1, PIN_RX, PIN_TX);
  delay(100);

  Serial.println("\n=== Vixen SP RA - firmware 3.2 (NEMA 17, belt 20T:44T, 1/256) ===");
  Serial.printf("Tracking %.3f Hz; %.0fx = %.1f kHz\n",
                SIDEREAL_HZ, SPEED_FAST, SPEED_FAST * SIDEREAL_HZ / 1000.0f);

  prefs.begin("vixensp", false);
  setDirection(prefs.getBool("dirHoog", DIR_HIGH_WHEN_TRACKING), false);

  uint32_t now = millis();
  buttonInit(btnL, now);
  buttonInit(btnM, now);
  buttonInit(btnR, now);

  if (btnM.stable) startWifi();
  else Serial.println("WiFi off (hold round at power-up, or type w).");

  stepTimer = timerBegin(1000000);                   // 1 MHz
  timerAttachInterrupt(stepTimer, &onTick);
  timerAlarm(stepTimer, 1000000 / F_TICK, true, 0);  // every 20 us

  tAttempt = millis() - 2000;
}

void loop() {
  if (wifiOn) ArduinoOTA.handle();
  if (state == OTA_BUSY) return;

  uint32_t now = millis();
  readSerial(now);
  buttonRead(btnL, now);
  buttonRead(btnM, now);
  buttonRead(btnR, now);

  switch (state) {
    case MANUAL_OFF:
    case OTA_BUSY:
      return;

    case WAIT_FOR_DRIVER:
      if ((now - tAttempt) >= 2000) {
        tAttempt = now;
        if (configure()) {
          driverOn();
          state = ACTIVE;
          Serial.println("Driver on, tracking started.");
        } else {
          Serial.println("Waiting for the driver (motor supply present?)...");
        }
      }
      return;

    case ACTIVE:
      break;
  }

  if ((now - tCheck) >= 1000) {
    tCheck = now;
    if (!driverHealthy()) {
      driverOff();
      state    = WAIT_FOR_DRIVER;
      tAttempt = now;
      Serial.println("!! Driver not responding or was reset. Reconfiguring.");
      return;
    }
  }

  if ((now - tControl) >= 20) {                       // 50 times a second
    float dt = (now - tControl) / 1000.0f;
    if (dt > 0.1f) dt = 0.1f;
    tControl = now;
    float step = SPEED_FAST / RAMP_TIME_S * dt;
    currentFactor += constrain(targetSpeed(now) - currentFactor, -step, step);
    setSpeed(currentFactor);
    regulateCurrent(now, currentFactor);
  }

  if ((now - tStatus) >= 1000) {
    tStatus = now;
    printStatus();
  }
}
