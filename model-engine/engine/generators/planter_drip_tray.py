"""Drip tray / saucer sized to sit under a Basic Planter.

Same construction trick as the planter: one closed cross-section revolved
around the vertical axis. Enter the *planter's* bottom diameter and the tray
sizes itself - interior floor = planter bottom + clearance on all sides,
with an outward-flared wall so the pot is easy to drop in and lift out.

The pot rests on L-shaped support ribs that protrude from the wall:
- The horizontal foot of each L runs along the floor from the wall in under
  the pot's outer rim, lifting the pot so drained water can collect and
  evaporate underneath. Because the pot bears on its outer rim, the ribs
  can never line up with the planter's drainage holes (which sit near the
  middle of its base).
- The short vertical leg of each L hugs the wall and centers the pot in the
  tray. It only rises a few mm above the foot so a pot with tapered
  (outward-leaning) walls doesn't wedge against it.
"""

import math

import adsk.core

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..registry import register

# How far above the foot the vertical centering leg engages the pot. Kept
# short on purpose: pots taper outward, so a tall leg would pinch them.
_CENTERING_ENGAGE_MM = 6.0


def _draw_radial_rounded_rect(sketch, angle, r_in, r_out, width, corner_radius):
    """Draws a plan-view rectangle running radially outward at `angle`, with
    the two inner corners (the exposed ones, at r_in) rounded. Values in cm.

    The rectangle is `width` wide tangentially, spanning r_in..r_out from the
    tray center. The outer corners stay square - they're buried in the wall.
    """
    cos_a, sin_a = math.cos(angle), math.sin(angle)

    def pt(r, s):
        # (radial, sideways) local coordinates rotated into model XY.
        return adsk.core.Point3D.create(r * cos_a - s * sin_a, r * sin_a + s * cos_a, 0)

    half_w = width / 2.0
    a = pt(r_in, -half_w)
    b = pt(r_out, -half_w)
    c = pt(r_out, half_w)
    d = pt(r_in, half_w)

    lines = sketch.sketchCurves.sketchLines
    line_ab = lines.addByTwoPoints(a, b)
    lines.addByTwoPoints(b, c)
    line_cd = lines.addByTwoPoints(c, d)
    line_da = lines.addByTwoPoints(d, a)

    arcs = sketch.sketchCurves.sketchArcs
    arcs.addFillet(line_da, a, line_ab, a, corner_radius)
    arcs.addFillet(line_cd, d, line_da, d, corner_radius)


def revolve_round_tray(component, floor_r, rim_r, height, wall, base):
    """Revolves a round tray shell (floor_r interior at the bottom widening
    to rim_r at the top) and returns its body. All values in cm."""
    profile_points = [
        (0.0, 0.0),
        (floor_r + wall, 0.0),   # outer bottom edge
        (rim_r + wall, height),  # outer top edge
        (rim_r, height),         # rim
        (floor_r, base),         # inner wall down to the floor
        (0.0, base),
    ]
    sketch = geometry_utils.sketch_on_xz(component)
    geometry_utils.draw_closed_profile_rz(sketch, profile_points)
    return geometry_utils.revolve_profile(component, sketch.profiles.item(0))


def add_l_ribs(component, tray_body, rib_count, rib_w, foot_in_r, leg_inner_r,
                r_out, foot_top, leg_top):
    """Adds the L-shaped support ribs (horizontal foot + vertical centering
    leg) evenly around the tray, fused into tray_body. All values in cm."""
    corner_r = min(geometry_utils.mm(2.5), rib_w * 0.4)

    foot_sketch = geometry_utils.sketch_on_xy(component)
    for i in range(rib_count):
        angle = 2.0 * math.pi * i / rib_count
        _draw_radial_rounded_rect(foot_sketch, angle, foot_in_r, r_out, rib_w, corner_r)
    foot_profiles = geometry_utils.collect(
        [foot_sketch.profiles.item(i) for i in range(foot_sketch.profiles.count)]
    )
    geometry_utils.extrude_join(component, foot_profiles, foot_top, target_body=tray_body)

    leg_sketch = geometry_utils.sketch_on_xy(component)
    for i in range(rib_count):
        angle = 2.0 * math.pi * i / rib_count
        _draw_radial_rounded_rect(leg_sketch, angle, leg_inner_r, r_out, rib_w, corner_r)
    leg_profiles = geometry_utils.collect(
        [leg_sketch.profiles.item(i) for i in range(leg_sketch.profiles.count)]
    )
    geometry_utils.extrude_join(component, leg_profiles, leg_top, target_body=tray_body)


