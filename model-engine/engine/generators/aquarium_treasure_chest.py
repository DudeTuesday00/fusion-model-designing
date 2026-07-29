"""Treasure chest for aquarium decor - the first Aquarium piece.

Two printable bodies:
- The chest: a hollow open-top box with raised vertical straps (the "metal
  bands") on the front and back faces, and an optional swim-through hole
  punched through both walls for fish (which doubles as an airline pass).
- The lid: a curved half-barrel shell with closed end caps, printed flat
  side down, placed beside the chest. In the tank, glue it fully closed or
  propped ajar with the classic escaping-treasure look.

Print in PLA or PETG - both are aquarium-safe once rinsed.
"""

import adsk.core
import adsk.fusion

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..registry import register


def _draw_rect(sketch, x0, y0, x1, y1, z=0.0):
    """Axis-aligned rectangle through model-space corners at height z."""
    pts = [
        sketch.modelToSketchSpace(adsk.core.Point3D.create(x0, y0, z)),
        sketch.modelToSketchSpace(adsk.core.Point3D.create(x1, y0, z)),
        sketch.modelToSketchSpace(adsk.core.Point3D.create(x1, y1, z)),
        sketch.modelToSketchSpace(adsk.core.Point3D.create(x0, y1, z)),
    ]
    lines = sketch.sketchCurves.sketchLines
    for i in range(4):
        lines.addByTwoPoints(pts[i], pts[(i + 1) % 4])


