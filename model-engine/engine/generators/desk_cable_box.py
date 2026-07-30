"""Cable management box with matching lid and side pass-throughs.

A low-profile rectangular box for power bricks and excess cable. Side slots
let cords enter/exit. Lid uses the same friction-lip pattern as storage boxes.
"""

import adsk.core

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..printability import require_base_below_height, require_min_wall
from ..registry import register
from .box_basic import _draw_rounded_rect, _outer_profile, _ring_profile


@register
class DeskCableBox(Generator):
    id = "desk_cable_box"
    display_name = "Cable Management Box"
    category = "Desk"
    parameters = [
        ParamSpec(name="length", label="Length (X)", type="float",
                  default=160.0, min=60.0, max=400.0, unit="mm"),
        ParamSpec(name="width", label="Width (Y)", type="float",
                  default=110.0, min=50.0, max=300.0, unit="mm"),
        ParamSpec(name="height", label="Height", type="float",
                  default=45.0, min=20.0, max=120.0, unit="mm"),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=2.4, min=1.2, max=8.0, unit="mm"),
        ParamSpec(name="base_thickness", label="Base Thickness", type="float",
                  default=2.4, min=1.2, max=10.0, unit="mm"),
        ParamSpec(name="corner_radius", label="Corner Radius", type="float",
                  default=8.0, min=0.0, max=40.0, unit="mm"),
        ParamSpec(name="slot_width", label="Cable Slot Width", type="float",
                  default=18.0, min=6.0, max=40.0, unit="mm", group="CableSlots"),
        ParamSpec(name="slot_height", label="Cable Slot Height", type="float",
                  default=12.0, min=4.0, max=40.0, unit="mm", group="CableSlots"),
        ParamSpec(name="slot_count", label="Slots per long side", type="int",
                  default=2, min=0, max=4, group="CableSlots"),
        ParamSpec(name="include_lid", label="Include lid", type="bool",
                  default=True),
        ParamSpec(name="lid_thickness", label="Lid Thickness", type="float",
                  default=2.4, min=1.2, max=8.0, unit="mm", group="Lid"),
        ParamSpec(name="lip_height", label="Lid Lip Height", type="float",
                  default=5.0, min=2.0, max=15.0, unit="mm", group="Lid"),
        ParamSpec(name="fit_clearance", label="Lid Clearance", type="float",
                  default=0.3, min=0.1, max=1.2, unit="mm", group="Lid"),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        length = mm(params["length"])
        width = mm(params["width"])
        height = mm(params["height"])
        wall = mm(params["wall_thickness"])
        base = mm(params["base_thickness"])
        corner_r = mm(params["corner_radius"])

        require_min_wall(params["wall_thickness"])
        require_base_below_height(params["base_thickness"], params["height"])

        if wall * 2.5 >= min(length, width):
            raise ValueError("Walls are too thick for this box size.")

        sketch = geometry_utils.sketch_on_xy(component)
        _draw_rounded_rect(sketch, -length / 2, -width / 2, length / 2, width / 2, corner_r)
        body = geometry_utils.extrude_profile(component, _outer_profile(sketch), height)
        body.name = "CableBox"

        cavity_plane = geometry_utils.offset_plane(component, base)
        cavity = component.sketches.add(cavity_plane)
        _draw_rounded_rect(
            cavity,
            -length / 2 + wall, -width / 2 + wall,
            length / 2 - wall, width / 2 - wall,
            max(corner_r - wall, 0.0), z=base)
        geometry_utils.extrude_cut(
            component, _outer_profile(cavity),
            height - base + mm(2), participants=[body])

        slot_w = mm(params["slot_width"])
        slot_h = mm(params["slot_height"])
        n_slots = int(params["slot_count"])
        if n_slots > 0 and slot_h < height - base:
            slot_z0 = base + mm(1.0)
            plane = geometry_utils.offset_plane(component, slot_z0)
            for side in (-1.0, 1.0):
                y = side * (width / 2.0)
                for i in range(n_slots):
                    frac = (i + 1) / (n_slots + 1)
                    x = -length / 2 + length * frac
                    slot_sk = component.sketches.add(plane)
                    half_w = slot_w / 2.0
                    pts = [
                        slot_sk.modelToSketchSpace(
                            adsk.core.Point3D.create(x - half_w, y - mm(5), slot_z0)),
                        slot_sk.modelToSketchSpace(
                            adsk.core.Point3D.create(x + half_w, y - mm(5), slot_z0)),
                        slot_sk.modelToSketchSpace(
                            adsk.core.Point3D.create(x + half_w, y + mm(5), slot_z0)),
                        slot_sk.modelToSketchSpace(
                            adsk.core.Point3D.create(x - half_w, y + mm(5), slot_z0)),
                    ]
                    lines = slot_sk.sketchCurves.sketchLines
                    for j in range(4):
                        lines.addByTwoPoints(pts[j], pts[(j + 1) % 4])
                    if slot_sk.profiles.count > 0:
                        geometry_utils.extrude_cut(
                            component, slot_sk.profiles.item(0), slot_h,
                            participants=[body])

        if not params["include_lid"]:
            return

        lid_t = mm(params["lid_thickness"])
        lip_h = mm(params["lip_height"])
        fit = mm(params["fit_clearance"])
        offset_y = width + mm(12.0)

        lid_sk = geometry_utils.sketch_on_xy(component)
        _draw_rounded_rect(
            lid_sk,
            -length / 2, offset_y - width / 2,
            length / 2, offset_y + width / 2,
            corner_r)
        lid = geometry_utils.extrude_profile(component, _outer_profile(lid_sk), lid_t)
        lid.name = "CableBoxLid"

        lip_l = length - 2.0 * wall - 2.0 * fit
        lip_w = width - 2.0 * wall - 2.0 * fit
        if lip_l < mm(10) or lip_w < mm(10):
            return

        lip_sk = geometry_utils.sketch_on_xy(component)
        lip_r = max(corner_r - wall - fit, 0.0)
        _draw_rounded_rect(
            lip_sk,
            -lip_l / 2, offset_y - lip_w / 2,
            lip_l / 2, offset_y + lip_w / 2,
            lip_r)
        lip_wall = min(wall, mm(2.0))
        if lip_l > 2 * lip_wall + mm(6) and lip_w > 2 * lip_wall + mm(6):
            _draw_rounded_rect(
                lip_sk,
                -lip_l / 2 + lip_wall, offset_y - lip_w / 2 + lip_wall,
                lip_l / 2 - lip_wall, offset_y + lip_w / 2 - lip_wall,
                max(lip_r - lip_wall, 0.0))
            prof = _ring_profile(lip_sk)
        else:
            prof = _outer_profile(lip_sk)
        geometry_utils.extrude_join(component, prof, lip_h, target_body=lid)