FOOT_PARAMS = [
    ParamSpec(name="base_style", label="Base Style", type="choice", default="Flat",
              choices=["Flat", "Bun Feet", "Block Feet", "Hex Feet", "Foot Ring"],
              group="Feet"),
    ParamSpec(name="base_attachment", label="Feet Attachment", type="choice",
              default="Separate (glue-on)",
              choices=["Separate (glue-on)", "Integrated (needs supports)"],
              group="Feet"),
    ParamSpec(name="foot_height", label="Foot Height", type="float",
              default=5.0, min=2.0, max=20.0, unit="mm", group="Feet"),
    ParamSpec(name="foot_size", label="Foot Size", type="float",
              default=12.0, min=6.0, max=30.0, unit="mm", group="Feet"),
    ParamSpec(name="foot_count", label="Feet (Round trays)", type="int",
              default=4, min=3, max=8, group="Feet"),
]

RIM_PARAMS = [
    ParamSpec(name="rim_finish", label="Rim Finish (Round only)", type="choice",
              default="Plain", choices=["Plain", "Scalloped"], group="Rim"),
]


def scallop_rim(component, tray_body, rim_mid_r, height):
    """Cuts a ring of round bites out of the rim, leaving petal points -
    one vertical cylinder cut, circular-patterned."""
    mm = geometry_utils.mm
    circumference = 2.0 * math.pi * rim_mid_r
    count = max(8, int(round(circumference / mm(16.0))))
    bite_r = circumference / count * 0.31
    bite_depth = min(bite_r * 0.9, mm(4.5))

    plane = geometry_utils.offset_plane(component, height)
    sketch = component.sketches.add(plane)
    center = sketch.modelToSketchSpace(adsk.core.Point3D.create(rim_mid_r, 0, height))
    geometry_utils.draw_circle(sketch, bite_r, center)
    feature = geometry_utils.extrude_cut_symmetric(
        component, sketch.profiles.item(0), 2.0 * bite_depth,
        participants=[tray_body])
    geometry_utils.circular_pattern(component, feature, count)


def _draw_foot_outline(sketch, style, cx, cy, foot_size, angle=0.0):
    mm = geometry_utils.mm
    if style == "Bun Feet":
        geometry_utils.draw_circle(sketch, foot_size / 2.0,
                                    adsk.core.Point3D.create(cx, cy, 0))
    elif style == "Hex Feet":
        geometry_utils.draw_polygon(sketch, 6, foot_size / 2.0,
                                     corner_radius_cm=0.0, center_x=cx, center_y=cy)
    else:  # Block Feet - square with rounded corners
        geometry_utils.draw_polygon(sketch, 4, foot_size / 2.0,
                                     corner_radius_cm=min(mm(2.5), foot_size * 0.25),
                                     center_x=cx, center_y=cy)


