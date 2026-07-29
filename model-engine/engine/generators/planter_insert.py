"""Self-watering insert for a Round Basic Planter.

A platform that stands on the pot floor on a central wick cup, creating a
water reservoir underneath. Soil sits on the platform and packs down into
the cup; the soil column in the cup wicks water up to the roots.

How it goes together:
- Print the pot with ZERO drainage holes (the reservoir must hold water).
- Drop the insert in, cup down. Slots at the cup's bottom edge let water in.
- Fill soil on top, and water through the fill hole at the platform's edge.

Enter the same pot dimensions you used for the planter and the insert
computes its own platform size from the pot's inner taper.
"""

import math

import adsk.core

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..registry import register


@register
class SelfWateringInsert(Generator):
    id = "planter_insert"
    display_name = "Self-Watering Insert (Round)"
    category = "Planter"
    parameters = [
        ParamSpec(name="pot_bottom_diameter", label="Planter Bottom Diameter", type="float",
                  default=90.0, min=40.0, max=500.0, unit="mm"),
        ParamSpec(name="pot_top_diameter", label="Planter Top Diameter", type="float",
                  default=120.0, min=40.0, max=500.0, unit="mm"),
        ParamSpec(name="pot_height", label="Planter Height", type="float",
                  default=100.0, min=40.0, max=500.0, unit="mm"),
        ParamSpec(name="pot_wall_thickness", label="Planter Wall Thickness", type="float",
                  default=3.0, min=1.2, max=20.0, unit="mm"),
        ParamSpec(name="reservoir_height", label="Reservoir Height", type="float",
                  default=25.0, min=10.0, max=80.0, unit="mm"),
        ParamSpec(name="plate_thickness", label="Platform Thickness", type="float",
                  default=2.4, min=1.6, max=6.0, unit="mm"),
        ParamSpec(name="wick_cup_diameter", label="Wick Cup Diameter", type="float",
                  default=36.0, min=20.0, max=80.0, unit="mm"),
        ParamSpec(name="fit_clearance", label="Fit Clearance", type="float",
                  default=1.0, min=0.3, max=4.0, unit="mm"),
        ParamSpec(name="aeration_hole_count", label="Aeration Holes", type="int",
                  default=8, min=0, max=16),
        ParamSpec(name="fill_hole_diameter", label="Fill Hole Diameter (0 = none)", type="float",
                  default=16.0, min=0.0, max=30.0, unit="mm"),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        pot_bottom_r = mm(params["pot_bottom_diameter"]) / 2.0
        pot_top_r = mm(params["pot_top_diameter"]) / 2.0
        pot_h = mm(params["pot_height"])
        pot_wall = mm(params["pot_wall_thickness"])
        reservoir_h = mm(params["reservoir_height"])
        plate_t = mm(params["plate_thickness"])
        cup_r = mm(params["wick_cup_diameter"]) / 2.0
        cup_wall = mm(2.0)
        clearance = mm(params["fit_clearance"])

        if reservoir_h + plate_t >= pot_h * 0.6:
            raise ValueError("Reservoir is too tall - it should stay under 60% "
                             "of the pot height to leave room for soil.")

        # Pot inner radius at a height, from the same taper the planter uses.
        def pot_inner_r(z):
            return pot_bottom_r + (pot_top_r - pot_bottom_r) * (z / pot_h) - pot_wall

        # The platform's top sits at reservoir_h + plate_t inside the pot;
        # size it to the tightest point it must pass (its own top edge).
        plate_r = pot_inner_r(reservoir_h + plate_t) - clearance
        if cup_r + mm(8.0) >= plate_r:
            raise ValueError("Wick cup is too wide for this pot/reservoir combination.")

        plate_top = reservoir_h + plate_t

        # 1) Solid column the full height - this becomes cup walls + platform.
        col_sketch = geometry_utils.sketch_on_xy(component)
        geometry_utils.draw_circle(col_sketch, cup_r)
        body = geometry_utils.extrude_profile(component, col_sketch.profiles.item(0), plate_top)

        # 2) Fuse the platform disc on top of the reservoir zone.
        plate_plane = geometry_utils.offset_plane(component, reservoir_h)
        plate_sketch = component.sketches.add(plate_plane)
        center = plate_sketch.modelToSketchSpace(adsk.core.Point3D.create(0, 0, reservoir_h))
        geometry_utils.draw_circle(plate_sketch, plate_r, center)
        geometry_utils.extrude_join(component, plate_sketch.profiles.item(0), plate_t,
                                     target_body=body)

        # 3) Hollow the soil channel down the middle - through the platform
        # and the cup, leaving the cup open top and bottom.
        channel_sketch = geometry_utils.sketch_on_xy(component)
        geometry_utils.draw_circle(channel_sketch, cup_r - cup_wall)
        geometry_utils.extrude_cut(component, channel_sketch.profiles.item(0), plate_top,
                                    participants=[body])

        # 4) Water-entry slots at the cup's bottom edge (it stands on the
        # remaining teeth, water flows in underneath).
        slot_h = mm(6.0)
        slot_w = mm(8.0)
        slot_sketch = geometry_utils.sketch_on_xy(component)
        for i in range(4):
            angle = 2.0 * math.pi * i / 4.0
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            half_w = slot_w / 2.0
            r0, r1 = cup_r - cup_wall - mm(1.0), cup_r + mm(1.0)
            pts = [(r0, -half_w), (r1, -half_w), (r1, half_w), (r0, half_w)]
            xy = [adsk.core.Point3D.create(r * cos_a - s * sin_a, r * sin_a + s * cos_a, 0)
                  for (r, s) in pts]
            lines = slot_sketch.sketchCurves.sketchLines
            for j in range(4):
                lines.addByTwoPoints(xy[j], xy[(j + 1) % 4])
        slot_profiles = geometry_utils.collect(
            [slot_sketch.profiles.item(i) for i in range(slot_sketch.profiles.count)]
        )
        geometry_utils.extrude_cut(component, slot_profiles, slot_h, participants=[body])

        # 5) Aeration holes ring in the platform (air for roots, overflow relief).
        hole_count = params["aeration_hole_count"]
        if hole_count > 0:
            ring_r = (cup_r + plate_r) / 2.0
            hole_r = mm(3.0)
            air_sketch = component.sketches.add(plate_plane)
            for i in range(hole_count):
                angle = 2.0 * math.pi * i / hole_count
                c = air_sketch.modelToSketchSpace(adsk.core.Point3D.create(
                    ring_r * math.cos(angle), ring_r * math.sin(angle), reservoir_h))
                geometry_utils.draw_circle(air_sketch, hole_r, c)
            air_profiles = geometry_utils.collect(
                [air_sketch.profiles.item(i) for i in range(air_sketch.profiles.count)]
            )
            geometry_utils.extrude_cut(component, air_profiles, plate_t, participants=[body])

        # 6) Fill hole near the rim - pour water straight into the reservoir.
        fill_d = mm(params["fill_hole_diameter"])
        if fill_d > 0:
            fill_r = fill_d / 2.0
            if fill_r + mm(2.0) >= plate_r - cup_r - mm(8.0):
                raise ValueError("Fill hole is too big to fit between the wick cup "
                                 "and the platform edge.")
            pos_r = plate_r - fill_r - mm(3.0)
            # Offset the fill hole angle so it lands between aeration holes.
            angle = math.pi / max(hole_count, 1) if hole_count > 0 else 0.0
            fill_sketch = component.sketches.add(plate_plane)
            c = fill_sketch.modelToSketchSpace(adsk.core.Point3D.create(
                pos_r * math.cos(angle), pos_r * math.sin(angle), reservoir_h))
            geometry_utils.draw_circle(fill_sketch, fill_r, c)
            geometry_utils.extrude_cut(component, fill_sketch.profiles.item(0), plate_t,
                                        participants=[body])
