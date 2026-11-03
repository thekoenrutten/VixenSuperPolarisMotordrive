"""
Vixen SP RA drive - housing for a NEMA 17 with a LilyGO T-Motor mounted behind it (design P10i, final).

Parts
  chassis      front wall with the motor, bottom with the dovetail, wall on the worm side
  shell        top wall (with the groove for the RA lock knob) and the wall on the DIN side
  back_plate   back wall with windows for the three button symbols and a light-seal rim
  carrier      screwed onto the T-Motor board with LilyGO's 4 corner screws; guides the push pins
  cap          clips onto the carrier; holds the pin collars and the clamp end of the USB-C PD trigger
  pin_1..3     one-piece push pins that press the T-Motor's KEY1/KEY2/KEY3 buttons through the back plate

Coordinates (housing): X width (0 = outside of the worm side -> DIN side), Y height (0 = base),
Z depth (0 = front face, where the pulley sticks out).
"Seen from the back" the worm side is on the left. Buttons from the back:
left arrow = KEY1, round = KEY2, right arrow = KEY3.

The LilyGO case (Shell.stl, MIT licence, Xinyuan-LilyGO/T-Motor) is used only for its outline,
as a safe boundary for the carrier above the components on the board.
Case coordinates -> housing: X = shaft_x - y, Y = shaft_y + x, Z = case_z0 + z.

Design history in short (P9e .. P10i):
  - Every part has a print orientation in which everything grows upward: no ledges, no T-slots.
  - Push pin = one piece printed lying down; 0.25 clearance per side in the guide, 0.5 around the
    collar, 1.4 mm free travel. Long edges chamfered 0.5 x 45 deg; arrow tips rounded r 0.4.
    There is no spring: the button pushes the pin out. The chosen set is 0.4 mm longer ("long04").
  - Lead-in of 0.4 x 45 deg (two 0.2 steps) on the bed side of every hole (elephant's foot).
  - Cap reaches to 0.2 below the back plate, so the back plate keeps it in place.
  - Light-seal rim (1.2 x 2.0) on the inside of the back plate against the PD trigger's LED.
  - Three wedges at the bottom of the DIN wall drop 1.0 mm into slots in the chassis floor.
  - Outer edges chamfered 1.0 x 45 deg (except the worm-side bottom edge, where the dovetail runs out).

Run:  python housing.py [output_dir]   (needs cadquery, trimesh, shapely, numpy)
Use export_stl.py to write every part in its print orientation.
"""
import cadquery as cq
import itertools, math, os
import numpy as np
import shapely.geometry as sg

HERE = os.path.dirname(os.path.abspath(__file__))
SHELL_STL = os.environ.get("SHELL_STL", os.path.join(HERE, "third_party", "lilygo", "Shell.stl"))

