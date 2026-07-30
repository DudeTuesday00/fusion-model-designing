"""Parametric pen / pencil cup — tapered vessel for the desk ecosystem.

Round or square footprint, optional weighted-looking thick base, optional
matching coaster-style tray. Prints supportless standing upright.
"""

import adsk.core

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..printability import require_base_below_height, require_min_wall
from ..registry import register
from .box_basic import _draw_rounded_rect, _outer_profile


@register
class DeskPenCup(Generator):
    id = "desk_pen_cup"
    display_name = "Pen / Pencil Cup"
    category = "Desk"
    parameters = [
        ParamSpec(name="shape", label="Shape", type="choice", default="Round",
                  choices=["Round", "Square"]),
        ParamSpec(name="top_diameter", label="Top Width / Diameter", type="float",
                  default=80.0, min=30.0, max=200.0, unit="mm"),
        ParamSpec(name="bottom_diameter", label="Bottom Width / Diameter", type="float",
                  default=70.0, min=30.0, max=200.0, unit="mm"),
        ParamSpec(name="height", label="Height", type="float",
                  default=110.0, min=40.0, max=250.0, unit="mm"),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=2.4, min=1.2, max=8.0, unit="mm"),
        ParamSpec(name="base_thickness", label="Base Thickness", type="float",
                  default=4.0, min=1.6, max=15.0, unit="mm"),
        ParamSpec(name="corner_radius", label="Corner Radius (Square)", type="float",
                  default=8.0, min=0.0, max=30.0, unit="mm"),
        ParamSpec(name="include_tray", label="Matching coaster tray", type="bool",
                  default=False),
        ParamSpec(name="tray_clearance", label="Tray Clearance", type="float",
                  default=2.0, min=0.5, max=10.0, unit="mm", group="Tray"),
        ParamSpec(name="tray_height", label="Tray Height", type="float",
                  default=8.0, min=3.0, max=25.0, unit="mm", group="Tray"),
        ParamSpec(name="tray_wall", label="Tray Wall", type="float",
                  default=2.0, min=1.2, max=5.0, unit="mm", group="Tray"),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        shape = params["shape"]
        top_r = mm(params["top_diameter"]) / 2.0
        bottom_r = mm(params["bottom_diameter"]) / 2.0
        height = mm(params["height"])
        wall = mm(params["wall_thickness"])
        base = mm(params["base_thickness"])
        corner_r = mm(params["corner_radius"])

        require_min_wall(params["wall_thickness"])
        require_base_below_height(params["base_thickness"], params["height"])

        if wall >= min(top_r, bottom_r):
            raise ValueError("Wall must be thinner than half the smallest width.")

        if shape == "Round":
            body = self._round_cup(component, top_r, bottom_r, height, wall, base)
        else:
            body = self._square_cup(component, top_r, bottom_r, height, wall, base, corner_r)
        body.name = "PenCup"

        if not params["include_tray"]:
            return

        clr = mm(params["tray_clearance"])
        tray_h = mm(params["tray_height"])
        tray_wall = mm(params["tray_wall"])
        # Park tray along +X
        offset = max(top_r, bottom_r) * 2 + clr + mm(15.0)
        self._tray(component, bottom_r, clr, tray_h, tray_wall, shape, corner_r, offset)

    def _round_cup(self, component, top_r, bottom_r, height, wall, base):
        def outer_at(z):
            return bottom_r + (top_r - bottom_r) * (z / height)

        profile = [
            (0.0, 0.0),
            (bottom_r, 0.0),
            (top_r, height),
            (top_r - wall, height),
            (outer_at(base) - wall, base),
            (0.0, base),
        ]
        sketch = geometry_utils.sketch_on_xz(component)
        geometry_utils.draw_closed_profile_rz(sketch, profile)
        return geometry_utils.revolve_profile(component, sketch.profiles.item(0))

    def _square_cup(self, component, top_r, bottom_r, height, wall, base, corner_r):
        # Across-flats radii as half-widths
        return geometry_utils.build_polygon_shell(
            component, 4,
            outer_bottom_r=bottom_r, outer_top_r=top_r,
            inner_floor_r=bottom_r - wall, inner_top_r=top_r - wall,
            height_cm=height, base_cm=base,
            outer_corner_r=corner_r,
            inner_corner_r=max(corner_r - wall, 0.0),
        )

    def _tray(self, component, bottom_r, clr, tray_h, tray_wall, shape, corner_r, offset_x):
        outer_r = bottom_r + clr + tray_wall
        inner_r = bottom_r + clr
        base_t = min(tray_h * 0.4, geometry_utils.mm(2.0))

        if shape == "Round":
            sketch = geometry_utils.sketch_on_xy(component)
            c = adsk.core.Point3D.create(offset_x, 0, 0)
            geometry_utils.draw_circle(sketch, outer_r, c)
            body = geometry_utils.extrude_profile(component, sketch.profiles.item(0), tray_h)
            cut = geometry_utils.sketch_on_xy(component)
            geometry_utils.draw_circle(cut, inner_r, c)
            geometry_utils.extrude_cut(
                component, cut.profiles.item(0), tray_h - base_t + geometry_utils.mm(1),
                participants=[body])
        else:
            sketch = geometry_utils.sketch_on_xy(component)
            _draw_rounded_rect(
                sketch,
                offset_x - outer_r, -outer_r,
                offset_x + outer_r, outer_r,
                corner_r + clr + tray_wall)
            body = geometry_utils.extrude_profile(component, _outer_profile(sketch), tray_h)
            cut = geometry_utils.sketch_on_xy(component)
            _draw_rounded_rect(
                cut,
                offset_x - inner_r, -inner_r,
                offset_x + inner_r, inner_r,
                max(corner_r + clr, 0.0))
            geometry_utils.extrude_cut(
                component, _outer_profile(cut), tray_h - base_t + geometry_utils.mm(1),
                participants=[body])
        body.name = "CupTray"
