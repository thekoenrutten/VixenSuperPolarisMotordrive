"""
Vixen SP RA drive - 44T GT2 worm pulley (design P8d, final).

Replaces the brass worm-shaft gear inside the ORIGINAL slip clutch of the Vixen SP. The pulley's
centre disc is clamped between the hub flange and the clamping bush, exactly like the brass gear,
with the original thumbscrew. Loosen the thumbscrew and the worm turns by hand without the motor.

Coordinates: Z = worm shaft axis. Z 0 = the face against the hub flange (and on the print bed).
The clamping bush comes from +Z.

Measured on the mount:
  brass gear 3.0 thick, bore 12; it sits on a brass bush of 13.0
  clamping bush: thin end 19 dia, 9 long; thick end 25 dia
  recess around the brass gear ~31.5 dia

Belt: GT2, 6 mm wide, 158 mm closed loop; 20T pulley on the motor -> 2.2 : 1.

Lessons that set the numbers (black PLA Matte, Bambu Lab P1S):
  - 40T: belt too slack -> 44T, 158 mm fits at the drawn centre distance (46.4).
  - Centre disc 3.0 did not clamp enough -> 3.3.
  - Bore 13.1 too tight on the 13.0 bush -> 13.3 (13.2 spare on the same plate). Re-test for other filaments.
  - Free-hanging top flange printed with a string -> 45 deg chamfer under the top flange.
  - 0.4 x 45 deg lead-in on the bed side of the bore (elephant's foot).
Print: 0.12 mm layers, 4 walls, 100 % infill, Z 0 on the bed, no supports, never "Auto orient".
Do not ream: the bore is printed to size.

Run:  python pulley.py [output_dir]
"""
import math, os, sys
import cadquery as cq

# ---------------- dimensions ----------------
teeth = 44
pitch = 2.0                         # GT2
pitch_d = teeth * pitch / math.pi   # 28.01
outer_d = pitch_d - 2 * 0.254       # tooth tips (GT2: pitch line 0.254 outside the tip)
groove_depth = 0.764                # GT2 groove depth
groove_r = 0.60                     # groove bottom: half circle (belt tooth r 0.555 + clearance)
groove_mouth = 1.55                 # width of the groove opening at the outside

BORE = 13.3                         # brass bush 13.0
BORE_VARIANTS = [13.3, 13.2]        # 13.2 as a spare
lead = 0.4                          # 45 deg on the bed side of the bore
disc_t = 3.3                        # clamped part (brass gear was 3.0)
rim_inner = 20.2                    # 0.6 radial clearance around the thin end of the clamping bush (19)
flange_d = 29.5                     # 0.25 clear of the mount
flange_t = 1.0                      # bottom flange (on the bed)
top_flange_t = 1.2
top_flange_chamfer = True           # underside of the top flange 45 deg from the tooth tips (printability)
belt_space = 6.5                    # between the flanges, for a 6 mm belt

z_belt0 = flange_t                              # 1.0
z_belt1 = z_belt0 + belt_space                  # 7.5
z_top = z_belt1 + top_flange_t                  # 8.7

# clutch dimensions (for checks)
bush_thin_d, bush_thin_l, bush_thick_d = 19.0, 9.0, 25.0


def ring(d_out, d_in, z0, z1):
    return cq.Workplane("XY").circle(d_out / 2).circle(d_in / 2).extrude(z1 - z0).translate((0, 0, z0))


def make_pulley(teeth=teeth, bore=BORE, disc_t=disc_t, label=True):
    pd = teeth * pitch / math.pi
    od = pd - 2 * 0.254
    body = ring(flange_d, bore, 0, z_belt0)                    # bottom flange
    body = body.union(ring(od, bore, z_belt0, disc_t))        # centre disc (clamped)
    body = body.union(ring(od, rim_inner, disc_t, z_belt1))   # toothed rim above the disc
    body = body.union(ring(flange_d, rim_inner, z_belt1, z_top))   # top flange

    # GT2 grooves between the flanges
    R = od / 2
    rc = R - groove_depth + groove_r
    h = z_belt1 - z_belt0
    groove = (cq.Workplane("XY").center(rc, 0).circle(groove_r).extrude(h)
              .union(cq.Workplane("XY")
                     .polyline([(rc, -groove_r), (R + 0.6, -groove_mouth / 2 - 0.3),
                                (R + 0.6, groove_mouth / 2 + 0.3), (rc, groove_r)]).close()
                     .extrude(h))
              .translate((0, 0, z_belt0)))
    grooves = None
    for i in range(teeth):
        g = groove.rotate((0, 0, 0), (0, 0, 1), i * 360.0 / teeth)
        grooves = g if grooves is None else grooves.union(g)
    body = body.cut(grooves)

    if top_flange_chamfer:
        r0, r1 = od / 2, flange_d / 2 + 0.5
        ch = (cq.Workplane("XZ")
              .polyline([(r0, z_belt1 - 0.01), (r1, z_belt1 - 0.01), (r1, z_belt1 + (r1 - r0))]).close()
              .revolve(360, (0, 0, 0), (0, 1, 0)))
        body = body.cut(ch)

    cone = cq.Solid.makeCone(bore / 2 + lead, bore / 2, lead)
    body = body.cut(cq.Workplane("XY").add(cone))

    if label:   # bore size in relief on the top flange, so spares can be told apart
        txt = (cq.Workplane("XY").workplane(offset=z_top - 0.05)
               .center(0, (rim_inner / 2 + flange_d / 2) / 2)
               .text(f"{teeth}T {bore:.1f}", 1.5, 0.35, kind="bold", halign="center", valign="center"))
        body = body.union(txt)
    return body, pd, od


def make_test_strip(bores=(13.1, 13.2, 13.3, 13.4), ring_out=17.0, height=3.0):
    """Rings with the pulley's bore sizes, same print orientation. Print one in a new filament first."""
    step = ring_out + 2.0
    strip = None
    for i, d in enumerate(bores):
        x = i * step
        r = cq.Workplane("XY").circle(ring_out / 2).circle(d / 2).extrude(height).translate((x, 0, 0))
        r = r.cut(cq.Workplane("XY").add(cq.Solid.makeCone(d / 2 + lead, d / 2, lead)).translate((x, 0, 0)))
        lab = (cq.Workplane("XY").workplane(offset=height - 0.05).center(x, ring_out / 2 + 2.3)
               .text(f"{d:.1f}", 2.4, 0.4, kind="bold", halign="center", valign="center"))
        strip = r if strip is None else strip.union(r)
        strip = strip.union(lab)
    bar = (cq.Workplane("XY").box((len(bores) - 1) * step + 18, 5.0, height, centered=False)
           .translate((-3, ring_out / 2 - 0.5, 0)))
    strip = strip.union(bar)
    for i, d in enumerate(bores):
        strip = strip.cut(cq.Workplane("XY").circle(d / 2).extrude(height).translate((i * step, 0, 0)))
    return strip


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "./"
    body, pd, od = make_pulley()
    print(f"{teeth}T: pitch dia {pd:.2f}, tooth tips {od:.2f}, groove bottom {od - 2 * groove_depth:.2f}")
    print(f"flange {flange_d} is {(flange_d - od) / 2:.2f} above the tooth tips; "
          f"wall under the grooves {(od / 2 - groove_depth) - rim_inner / 2:.2f}")
    print(f"valid {body.val().isValid()}, volume {body.val().Volume():.1f} mm3")
    cq.exporters.export(body, os.path.join(out, "pulley_44T_bore13.3.step"))
