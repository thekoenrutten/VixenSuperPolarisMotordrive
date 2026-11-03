# Bill of materials

## Electronics and drive

| Qty | Part | Notes |
|---|---|---|
| 1 | **LilyGO TTGO T-Motor** (ESP32-PICO-D4 + TMC2209) | DIP switches in the factory position → driver address 3. No heatsink needed. Keep the 4 screws and the white spacers of its plastic case: the carrier is mounted with them |
| 1 | **NEMA 17 stepper**, 1.8°, 40 mm long | used: Wantai 42BYGHW609, 0.42 Nm at 1.7 A, ~1.5 Ω per coil. Any 42 × 40 mm motor with a 22 mm centring collar and M3 holes at 31 mm pitch fits |
| 1 | GT2 pulley, **20 teeth**, 6 mm belt, bore for the motor shaft (5 mm) | |
| 1 | GT2 closed belt, **6 mm wide, 158 mm** (79 teeth) | |
| 1 | USB-C PD trigger board, **fixed 9 V** | used: TinyTronics 006497. The screw terminal is desoldered; its wires go to the T-Motor P1 cable |
| 1 | USB-C PD power bank that supplies 9 V | plus a USB-C cable |

## Printed parts

See [printing.md](printing.md): chassis, shell, back plate, carrier, cap, three push pins and the 44T worm pulley.

## Hardware

| Qty | Part | Where |
|---|---|---|
| 5 | M3 heat-set insert, for a 3.8 mm hole, 6 mm deep | chassis 2 (back), shell 3 (2 front, 1 back) |
| 4 | M3 × 6 | motor to the front wall |
| 2 | M3 × 8 | shell from the front |
| 3 | M3 × 6 | back plate |
| 4 | screws + spacers from the LilyGO case | carrier on the T-Motor board |

The housing clamps onto the mount with the mount's own dovetail clamp screws. The pulley is held by the
original Vixen slip clutch and thumbscrew; the brass worm-shaft gear comes out and is kept.

## Tools

Soldering iron (PD trigger wires, heat-set inserts), multimeter, a computer with the Arduino IDE.
For the very first upload the T-Motor needs a USB-serial link; see [electronics-firmware.md](electronics-firmware.md).