# ---------------- housing ----------------
housing_x, housing_y, housing_z = 58.0, 58.0, 67.0
front_wall, wall, wall_worm = 3.0, 2.0, 1.5
din_in, top_in, back_in = housing_x - wall, housing_y - wall, housing_z - wall      # 56, 56, 65
dt_x0, dt_x1, dt_z0, dt_width, dt_height, dt_neck = 0.0, 48.5, 22.0, 20.0, 8.0, 11.5   # dovetail (28 deg)
insert_hole, insert_depth = 3.8, 6.0          # M3 heat-set inserts
m3_clear, m3_lying = 3.4, 3.8
motor_w, motor_l, motor_tol = 42.3, 40.0, 0.5
shaft_x, shaft_y = 32.5, 24.75
collar_hole, hole_pitch = 22.4, 31.0
motor_back = front_wall + motor_l + motor_tol           # 43.5
case_thick = 12.0                                       # measured: motor -> back of the LilyGO case
case_z0 = motor_back + case_thick - 9.5                 # 46.0
board_z = case_z0 + 1.5                                 # 47.5 top of the board
head_z = case_z0 + 3.0                                  # 49.0 underside of the screw head (as in the case)
corner = 15.5
tm_edge = 39.1 / 2
jst_over, p1_over = 10.9, 11.2
jst_ys, p1_ys = (-6.2, 6.2), (-7.2, 10.2)
plug_z = (case_z0 + 1.0, case_z0 + 8.0)
button_x_case, button_y_case = -19.2, (7.3, 0.0, -7.15)
button_top = case_z0 + 4.3                              # 50.3 top of the button [ASSUMPTION: from the case]
protrusion = 3.0                                        # symbol sticks out of the back plate
window_clear = 0.4
# PD trigger (USB-C opening in the shell)
pd_l, pd_w, pd_t = 42.5, 18.0, 1.6
pd_comp, pd_solder = 4.4, 1.0
usb_w, usb_h, usb_out, usb_l = 8.94, 3.2, 1.2, 7.0
pd_x1 = housing_x - usb_out                 # 56.8
pd_x0 = pd_x1 - pd_l                        # 14.3
slide_in = 2.3
pd_y0, pd_y1 = 13.0, 31.0
pd_z0 = case_z0 + 10.5                      # 56.5
pd_z1 = pd_z0 + pd_t                        # 58.1
usb_y = (pd_y0 + pd_y1) / 2
usb_z = pd_z1 + usb_h / 2
worm_x, worm_y = -13.16, 33.5
front_bolt_din = (51.0, 51.3)
front_bolt_mid = (31.0, 51.6)
back_bolts = {"chassis_low": (5.2, 6.5), "chassis_high": (5.2, 44.0), "shell_din": (52.0, 51.0)}
groove_y, groove_margin, groove_thick = 50.0, 2.0, 2.1    # groove for the RA lock knob
arc_chord, arc_sag = 64.5, 12.0
arc_r = ((arc_chord / 2) ** 2 + arc_sag ** 2) / (2 * arc_sag)
arc_cx, arc_cz = arc_sag - arc_r, arc_chord / 2
groove_r = arc_r + groove_margin

def cs(xs, ys):
    """Case coordinates -> housing X, Y."""
    return shaft_x - ys, shaft_y + xs

button_xy = [cs(button_x_case, y) for y in button_y_case]     # (25.2 / 32.5 / 39.65 ; 5.55)
ky = button_xy[0][1]
lx, mx, rx = (p[0] for p in button_xy)
corners = [cs(sx, sy) for sx, sy in itertools.product((-corner, corner), repeat=2)]

# ---------------- CARRIER ----------------
plate_z0, plate_z1 = case_z0 + 8.6, pd_z0     # 54.6 .. 56.5 (below: above the old case plate; above: PD trigger)
leg_in, leg_out = 3.5, 4.5                    # leg: square from corner-3.5 (inward) to +4.5 (outward)
head_hole = 5.9                               # screw head 5.5 + screwdriver
slot_w = 3.4                                  # M3 in a slot (seat = two straight strips = short bridges)
pd_window = (pd_x0 - slide_in + 1.0, 60.0, pd_y0 + 0.8, pd_y1 - 0.8)   # opening under the PD's solder side
block_z0 = case_z0 + 6.0                      # 52.0: underside of the guide block (1.7 above the buttons)
guide_clear = 0.25 + 0.1                      # per side; a vertical hole prints ~0.1 per side tighter
io_holes = [cs(-9.54, 17.98), cs(9.54, 17.98)]  # IO0 / RST (toothpick)

# ---------------- PUSH PINS (printed lying down) ----------------
pin_t = 5.0                                   # thickness = print height (along housing X)
stem_y = (ky - 1.5, ky + 1.5)
collar_y = (stem_y[0], ky + 4.95)             # collar only upward (bottom wall of the housing below)
collar_l = 1.6
rest = 0.5                                    # at rest (collar against the cap) between tip and button
free_travel = 1.4                             # then the collar hits the carrier (end stop)
chamber_z1 = plate_z1 + collar_l + free_travel    # 59.5 ceiling of the collar chamber in the cap
tip_z = button_top + rest                     # 50.8
sym_w, sym_h, round_d = 5.4, 5.0, 4.8
chamber_clear = 0.5
bevel = 0.5                                   # long edges of stem and collar 0.5 x 45 deg
tip_round = 0.4                               # arrow tips rounded
PIN_EXTRA = 0.4                               # chosen set "long04": 0.4 mm longer at the button end

