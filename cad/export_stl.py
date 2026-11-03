"""
Export every printable part as an STL in its print orientation (as it should lie on the bed),
plus STEP files of the pulley and of the assembled housing.

    python export_stl.py ../stl

Never use "Auto orient" in the slicer: the orientations below are part of the design.
"""
import os, sys
import cadquery as cq

import housing as H
import pulley as P

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stl")
os.makedirs(out, exist_ok=True)


def flat(w):
    bb = w.val().BoundingBox()
    return w.translate((-bb.xmin, -bb.ymin, -bb.zmin))

def down(w, side):
    """Rotate so that the given side of the part faces the bed (-Z)."""
    if side == "-x":
        w = w.rotate((0, 0, 0), (0, 1, 0), -90)
    elif side == "+x":
        w = w.rotate((0, 0, 0), (0, 1, 0), 90)
    elif side == "+z":
        w = w.rotate((0, 0, 0), (1, 0, 0), 180)
    elif side != "-z":
        raise ValueError(side)
    return flat(w)

parts = {
    "chassis":          (H.CHASSIS,    "-x"),   # on its side, worm side on the bed
    "shell":            (H.SHELL,      "+x"),   # outside of the DIN wall on the bed
    "back_plate":       (H.BACK_PLATE, "+z"),   # outside on the bed, rim up
    "carrier":          (H.CARRIER,    "+z"),   # top on the bed, legs up
    "cap":              (H.CAP,        "+z"),   # top on the bed
    "push_pin_1_left":  (H.PINS[0],    "-x"),   # lying down, flat side on the bed
    "push_pin_2_round": (H.PINS[1],    "-x"),
    "push_pin_3_right": (H.PINS[2],    "-x"),
}
for name, (w, side) in parts.items():
    path = os.path.join(out, f"{name}.stl")
    cq.exporters.export(down(w, side), path, tolerance=0.01, angularTolerance=0.1)
    print("wrote", path)

# three pins on one plate
plate = None
for i, (w, side) in enumerate(parts[k] for k in ("push_pin_1_left", "push_pin_2_round", "push_pin_3_right")):
    p = down(w, side).translate((0, i * 12.0, 0))
    plate = p if plate is None else plate.union(p)
cq.exporters.export(plate, os.path.join(out, "push_pins_x3.stl"), tolerance=0.01, angularTolerance=0.1)

for bore in P.BORE_VARIANTS:
    body, _, _ = P.make_pulley(bore=bore)
    path = os.path.join(out, f"pulley_44T_bore{bore:.1f}.stl")
    cq.exporters.export(body, path, tolerance=0.01, angularTolerance=0.1)
    print("wrote", path)
cq.exporters.export(P.make_test_strip(), os.path.join(out, "pulley_bore_test_strip.stl"),
                    tolerance=0.01, angularTolerance=0.1)

step_dir = os.path.join(out, "..", "cad", "step")
os.makedirs(step_dir, exist_ok=True)
cq.exporters.export(P.make_pulley()[0], os.path.join(step_dir, "pulley_44T_bore13.3.step"))
asm = cq.Assembly()
for n, w, k in (("chassis", H.CHASSIS, "steelblue"), ("shell", H.SHELL, "goldenrod"),
                ("back_plate", H.BACK_PLATE, "seagreen"), ("carrier", H.CARRIER, "purple"), ("cap", H.CAP, "orange")):
    asm.add(w, name=n, color=cq.Color(k))
for i, p in enumerate(H.PINS):
    asm.add(p, name=f"push_pin_{i+1}", color=cq.Color("red"))
asm.export(os.path.join(step_dir, "housing_assembly.step"))
print("done")