@register
class TreasureChest(Generator):
    id = "aquarium_treasure_chest"
    display_name = "Treasure Chest"
    category = "Aquarium Decor"
    parameters = [
        ParamSpec(name="length", label="Length", type="float", default=80.0,
                  min=30.0, max=250.0, unit="mm"),
        ParamSpec(name="width", label="Width", type="float", default=55.0,
                  min=25.0, max=200.0, unit="mm"),
        ParamSpec(name="box_height", label="Box Height", type="float", default=45.0,
                  min=15.0, max=150.0, unit="mm"),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=2.4, min=1.6, max=8.0, unit="mm"),
        ParamSpec(name="base_thickness", label="Base Thickness", type="float",
                  default=3.0, min=1.6, max=10.0, unit="mm"),
        ParamSpec(name="strap_count", label="Straps", type="int", default=2,
                  min=0, max=5),
        ParamSpec(name="strap_width", label="Strap Width", type="float",
                  default=8.0, min=4.0, max=20.0, unit="mm"),
        ParamSpec(name="strap_thickness", label="Strap Thickness", type="float",
                  default=1.2, min=0.6, max=4.0, unit="mm"),
        ParamSpec(name="swim_hole_diameter", label="Swim-Through Hole (0 = none)",
                  type="float", default=0.0, min=0.0, max=60.0, unit="mm"),
        ParamSpec(name="include_lid", label="Include lid (second piece)",
                  type="bool", default=True),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        length = mm(params["length"])
        width = mm(params["width"])
        height = mm(params["box_height"])
        wall = mm(params["wall_thickness"])
        base = mm(params["base_thickness"])

        if wall * 2.5 >= min(length, width):
            raise ValueError("Walls are too thick for this chest size.")
        if base >= height:
            raise ValueError("Base thickness must be less than the box height.")

        # --- chest box: solid block, then carve the open-top cavity --------
        box_sketch = geometry_utils.sketch_on_xy(component)
        _draw_rect(box_sketch, -length / 2, -width / 2, length / 2, width / 2)
        box_body = geometry_utils.extrude_profile(
            component, box_sketch.profiles.item(0), height)

        # Cavity from the base plane out through the top (symmetric cut
        # around a mid-plane so the extrude direction can't surprise us).
        overshoot = mm(5.0)
        cavity_mid = (base + height + overshoot) / 2.0
        cavity_plane = geometry_utils.offset_plane(component, cavity_mid)
        cavity_sketch = component.sketches.add(cavity_plane)
        _draw_rect(cavity_sketch, -length / 2 + wall, -width / 2 + wall,
                    length / 2 - wall, width / 2 - wall, z=cavity_mid)
        geometry_utils.extrude_cut_symmetric(
            component, cavity_sketch.profiles.item(0),
            height + overshoot - base, participants=[box_body])

        # --- straps: raised vertical bands on front and back faces ---------
        strap_count = params["strap_count"]
        if strap_count > 0:
            strap_w = mm(params["strap_width"])
            strap_t = mm(params["strap_thickness"])
            if strap_count * (strap_w + mm(6.0)) > length:
                raise ValueError("Too many straps for this chest length - "
                                 "reduce the count or width.")
            strap_sketch = geometry_utils.sketch_on_xy(component)
            for i in range(strap_count):
                # Even spacing: 2 straps sit at 1/3 and 2/3 of the length.
                x_center = -length / 2 + length * (i + 1) / (strap_count + 1)
                _draw_rect(strap_sketch, x_center - strap_w / 2, width / 2,
                            x_center + strap_w / 2, width / 2 + strap_t)
                _draw_rect(strap_sketch, x_center - strap_w / 2, -width / 2 - strap_t,
                            x_center + strap_w / 2, -width / 2)
            strap_profiles = geometry_utils.collect(
                [strap_sketch.profiles.item(i) for i in range(strap_sketch.profiles.count)]
            )
            geometry_utils.extrude_join(component, strap_profiles, height,
                                         target_body=box_body)

        # --- swim-through hole: straight through both long walls -----------
        hole_d = mm(params["swim_hole_diameter"])
        if hole_d > 0:
            hole_r = hole_d / 2.0
            hole_z = base + (height - base) * 0.5
            if hole_r * 2.0 >= height - base - mm(4.0):
                raise ValueError("Swim-through hole is too big for the box height.")
            hole_sketch = geometry_utils.sketch_on_xz(component)
            center = hole_sketch.modelToSketchSpace(
                adsk.core.Point3D.create(0, 0, hole_z))
            geometry_utils.draw_circle(hole_sketch, hole_r, center)
            geometry_utils.extrude_cut_symmetric(
                component, hole_sketch.profiles.item(0),
                width + mm(10.0), participants=[box_body])

        # --- lid: half-barrel shell with end caps, placed beside the box ---
        if not params["include_lid"]:
            return

        lid_r = width / 2.0
        # Park the lid clear of the box: it extrudes half the box length to
        # each side of its sketch plane, whichever side of Y the plane lands.
        lid_offset = width / 2.0 + length / 2.0 + mm(10.0)
        planes = component.constructionPlanes
        plane_input = planes.createInput()
        plane_input.setByOffset(component.xZConstructionPlane,
                                 adsk.core.ValueInput.createByReal(lid_offset))
        lid_plane = planes.add(plane_input)
        lid_y = lid_plane.geometry.origin.y  # actual side is Fusion's choice

        def semicircle(sketch, radius):
            arcs = sketch.sketchCurves.sketchArcs
            lines = sketch.sketchCurves.sketchLines
            p_start = sketch.modelToSketchSpace(adsk.core.Point3D.create(-radius, lid_y, 0))
            p_mid = sketch.modelToSketchSpace(adsk.core.Point3D.create(0, lid_y, radius))
            p_end = sketch.modelToSketchSpace(adsk.core.Point3D.create(radius, lid_y, 0))
            arcs.addByThreePoints(p_start, p_mid, p_end)
            lines.addByTwoPoints(p_end, p_start)

        lid_solid_sketch = component.sketches.add(lid_plane)
        semicircle(lid_solid_sketch, lid_r)
        lid_body = geometry_utils.extrude_symmetric(
            component, lid_solid_sketch.profiles.item(0), length)

        lid_cavity_sketch = component.sketches.add(lid_plane)
        semicircle(lid_cavity_sketch, lid_r - wall)
        geometry_utils.extrude_cut_symmetric(
            component, lid_cavity_sketch.profiles.item(0),
            length - 2.0 * wall, participants=[lid_body])