# ---------------- CAP ----------------
cap_z1 = back_in - 0.2                        # 64.8: 0.2 short of the back plate (keeps the cap in place)
cap_y0 = 2.4
peg_d, peg_rib, peg_l = 5.4, 0.3, 3.0         # peg in the screw hole 5.9 (prints ~5.7) + 3 crush ribs to 6.0
lip_z0 = pd_z1 + 0.1                          # lips 0.1 above the PD board
wire_z1 = 61.0                                # passage for the wires at the clamp end


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

def cyl_z(cx, cy, d, z0, z1):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((cx, cy, z0))

def prism_z(points_xy, z0, z1):
    return cq.Workplane("XY").polyline(points_xy).close().extrude(z1 - z0).translate((0, 0, z0))

def poly_z(poly, z0, z1):
    poly = poly.buffer(0).simplify(0.01)
    gs = poly.geoms if hasattr(poly, "geoms") else [poly]
    w = None
    for g in gs:
        s = prism_z(list(g.exterior.coords)[:-1], z0, z1)
        for r in g.interiors:
            s = s.cut(prism_z(list(r.coords)[:-1], z0 - 1, z1 + 1))
        w = s if w is None else w.union(s)
    return w

def octagon(x0, x1, y0, y1, c):
    """Rectangle with the four corners chamfered c at 45 deg."""
    return sg.Polygon([(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1),
                       (x0, y1 - c), (x0, y0 + c)])

def lead_in(poly, z_bed, layer=0.2, steps=2):
    """Stepped lead-in on the bed side of a hole (bed at z_bed, hole runs to lower Z): 0.2 wider per layer."""
    w = None
    for k in range(steps):
        d = (steps - k) * layer
        z0 = z_bed - (k + 1) * layer
        z1 = z_bed + 1.0 if k == 0 else z_bed - k * layer + 0.01
        st = poly_z(poly.buffer(d, join_style=2), z0, z1)
        w = st if w is None else w.union(st)
    return w

def groove_cutter(dy=0.0):
    h = 12.0
    w = (cq.Workplane("XZ", origin=(0, groove_y - dy, 0)).center(arc_cx, arc_cz).circle(groove_r)
         .workplane(offset=-h).center(h, 0).circle(groove_r).loft(ruled=True))
    return w.intersect(box(-5, housing_x + 5, groove_y - dy - 0.01, housing_y + 5, -5, housing_z + 5))

GROOVE = groove_cutter()
GROOVE_INNER = groove_cutter(groove_thick)

# button symbols (section in XY); the back-plate windows match these
def sym_poly(i, d=0.0):
    if i == 0:
        p = sg.Polygon([(lx - sym_h / 2, ky), (lx + sym_h / 2, ky - sym_w / 2), (lx + sym_h / 2, ky + sym_w / 2)])
    elif i == 2:
        p = sg.Polygon([(rx + sym_h / 2, ky), (rx - sym_h / 2, ky + sym_w / 2), (rx - sym_h / 2, ky - sym_w / 2)])
    else:
        # round, with a small 45 deg flat on the bed side (X mx-2.5) so it prints lying down
        r = round_d / 2
        c = sg.Point(mx, ky).buffer(r, 64)
        a = r / math.sqrt(2)
        dx = (2.5 - a)
        tr = sg.Polygon([(mx - a, ky - a), (mx - 2.5, ky - a + dx), (mx - 2.5, ky + a - dx), (mx - a, ky + a), (mx, ky)])
        p = c.union(tr)
    return p.buffer(d, join_style=2) if d else p

def symbol(i, z0, z1, d=0.0, rnd=0.0):
    p = sym_poly(i, d)
    if rnd:
        p = p.buffer(-rnd, join_style=1).buffer(rnd, join_style=1)
    return poly_z(p, z0, z1)

def window(i, Z0, Z1, d=0.0):
    """Back-plate windows (triangle 5 x 5.4, round 5.0)."""
    if i == 1:
        return cyl_z(mx, ky, 5.0 + 2 * d, Z0, Z1)
    return symbol(i, Z0, Z1, d)