def add_feet(component, tray_body, params, floor_r, wall, base, foot_angles):
    """Adds the selected foot style under the tray.

    Integrated: feet are sketched at z=0 and extruded symmetrically - the
    upper half buries into the tray base, so the tray stands on feet down to
    z = -foot_height. Prints with supports under the raised base.

    Separate (glue-on): the tray keeps its flat printable bottom and only
    gets shallow alignment sockets; the feet are built as separate bodies
    beside the tray with matching pegs. Print everything flat, then glue
    the pegs into the sockets.
    """
    mm = geometry_utils.mm
    style = params["base_style"]
    if style == "Flat":
        return
    separate = params["base_attachment"].startswith("Separate")
    foot_h = mm(params["foot_height"])
    foot_size = mm(params["foot_size"])
    outer_r = floor_r + wall

    ring_r = outer_r * 0.78  # ceramic-style ring sits at ~78% of the base
    ring_w = max(foot_size * 0.35, mm(3.0))

    if style != "Foot Ring":
        radius_c = outer_r - foot_size / 2.0 - mm(1.0)
        if radius_c < foot_size:
            raise ValueError("Feet are too big for this tray - reduce the foot size.")
        spacing = 2.0 * radius_c * math.sin(math.pi / max(len(foot_angles), 1))
        if len(foot_angles) > 1 and spacing < foot_size + mm(2.0):
            raise ValueError("Too many feet to fit - reduce the count or size.")
        positions = [(radius_c * math.cos(a), radius_c * math.sin(a), a)
                     for a in foot_angles]

    if not separate:
        # --- integrated: fuse feet straddling z=0 into the base ------------
        sketch = geometry_utils.sketch_on_xy(component)
        if style == "Foot Ring":
            geometry_utils.draw_circle(sketch, ring_r + ring_w / 2.0)
            geometry_utils.draw_circle(sketch, ring_r - ring_w / 2.0)
            profiles = [sketch.profiles.item(i) for i in range(sketch.profiles.count)
                        if sketch.profiles.item(i).profileLoops.count == 2]
        else:
            for (cx, cy, angle) in positions:
                if style == "Block Feet":
                    _draw_radial_rounded_rect(sketch, angle,
                                                math.hypot(cx, cy) - foot_size / 2.0,
                                                math.hypot(cx, cy) + foot_size / 2.0,
                                                foot_size, min(mm(2.5), foot_size * 0.3))
                else:
                    _draw_foot_outline(sketch, style, cx, cy, foot_size)
            profiles = [sketch.profiles.item(i) for i in range(sketch.profiles.count)]
        foot_bodies = geometry_utils.extrude_symmetric_all(
            component, geometry_utils.collect(profiles), 2.0 * foot_h)
        geometry_utils.combine_join(component, tray_body, foot_bodies)
        return

    # --- separate glue-on feet ---------------------------------------------
    peg_d = min(mm(8.0), foot_size * 0.5)
    socket_depth = min(mm(1.6), base * 0.5)
    peg_h = socket_depth - mm(0.2)
    extrudes = component.features.extrudeFeatures

    # 1) Alignment sockets cut up into the tray's underside.
    socket_sketch = geometry_utils.sketch_on_xy(component)
    if style == "Foot Ring":
        geometry_utils.draw_circle(socket_sketch, ring_r + (ring_w + mm(0.4)) / 2.0)
        geometry_utils.draw_circle(socket_sketch, ring_r - (ring_w + mm(0.4)) / 2.0)
        socket_profiles = [socket_sketch.profiles.item(i)
                           for i in range(socket_sketch.profiles.count)
                           if socket_sketch.profiles.item(i).profileLoops.count == 2]
    else:
        for (cx, cy, _a) in positions:
            geometry_utils.draw_circle(socket_sketch, (peg_d + mm(0.4)) / 2.0,
                                        adsk.core.Point3D.create(cx, cy, 0))
        socket_profiles = [socket_sketch.profiles.item(i)
                           for i in range(socket_sketch.profiles.count)]
    geometry_utils.extrude_cut(component, geometry_utils.collect(socket_profiles),
                                socket_depth, participants=[tray_body])

    # 2) The feet themselves, parked in a row beside the tray, peg up.
    peg_plane = geometry_utils.offset_plane(component, foot_h)

    def solid_up(profiles_list, height_cm):
        ext_input = extrudes.createInput(
            geometry_utils.collect(profiles_list),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ext_input.setOneSideExtent(
            adsk.fusion.DistanceExtentDefinition.create(
                adsk.core.ValueInput.createByReal(height_cm)),
            adsk.fusion.ExtentDirections.PositiveExtentDirection)
        feature = extrudes.add(ext_input)
        return [feature.bodies.item(i) for i in range(feature.bodies.count)]

    if style == "Foot Ring":
        ring_cy = -(outer_r + ring_r + ring_w + mm(10.0))
        ring_sketch = geometry_utils.sketch_on_xy(component)
        geometry_utils.draw_circle(ring_sketch, ring_r + ring_w / 2.0,
                                    adsk.core.Point3D.create(0, ring_cy, 0))
        geometry_utils.draw_circle(ring_sketch, ring_r - ring_w / 2.0,
                                    adsk.core.Point3D.create(0, ring_cy, 0))
        ring_profiles = [ring_sketch.profiles.item(i)
                         for i in range(ring_sketch.profiles.count)
                         if ring_sketch.profiles.item(i).profileLoops.count == 2]
        ring_body = solid_up(ring_profiles, foot_h)[0]
        ridge_sketch = component.sketches.add(peg_plane)
        rc = lambda r: geometry_utils.draw_circle(
            ridge_sketch, r, ridge_sketch.modelToSketchSpace(
                adsk.core.Point3D.create(0, ring_cy, foot_h)))
        rc(ring_r + (ring_w - mm(0.8)) / 2.0)
        rc(ring_r - (ring_w - mm(0.8)) / 2.0)
        ridge_profiles = [ridge_sketch.profiles.item(i)
                          for i in range(ridge_sketch.profiles.count)
                          if ridge_sketch.profiles.item(i).profileLoops.count == 2]
        # Symmetric extrude: half buries into the ring, half sticks up as
        # the ridge - immune to the offset plane's unknown normal direction.
        ridge_bodies = geometry_utils.extrude_symmetric_all(
            component, geometry_utils.collect(ridge_profiles), 2.0 * peg_h)
        geometry_utils.combine_join(component, ring_body, ridge_bodies)
        return

    row_y = -(outer_r + foot_size + mm(8.0))
    spacing_x = foot_size + mm(6.0)
    count = len(positions)
    for i in range(count):
        fx = (i - (count - 1) / 2.0) * spacing_x
        foot_sketch = geometry_utils.sketch_on_xy(component)
        _draw_foot_outline(foot_sketch, style, fx, row_y, foot_size)
        foot_body = solid_up([foot_sketch.profiles.item(0)], foot_h)[0]
        peg_sketch = component.sketches.add(peg_plane)
        center = peg_sketch.modelToSketchSpace(
            adsk.core.Point3D.create(fx, row_y, foot_h))
        geometry_utils.draw_circle(peg_sketch, peg_d / 2.0, center)
        peg_bodies = geometry_utils.extrude_symmetric_all(
            component, geometry_utils.collect([peg_sketch.profiles.item(0)]),
            2.0 * peg_h)
        geometry_utils.combine_join(component, foot_body, peg_bodies)


@register
class DripTray(Generator):
    id = "planter_drip_tray"
    display_name = "Drip Tray / Saucer"
    category = "Planter"
    parameters = [
        ParamSpec(name="shape", label="Shape (match your planter)", type="choice", default="Round",
                  choices=["Round", "Hexagon", "Square"]),
        ParamSpec(name="pot_bottom_diameter", label="Planter Bottom Width / Diameter", type="float",
                  default=90.0, min=20.0, max=500.0, unit="mm"),
        ParamSpec(name="clearance", label="Clearance Around Pot", type="float",
                  default=3.0, min=0.5, max=20.0, unit="mm"),
        ParamSpec(name="tray_height", label="Tray Height", type="float",
                  default=15.0, min=5.0, max=60.0, unit="mm"),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=2.4, min=1.2, max=10.0, unit="mm"),
        ParamSpec(name="base_thickness", label="Base Thickness", type="float",
                  default=3.0, min=1.2, max=15.0, unit="mm"),
        ParamSpec(name="flare_angle", label="Wall Flare Angle (deg)", type="float",
                  default=15.0, min=0.0, max=45.0),
        ParamSpec(name="corner_radius", label="Corner Radius (Square only)", type="float",
                  default=13.0, min=0.0, max=60.0, unit="mm"),
        ParamSpec(name="rib_count", label="Support Ribs (Round only)", type="int",
                  default=4, min=0, max=8),
        ParamSpec(name="rib_width", label="Rib Width", type="float",
                  default=8.0, min=4.0, max=20.0, unit="mm"),
        ParamSpec(name="standoff_height", label="Standoff Height", type="float",
                  default=4.0, min=1.0, max=15.0, unit="mm"),
        ParamSpec(name="foot_length", label="Foot Length Under Pot", type="float",
                  default=12.0, min=5.0, max=40.0, unit="mm"),
        ParamSpec(name="centering_gap", label="Centering Gap", type="float",
                  default=1.0, min=0.2, max=5.0, unit="mm"),
    ] + RIM_PARAMS + FOOT_PARAMS

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        pot_r = mm(params["pot_bottom_diameter"]) / 2.0
        clearance = mm(params["clearance"])
        height = mm(params["tray_height"])
        wall = mm(params["wall_thickness"])
        base = mm(params["base_thickness"])
        flare = math.radians(params["flare_angle"])

        if base >= height:
            raise ValueError("Base thickness must be less than the tray height.")

        shape = params["shape"]

        # The interior must be pot radius + clearance at floor level,
        # widening as it rises because of the flare. All radii across-flats.
        floor_r = pot_r + clearance
        rim_r = floor_r + (height - base) * math.tan(flare)

        if shape == "Round":
            tray_body = revolve_round_tray(component, floor_r, rim_r, height, wall, base)
        else:
            sides = 6 if shape == "Hexagon" else 4
            corner_r = mm(params["corner_radius"]) if shape == "Square" else 0.0
            if corner_r >= floor_r:
                raise ValueError("Corner radius must be less than half the tray's interior width.")
            tray_body = geometry_utils.build_polygon_shell(
                component, sides,
                outer_bottom_r=floor_r + wall, outer_top_r=rim_r + wall,
                inner_floor_r=floor_r, inner_top_r=rim_r,
                height_cm=height, base_cm=base,
                outer_corner_r=corner_r + wall if corner_r > 0 else 0.0,
                inner_corner_r=corner_r,
            )

        # Round trays use the rib count the user asked for. Polygon trays put
        # exactly one rib on the center of each flat side, so every centering
        # leg presses against a flat face of the pot.
        if params["rim_finish"] == "Scalloped":
            if shape != "Round":
                raise ValueError("The scalloped rim is only available on Round trays.")
            scallop_rim(component, tray_body, rim_r + wall / 2.0, height)

        # Feet go on whether or not ribs are wanted. Round trays space them
        # by the foot count; polygon trays put one foot under each corner.
        if shape == "Round":
            foot_angles = [2.0 * math.pi * i / params["foot_count"]
                           for i in range(params["foot_count"])]
        else:
            foot_angles = [math.pi / sides + 2.0 * math.pi * i / sides
                           for i in range(sides)]
        add_feet(component, tray_body, params, floor_r, wall, base, foot_angles)

        if shape == "Round":
            rib_count = params["rib_count"]
        else:
            rib_count = sides if params["rib_count"] > 0 else 0

        if rib_count == 0:
            return
        if rib_count < 3:
            raise ValueError("Use at least 3 support ribs so the pot sits stable (or 0 for none).")

        rib_w = mm(params["rib_width"])
        standoff_h = mm(params["standoff_height"])
        foot_len = mm(params["foot_length"])
        gap = mm(params["centering_gap"])

        foot_top = base + standoff_h
        leg_top = foot_top + mm(_CENTERING_ENGAGE_MM)

        if leg_top > height:
            raise ValueError("Standoff height is too tall - the centering leg would "
                             "stick out above the tray rim. Reduce it or raise the tray height.")
        if foot_len >= pot_r:
            raise ValueError("Foot length must be shorter than the planter's bottom radius.")
        if gap >= clearance:
            raise ValueError("Centering gap must be smaller than the clearance around the pot.")

        # Ribs bear the pot near its rim; make sure neighbors don't collide.
        foot_in_r = pot_r - foot_len
        if 2.0 * foot_in_r * math.sin(math.pi / rib_count) < rib_w + mm(1.0):
            raise ValueError("Too many ribs to fit - reduce the rib count or width.")

        # Bury the rib's outer end in the wall. The wall's inner face slopes
        # outward with the flare, so chase it up to the leg top - but never
        # past the wall's own thickness or we'd poke out of the tray.
        r_out = floor_r + min((leg_top - base) * math.tan(flare), wall)
        add_l_ribs(component, tray_body, rib_count, rib_w, foot_in_r,
                    pot_r + gap, r_out, foot_top, leg_top)
