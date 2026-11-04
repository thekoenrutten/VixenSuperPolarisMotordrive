# Assembly

Directions: **front** is the pulley side (the motor shaft comes out of the front wall). **Seen from the back**,
the worm side of the housing is on the left and the DIN wall (with the USB-C opening) on the right.
On the mount, keep the **RA axis** and the **dec axis** apart: this drive goes on the RA worm.

> Never plug or unplug the motor while the power bank is connected (VM on). It can destroy the TMC2209.

## 1. Before you start

1. Press the heat-set inserts in: 2 in the back of the chassis, 3 in the shell (2 at the front, 1 at the back).
2. Check the motor with a multimeter: pins 1-2 and pins 3-4 of its plug must each be one coil (a few ohms),
   and there must be no connection between the two pairs.
3. Prepare the PD trigger: desolder its screw terminal, cut the plug of the **P1 cable that comes with the T-Motor**
   off with a few centimetres of wire, and solder wire 1 (+VM) to the PD trigger's + and wire 2 (GND) to −.
   Insulate wires 3–6. Check +9 V between pin 1 and pin 2 with the multimeter before plugging it into the T-Motor.
   See the [wiring diagram](electronics-firmware.md#wiring).
4. Flash the firmware once (see [electronics-firmware.md](electronics-firmware.md)). After that, updates go over WiFi.

## 2. Housing

1. **Carrier on the T-Motor** with the 4 screws and white spacers from the LilyGO case. Plug in the motor JST and P1.
2. Fit the 20T pulley on the motor. Put the **motor, with the T-Motor and carrier behind it**, into the chassis from above;
   4 × M3 × 6 through the front wall. Coil the motor cable on the worm-wheel side.
3. **Shell** from above. Let it drop straight down: the three ribs on the inside of the DIN wall fall into slots in
   the floor. If it does not go all the way, do not force it: look for strings or elephant's foot in a slot.
   2 × M3 × 8 from the front.
4. Stand the housing on its front (back up). Drop the **push pins** into their three holes: left arrow left, round in the
   middle, right arrow right, collar up (towards the groove). Each pin only fits one way.
5. Lay the **PD trigger** flat on the carrier, clamp end towards the worm side, components up, and slide it
   **2.3 mm towards the DIN wall** until the USB-C socket is flush with the outside.
6. Press the **cap** straight on from the back: its three pegs go into the screw holes (lower left, lower right,
   upper left) and clamp.
7. **Back plate** straight on from the back; 3 × M3 × 6.

Check: every button clicks and springs back, nothing rattles, the symbols stick out about 3 mm.

## 3. On the mount

1. Remove the brass worm-shaft gear from the slip clutch. Put the **44T pulley** on the hub, the clamping bush on top,
   and tighten the thumbscrew. With the thumbscrew loose, the worm should turn by hand while the pulley stays put.
2. Put the belt around both pulleys.
3. Slide the housing onto the dovetail and move it away from the worm until the belt is taut with a little give;
   tighten the clamp screws.
4. Turn the RA axis through a full circle with the lock closed: the lock knob must not touch the groove in the top of the housing.
5. Balance the RA axis slightly east-heavy, so the gears always mesh on the same side.
6. Power on and check the direction: hold **round + right arrow** (100×); the telescope must move like the sun,
   east → south → west (northern hemisphere). Wrong way: hold both arrows for 3 s, release, try again.

## 4. Sidereal rate (optional calibration)

`WORM_PERIOD_S` in the firmware (598.36 s) is the theoretical worm period. To calibrate, track a star near the
celestial equator at high magnification for a few worm periods and measure the drift; adjust the value and
update over WiFi.