# =====================================================================
# CARRIER   print orientation: top (Z 56.5) on the bed; legs grow upward
# =====================================================================
def case_outline(z=8.6):
    import trimesh
    m = trimesh.load(SHELL_STL)
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    pl, T = s.to_2D()
    big = max(pl.polygons_full, key=lambda q: q.area)
    xy = np.array(big.exterior.simplify(0.05).coords)
    P_ = (np.c_[xy, np.zeros(len(xy)), np.ones(len(xy))] @ T.T)[:, :2]
    return sg.Polygon([cs(px, py) for px, py in P_[:-1]]).buffer(0)

def leg_square(hx, hy):
    sx = 1 if hx > shaft_x else -1
    sy = 1 if hy > shaft_y else -1
    xs = sorted((hx - sx * leg_in, hx + sx * leg_out))
    ys = sorted((hy - sy * leg_in, hy + sy * leg_out))
    return sg.box(xs[0], ys[0], xs[1], ys[1])

outline = case_outline()
for h in corners:
    outline = outline.union(leg_square(*h))
outline = outline.union(sg.box(11.0, 12.0, 13.2, 44.0))               # strip on the worm side joins both halves
outline = outline.intersection(sg.box(11.0, cap_y0, din_in - 0.4, 46.5)).buffer(0)

plate = outline.difference(sg.box(*[pd_window[0], pd_window[2], pd_window[1], pd_window[3]]))
CR = poly_z(plate, plate_z0, plate_z1)
# legs (corner screws): square from the plate down to the board
for i, (hx, hy) in enumerate(corners):
    CR = CR.union(poly_z(leg_square(hx, hy), board_z, plate_z0 + 0.05))
    CR = CR.cut(cyl_z(hx, hy, head_hole, head_z, plate_z1 + 1))             # head hole, open at the top
    along_x = (hx > shaft_x) == (hy > shaft_y)                               # slots alternate: carrier is located
    sl = box(hx - head_hole, hx + head_hole, hy - slot_w / 2, hy + slot_w / 2, board_z - 1, head_z + 0.01) if along_x else \
        box(hx - slot_w / 2, hx + slot_w / 2, hy - head_hole, hy + head_hole, board_z - 1, head_z + 0.01)
    CR = CR.cut(sl.intersect(cyl_z(hx, hy, head_hole, board_z - 1, head_z + 0.01)))
# guide block under the plate for the three pins
CR = CR.union(box(21.0, 44.0, cap_y0 + 0.2, 9.2, block_z0, plate_z0 + 0.05))
for i, (x, y) in enumerate(button_xy):
    CR = CR.cut(box(x - pin_t / 2 - guide_clear, x + pin_t / 2 + guide_clear,
                    stem_y[0] - guide_clear, stem_y[1] + guide_clear, block_z0 - 1, plate_z1 + 1))
    CR = CR.cut(lead_in(sg.box(x - pin_t / 2 - guide_clear, stem_y[0] - guide_clear,
                               x + pin_t / 2 + guide_clear, stem_y[1] + guide_clear), plate_z1))
for x, y in io_holes:
    CR = CR.cut(cyl_z(x, y, 3.4, plate_z0 - 1, plate_z1 + 1))
CARRIER = CR


# =====================================================================
# PUSH PINS   print orientation: lying down, flat side (low X) on the bed
# =====================================================================
def push_pin(i, extra=0.0):
    x = button_xy[i][0]
    collar_z0 = chamber_z1 - collar_l
    s = poly_z(octagon(x - pin_t / 2, x + pin_t / 2, stem_y[0], stem_y[1], bevel), tip_z - extra, collar_z0 + 0.05)
    s = s.union(poly_z(octagon(x - pin_t / 2, x + pin_t / 2, collar_y[0], collar_y[1], bevel), collar_z0, chamber_z1))
    s = s.union(symbol(i, chamber_z1 - 0.05, housing_z + protrusion, rnd=tip_round))
    return s

