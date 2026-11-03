# Printing

All STL files in [`../stl`](../stl) are already in their print orientation. **Never use "Auto orient"**:
each orientation was chosen so the part prints without supports. Textured PEI plate, no brim needed.

Tested on a Bambu Lab P1S in **black PLA Matte** (black also stops the PD trigger's LED shining through).
A final print in PETG-CF is planned but not yet tested; see "Other filaments" below.

| File | Orientation | Layer | Walls | Infill |
|---|---|---|---|---|
| `chassis.stl` | on its side, worm side on the bed | 0.20 | 4 | 15 % |
| `shell.stl` | outside of the DIN wall on the bed | 0.20 | 4 | 15 % |
| `back_plate.stl` | outside on the bed, light-seal rim up | 0.20 | 4 | 15 % |
| `carrier.stl` | top on the bed, legs up | 0.20 | 4 | 100 % |
| `cap.stl` | top on the bed | 0.20 | 4 | 100 % |
| `push_pins_x3.stl` (or the three single files) | lying down | 0.12 | 3 | 100 % |
| `pulley_44T_bore13.3.stl` | bottom flange on the bed | 0.12 | 4 | 100 % |
| `pulley_44T_bore13.2.stl` | spare with a tighter bore | 0.12 | 4 | 100 % |
| `pulley_bore_test_strip.stl` | flat | 0.12 | 4 | 100 % |

The only bridges are two short straight strips per corner screw in the carrier (the screw-head seats).

## Fit-critical dimensions

| What | Value | If it does not fit |
|---|---|---|
| Pulley bore on the 13.0 mm brass bush | 13.3 (black PLA Matte) | print the test strip (13.1–13.4) and pick the size that slides on without force and does not wobble; set `BORE` in `cad/pulley.py` |
| Pulley centre disc (clamped by the clutch) | 3.3 mm | 3.0 did not clamp hard enough |
| Push pin in its guide | 0.25 mm per side + 0.1 for hole shrink | pins should click every button and not rattle; `PIN_EXTRA` in `cad/housing.py` sets the length at the button end |
| Heat-set inserts | hole 3.8, 6 deep | |
| Motor collar | 22.4 for a 22 mm collar | |

## Other filaments

Shrinkage and fit change with the material. Before printing a whole set in a new filament, print small tests,
one question per print:

1. the **pulley bore test strip**,
2. a heat-set insert and an M3 hole,
3. the **push pins** with the carrier and cap.

PETG-CF softens at a much higher temperature than PLA, which gives more margin for summer heat and motor current.
PLA works at the current used (0.48 A while tracking), but do not run the motor current much higher in a PLA housing.

## Regenerating the STL files

```
pip install cadquery trimesh shapely rtree numpy
cd cad
python export_stl.py ../stl
```

`python housing.py` alone builds the model and prints collision checks between all parts.