PINS = [push_pin(i, PIN_EXTRA) for i in range(3)]
PINS_NOMINAL = [push_pin(i) for i in range(3)]   # used for the light-rim clearance, as in the original design


# =====================================================================
# CAP   print orientation: top (Z 64.8) on the bed; everything opens upward
# =====================================================================
CP = box(12.6, 51.0, cap_y0, 12.6, plate_z1, cap_z1)                             # bar over the pins
CP = CP.union(box(11.0, pd_x0 - 0.2, 12.5, 33.2, plate_z1, cap_z1))               # arm at the clamp end
CP = CP.union(box(11.0, 20.6, 31.4, 43.6, plate_z1, cap_z1))                      # block over the upper-left screw
for ya, yb in ((pd_y0 - 0.4, pd_y0 + 1.4), (pd_y1 - 1.4, pd_y1 + 0.4)):          # lips over the PD corners
    CP = CP.union(box(pd_x0 - 0.3, pd_x0 + 1.5, ya, yb, lip_z0, cap_z1))
CP = CP.union(box(pd_x0 - 0.3, pd_x0 + 1.8, pd_y1 + 0.4, 33.2, plate_z1, cap_z1))  # small wall along the PD (top)
CP = CP.cut(box(10.0, pd_x0 + 0.1, pd_y0 + 2.0, pd_y1 - 2.0, plate_z1 - 1, wire_z1))   # wire passage
for i, (x, y) in enumerate(button_xy):
    CP = CP.cut(box(x - pin_t / 2 - chamber_clear, x + pin_t / 2 + chamber_clear,
                    collar_y[0] - chamber_clear, collar_y[1] + chamber_clear, plate_z1 - 1, chamber_z1))
    CP = CP.cut(symbol(i, plate_z1 - 1, cap_z1 + 1, guide_clear))     # also through the chamber: pin goes all the way in
    CP = CP.cut(lead_in(sym_poly(i, guide_clear), cap_z1))
    CP = CP.cut(box(x - pin_t / 2 - chamber_clear, x + pin_t / 2 + chamber_clear, cap_y0 - 1, collar_y[0] - chamber_clear,
                    plate_z1 - 1, cap_z1 + 1))                              # open at the bottom: no thin rims
for (hx, hy) in corners:
    if hx > 40 and hy > 30:
        continue                                                            # upper right: no peg
    peg = cyl_z(hx, hy, peg_d, plate_z1 - peg_l, plate_z1 + 0.05)
    for k in range(3):
        a = math.radians(90 + 120 * k)
        peg = peg.union(cyl_z(hx + (peg_d / 2) * math.cos(a), hy + (peg_d / 2) * math.sin(a), 2 * peg_rib + 0.3,
                              plate_z1 - peg_l + 0.6, plate_z1 + 0.05).intersect(cyl_z(hx, hy, peg_d + 2 * peg_rib, 0, 99)))
    CP = CP.union(peg)
CP = CP.cut(cyl_z(*io_holes[1], 3.4, plate_z1 - 1, cap_z1 + 1))
CAP = CP


# ---- wedges at the bottom of the DIN wall (shell) in slots in the floor (chassis) ----
wedge_x0 = din_in - 1.4           # 54.6 inside of the wedge (stop inward); motor ends at X 53.65
wedge_depth = 1.0                 # below the floor (Y 2): wedge down to Y 1.0
wedge_top = 5.0                   # rib above the floor up to Y 5
wedge_clear = 0.15                # clearance all round in the slot
wedge_z = ((front_wall + 0.3, 15.0), (28.0, 40.0), (50.0, 62.8))   # front, middle, back
wedge_low = sg.Polygon([(din_in, wall), (wedge_x0, wall - wedge_depth), (wedge_x0, wall)])

def poly_xy_along_z(p, z0, z1):
    """Profile in the XY plane, extruded along Z."""
    return prism_z(list(p.exterior.coords)[:-1], z0, z1)

def wedge(z0, z1):
    p = sg.Polygon([(din_in + 0.3, wall + 0.3), (din_in, wall), (wedge_x0, wall - wedge_depth), (wedge_x0, wedge_top),
                    (din_in + 0.3, wedge_top)])
    return poly_xy_along_z(p, z0, z1)

def wedge_slot(z0, z1):
    p = wedge_low.buffer(wedge_clear, join_style=2, mitre_limit=1.5).union(
        sg.box(wedge_x0 - wedge_clear, wall - 0.01, din_in + wedge_clear + 0.3, wall + 0.5))
    p = p.intersection(sg.box(0, -1, housing_x, wall + 0.5))
    return poly_xy_along_z(p, max(z0 - 0.3, front_wall), z1 + 0.3)


# =====================================================================
# CHASSIS, SHELL, BACK PLATE
# =====================================================================
C = box(0, housing_x, 0, housing_y, 0, front_wall)
C = C.cut(cyl_z(shaft_x, shaft_y, collar_hole, -1, front_wall + 1))
for dx, dy in itertools.product((-hole_pitch / 2, hole_pitch / 2), repeat=2):
    C = C.cut(cyl_z(shaft_x + dx, shaft_y + dy, m3_lying, -1, front_wall + 1))
C = C.union(box(0, housing_x, 0, wall, front_wall - 0.1, back_in))
C = C.union(box(0, wall_worm, 0, groove_y - groove_thick, front_wall - 0.1, back_in))
zm = dt_z0 + dt_width / 2
C = C.union(cq.Workplane("YZ").polyline([(0.3, zm - dt_neck / 2), (0.3, zm + dt_neck / 2),
                                         (-dt_height, dt_z0 + dt_width), (-dt_height, dt_z0)])
            .close().extrude(dt_x1 - dt_x0).translate((dt_x0, 0, 0)))
for x, y in (front_bolt_din, front_bolt_mid):
    C = C.cut(cyl_z(x, y, m3_lying, -1, front_wall + 0.5))
C = C.union(box(wall_worm - 0.1, 9.0, wall - 0.1, 11.0, 57.0, back_in))
C = C.union(box(wall_worm - 0.1, 9.0, 40.5, 47.5, 57.0, back_in))
for name in ("chassis_low", "chassis_high"):
    x, y = back_bolts[name]
    C = C.cut(cyl_z(x, y, insert_hole, back_in - insert_depth, back_in + 0.5))
C = C.cut(GROOVE)
for z0, z1 in wedge_z:
    C = C.cut(wedge_slot(z0, z1))

S = box(0, housing_x, top_in, housing_y, front_wall, back_in)
S = S.union(box(din_in, housing_x, wall, top_in + 0.1, front_wall, back_in))
S = S.cut(GROOVE).union(GROOVE_INNER.cut(GROOVE).intersect(box(0, housing_x, 0, housing_y, front_wall, back_in)))
S = S.union(box(44.5, din_in + 0.1, shaft_y + motor_w / 2 + 0.5, top_in + 0.1, front_wall, front_wall + 7.0))
S = S.union(prism_z([(25.5, 47.5), (32.0, 47.5), (40.6, top_in + 0.1), (25.5, top_in + 0.1)],
                    front_wall, front_wall + 7.0))
for x, y in (front_bolt_din, front_bolt_mid):
    S = S.cut(cyl_z(x, y, insert_hole, front_wall - 0.1, front_wall + insert_depth))
S = S.union(box(48.0, din_in + 0.1, 46.0, top_in + 0.1, 57.0, back_in))
x, y = back_bolts["shell_din"]
S = S.cut(cyl_z(x, y, insert_hole, back_in - insert_depth, back_in + 0.5))
S = S.cut(cq.Workplane("YZ").workplane(offset=din_in - 0.1).center(usb_y, usb_z)
          .slot2D(usb_w + 0.6, usb_h + 0.6).extrude(wall + 0.2))
S = S.cut(box(din_in - 0.1, pd_x1 + 0.2, pd_y0 - 0.3, pd_y1 + 0.3, pd_z0 - 0.2, pd_z1 + 0.2))
for z0, z1 in wedge_z:
    S = S.union(wedge(z0, z1))

BP = box(0, housing_x, 0, housing_y, back_in, housing_z).cut(GROOVE)
for x, y in back_bolts.values():
    BP = BP.cut(cyl_z(x, y, m3_clear, back_in - 1, housing_z + 1))
for i in range(3):
    BP = BP.cut(window(i, back_in - 1, housing_z + 1, window_clear))

# ---- light-seal rim on the inside of the back plate ----
rim_w, rim_h, rim_clear = 1.2, 2.0, 0.25
rim_z0 = back_in - rim_h                      # 63.0 (PD components up to 62.5 [ASSUMPTION])

def section(w, z):
    import trimesh, tempfile
    from shapely.ops import unary_union
    f = tempfile.NamedTemporaryFile(suffix=".stl", delete=False).name
    cq.exporters.export(w, f, tolerance=0.01, angularTolerance=0.1)
    m = trimesh.load(f)
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None:
        return sg.Polygon()
    pl, T = sec.to_2D()
    out = []
    for p in pl.polygons_full:
        xy = np.array(p.exterior.coords)
        P_ = (np.c_[xy, np.zeros(len(xy)), np.ones(len(xy))] @ T.T)[:, :2]
        holes = []
        for r in p.interiors:
            rr = np.array(r.coords)
            holes.append((np.c_[rr, np.zeros(len(rr)), np.ones(len(rr))] @ T.T)[:, :2])
        out.append(sg.Polygon(P_, holes))
    return unary_union(out).buffer(0)

def light_rim():
    from shapely.ops import unary_union
    zs = (rim_z0 + 0.1, back_in - 1.0, back_in - 0.1)
    walls = unary_union([section(C.union(S), z) for z in zs])
    inside = sg.box(0, 0, housing_x, housing_y).difference(walls).buffer(0)
    inside = max(getattr(inside, "geoms", [inside]), key=lambda g: g.area)
    obstacles = [CAP] + PINS_NOMINAL
    keep_out = unary_union([section(w, z) for w in obstacles for z in zs]).buffer(rim_clear, join_style=2)
    band = inside.buffer(-rim_clear, join_style=2).difference(inside.buffer(-(rim_clear + rim_w), join_style=2))
    r = band.difference(keep_out)
    r = r.difference(sg.box(11.0, 0, 51.5, 4.5))       # bottom wall under the cap: the cap covers the seam there
    r = r.buffer(-0.45, join_style=2).buffer(0.45, join_style=2)       # no pieces narrower than 0.9
    pieces = [g for g in getattr(r, "geoms", [r]) if g.area > 4.0]
    return unary_union(pieces)

RIM = light_rim()
BP = BP.union(poly_z(RIM, rim_z0, back_in + 0.05))

# ---- chamfer the outer edges 1.0 x 45 deg ----
edge_chamfer = 1.0
_block = box(0, housing_x, 0, housing_y, 0, housing_z)
_not = cq.selectors.InverseSelector(cq.selectors.BoxSelector((-0.5, -0.5, 1.0), (0.5, 0.5, housing_z - 1.0)))
EDGE_STRIP = _block.cut(_block.edges(_not).chamfer(edge_chamfer))
C = C.cut(EDGE_STRIP)
S = S.cut(EDGE_STRIP)
BP = BP.cut(EDGE_STRIP)

CHASSIS, SHELL, BACK_PLATE = C, S, BP


# =====================================================================
# DUMMIES (for collision checks and the assembly STEP)
# =====================================================================
def to_housing(w):
    return w.rotate((0, 0, 0), (0, 0, 1), 90).translate((shaft_x, shaft_y, case_z0))

mx0, mx1 = shaft_x - motor_w / 2, shaft_x + motor_w / 2
my0, my1 = shaft_y - motor_w / 2, shaft_y + motor_w / 2
DUMMIES = {
    "motor": box(mx0, mx1, my0, my1, front_wall, motor_back - motor_tol),
    "motor_cable_top": box(shaft_x - 6, shaft_x + 6, my1, my1 + 5.0, motor_back - 8, motor_back - 1),
    "case_spacers": box(shaft_x - 19, shaft_x + 19, shaft_y - 19, shaft_y + 19, motor_back, case_z0 - 0.5),
    "board": to_housing(box(-21.05, 21.05, -19.55, 19.55, -0.1, 1.5)),
    "tm_p1_plug": box(shaft_x - p1_ys[1], shaft_x - p1_ys[0], shaft_y + tm_edge, shaft_y + tm_edge + p1_over, *plug_z),
    "tm_motor_plug": box(shaft_x - tm_edge - jst_over, shaft_x - tm_edge, shaft_y + jst_ys[0], shaft_y + jst_ys[1], *plug_z),
    "pd_board": box(pd_x0, pd_x1, pd_y0, pd_y1, pd_z0, pd_z1),
    "pd_components": box(pd_x0 + 2.0, pd_x1 - 1, pd_y0 + 1, pd_y1 - 1, pd_z1, pd_z1 + pd_comp),
    "pd_solder": box(pd_x0 + 1, pd_x1 - 1, pd_y0 + 1, pd_y1 - 1, pd_z0 - pd_solder, pd_z0),
    "pd_usb": box(pd_x1 - usb_l + usb_out, pd_x1 + usb_out, usb_y - usb_w / 2, usb_y + usb_w / 2, pd_z1, pd_z1 + usb_h),
    "capacitor": to_housing(cyl_z(4.5, 4.9, 5.0, 1.5, 7.0)),
}
for i, y in enumerate(button_y_case):
    DUMMIES[f"button{i+1}"] = to_housing(box(button_x_case - 1.5, button_x_case + 1.5, y - 1.75, y + 1.75, 1.5, 4.3))
for (hx, hy) in corners:
    DUMMIES[f"screw_head_{hx:.0f}_{hy:.0f}"] = cyl_z(hx, hy, 5.5, head_z, head_z + 3.0)
    DUMMIES[f"screw_{hx:.0f}_{hy:.0f}"] = cyl_z(hx, hy, 3.0, board_z - 5, head_z)
DUMMIES["board_components"] = to_housing(box(-11.5, 11.5, -11.5, 11.5, 1.5, 7.5))   # [ASSUMPTION]


def overlap(a, b):
    try:
        return sum(s.Volume() for s in a.intersect(b).solids().vals())
    except Exception:
        return -1.0


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "./"
    print("light rim: pieces", len(getattr(RIM, "geoms", [RIM])), "length along the walls ~", round(RIM.area / rim_w, 1), "mm")
    for n, w in (("chassis", CHASSIS), ("shell", SHELL), ("back_plate", BACK_PLATE), ("carrier", CARRIER), ("cap", CAP)):
        print(f"  {n:10s} valid {w.val().isValid()}  solids {len(w.solids().vals())}  volume {w.val().Volume():9.1f} mm3")
    pd_set = DUMMIES["pd_board"].union(DUMMIES["pd_components"]).union(DUMMIES["pd_solder"]).union(DUMMIES["pd_usb"])
    others = {"chassis": CHASSIS, "shell": SHELL, "cap": CAP, "carrier": CARRIER, "pd": pd_set, "motor": DUMMIES["motor"]}
    for i, p in enumerate(PINS):
        others[f"pin{i+1}"] = p
    for n, w in others.items():
        print(f"  back_plate x {n:8s} overlap {overlap(BACK_PLATE, w):7.3f}")
    print(f"  chassis x shell overlap {overlap(CHASSIS, SHELL):.3f};  shell x motor {overlap(SHELL, DUMMIES['motor']):.3f}")
    asm = cq.Assembly()
    for n, w, k in (("back_plate", BACK_PLATE, "seagreen"), ("chassis", CHASSIS, "steelblue"), ("shell", SHELL, "goldenrod"),
                    ("cap", CAP, "orange"), ("carrier", CARRIER, "purple")):
        asm.add(w, name=n, color=cq.Color(k))
    for i, p in enumerate(PINS):
        asm.add(p, name=f"pin_{i+1}", color=cq.Color("red"))
    for n, w in DUMMIES.items():
        asm.add(w, name="DUMMY_" + n, color=cq.Color(0.6, 0.6, 0.6, 0.5))
    asm.export(os.path.join(out, "housing_assembly_with_dummies.step"))
