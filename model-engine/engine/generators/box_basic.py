"""Parametric storage box with a matching lid.

Family A starting point: rectangular, square, or round open-top box plus a
separate friction-fit lid. The lid plate covers the rim; a downward lip sits
inside the opening with adjustable clearance so the fit can be tuned for
your printer and filament.

Both pieces print flat (box on its base, lid plate-down). Bodies are placed
side-by-side for easy multi-body export.
"""

import math

import adsk.core

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..printability import require_base_below_height, require_min_wall
from ..registry import register


def _draw_rect(sketch, x0, y0, x1, y1, z=0.0):
    pts = [
        sketch.modelToSketchSpace(adsk.core.Point3D.create(x0, y0, z)),
        sketch.modelToSketchSpace(adsk.core.Point3D.create(x1, y0, z)),
        sketch.modelToSketchSpace(adsk.core.Point3D.create(x1, y1, z)),
        sketch.modelToSketchSpace(adsk.core.Point3D.create(x0, y1, z)),
    ]
    lines = sketch.sketchCurves.sketchLines
    for i in range(4):
        lines.addByTwoPoints(pts[i], pts[(i + 1) % 4])


def _draw_rounded_rect(sketch, x0, y0, x1, y1, corner_r, z=0.0):
    """Axis-aligned rectangle with optional corner arcs (three-point)."""
    if corner_r < 1e-6:
        _draw_rect(sketch, x0, y0, x1, y1, z)
        return

    max_r = min(abs(x1 - x0), abs(y1 - y0)) / 2.0 - 1e-4
    r = min(corner_r, max_r)
    if r < 1e-6:
        _draw_rect(sketch, x0, y0, x1, y1, z)
        return

    def pt(x, y):
        return sketch.modelToSketchSpace(adsk.core.Point3D.create(x, y, z))

    lines = sketch.sketchCurves.sketchLines
    arcs = sketch.sketchCurves.sketchArcs
    k = math.sqrt(2.0) / 2.0

    lines.addByTwoPoints(pt(x0 + r, y0), pt(x1 - r, y0))
    arcs.addByThreePoints(pt(x1 - r, y0), pt(x1 - r + r * k, y0 + r * k), pt(x1, y0 + r))
    lines.addByTwoPoints(pt(x1, y0 + r), pt(x1, y1 - r))
    arcs.addByThreePoints(pt(x1, y1 - r), pt(x1 - r + r * k, y1 - r + r * k), pt(x1 - r, y1))
    lines.addByTwoPoints(pt(x1 - r, y1), pt(x0 + r, y1))
    arcs.addByThreePoints(pt(x0 + r, y1), pt(x0 + r - r * k, y1 - r + r * k), pt(x0, y1 - r))
    lines.addByTwoPoints(pt(x0, y1 - r), pt(x0, y0 + r))
    arcs.addByThreePoints(pt(x0, y0 + r), pt(x0 + r - r * k, y0 + r * k), pt(x0 + r, y0))


@register
class BasicBoxWithLid(Generator):
    id = "box_basic"
    display_name = "Box + Matching Lid"
    category = "Storage"
    parameters = [
        ParamSpec(name="shape", label="Shape", type="choice", default="Rectangle",
                  choices=["Rectangle", "Square", "Round"]),
        ParamSpec(name="length", label="Length (X)", type="float",
                  default=100.0, min=20.0, max=400.0, unit="mm"),
        ParamSpec(name="width", label="Width (Y) — Square/Round use Length", type="float",
                  default=70.0, min=20.0, max=400.0, unit="mm"),
        ParamSpec(name="height", label="Box Height (inside + base)", type="float",
                  default=50.0, min=10.0, max=300.0, unit="mm"),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=2.4, min=1.2, max=12.0, unit="mm"),
        ParamSpec(name="base_thickness", label="Base Thickness", type="float",
                  default=2.4, min=1.2, max=15.0, unit="mm"),
        ParamSpec(name="corner_radius", label="Corner Radius (Rect/Square)", type="float",
                  default=6.0, min=0.0, max=40.0, unit="mm"),
        ParamSpec(name="include_lid", label="Include matching lid", type="bool",
                  default=True),
        ParamSpec(name="lid_style", label="Lid Style", type="choice",
                  default="Friction Lip",
                  choices=["Friction Lip", "Flat Cap"], group="Lid"),
        ParamSpec(name="lid_thickness", label="Lid Plate Thickness", type="float",
                  default=2.4, min=1.2, max=10.0, unit="mm", group="Lid"),
        ParamSpec(name="lip_height", label="Lip Height", type="float",
                  default=6.0, min=2.0, max=25.0, unit="mm", group="Lid"),
        ParamSpec(name="fit_clearance", label="Lip Clearance (per side)", type="float",
                  default=0.25, min=0.05, max=1.5, unit="mm", group="Lid"),
        ParamSpec(name="lid_overhang", label="Lid Overhang past outer wall", type="float",
                  default=0.0, min=0.0, max=5.0, unit="mm", group="Lid"),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        shape = params["shape"]
        length = mm(params["length"])
        width = mm(params["width"]) if shape == "Rectangle" else length
        height = mm(params["height"])
        wall = mm(params["wall_thickness"])
        base = mm(params["base_thickness"])
        corner_r = mm(params["corner_radius"]) if shape != "Round" else 0.0

        require_min_wall(params["wall_thickness"])
        require_base_below_height(params["base_thickness"], params["height"],
                                   height_label="box height")

        if shape == "Round":
            if wall >= length / 2.0:
                raise ValueError("Wall thickness must be less than half the diameter.")
            box_body = self._build_round_box(component, length / 2.0, height, wall, base)
        else:
            if wall * 2.5 >= min(length, width):
                raise ValueError("Walls are too thick for this box size.")
            if corner_r * 2.0 >= min(length, width) - 2.0 * wall:
                raise ValueError("Corner radius is too large for this box size.")
            box_body = self._build_rect_box(
                component, length, width, height, wall, base, corner_r)

        box_body.name = "Box"

        if not params["include_lid"]:
            return

        lid_t = mm(params["lid_thickness"])
        lip_h = mm(params["lip_height"])
        clearance = mm(params["fit_clearance"])
        overhang = mm(params["lid_overhang"])

        if params["lid_style"] == "Flat Cap":
            lip_h = 0.0

        if shape == "Round":
            lid_offset_y = length + overhang + mm(12.0)
            self._build_round_lid(
                component, length / 2.0, wall, lid_t, lip_h, clearance, overhang,
                lid_offset_y)
        else:
            lid_offset_y = width + overhang + mm(12.0)
            self._build_rect_lid(
                component, length, width, wall, lid_t, lip_h, clearance,
                overhang, corner_r, lid_offset_y)

    def _build_rect_box(self, component, length, width, height, wall, base, corner_r):
        sketch = geometry_utils.sketch_on_xy(component)
        _draw_rounded_rect(sketch, -length / 2, -width / 2, length / 2, width / 2, corner_r)
        body = geometry_utils.extrude_profile(component, sketch.profiles.item(0), height)

        overshoot = geometry_utils.mm(2.0)
        cavity_depth = height - base + overshoot
        cavity_plane = geometry_utils.offset_plane(component, base)
        cavity_sketch = component.sketches.add(cavity_plane)
        inner_r = max(corner_r - wall, 0.0)
        _draw_rounded_rect(
            cavity_sketch,
            -length / 2 + wall, -width / 2 + wall,
            length / 2 - wall, width / 2 - wall,
            inner_r, z=base)
        geometry_utils.extrude_cut(
            component, cavity_sketch.profiles.item(0), cavity_depth,
            participants=[body])
        return body

    def _build_round_box(self, component, radius, height, wall, base):
        profile = [
            (0.0, 0.0),
            (radius, 0.0),
            (radius, height),
            (radius - wall, height),
            (radius - wall, base),
            (0.0, base),
        ]
        sketch = geometry_utils.sketch_on_xz(component)
        geometry_utils.draw_closed_profile_rz(sketch, profile)
        return geometry_utils.revolve_profile(component, sketch.profiles.item(0))

    def _build_rect_lid(self, component, length, width, wall, lid_t, lip_h,
                         clearance, overhang, corner_r, offset_y):
        plate_l = length + 2.0 * overhang
        plate_w = width + 2.0 * overhang
        plate_r = corner_r + overhang if corner_r > 0 else 0.0

        sketch = geometry_utils.sketch_on_xy(component)
        _draw_rounded_rect(
            sketch,
            -plate_l / 2, offset_y - plate_w / 2,
            plate_l / 2, offset_y + plate_w / 2,
            plate_r)
        lid_body = geometry_utils.extrude_profile(
            component, sketch.profiles.item(0), lid_t)
        lid_body.name = "Lid"

        if lip_h <= 1e-6:
            return

        lip_outer_l = length - 2.0 * wall - 2.0 * clearance
        lip_outer_w = width - 2.0 * wall - 2.0 * clearance
        if lip_outer_l < geometry_utils.mm(8.0) or lip_outer_w < geometry_utils.mm(8.0):
            raise ValueError(
                "Lid lip is too small - increase box size or reduce wall/clearance."
            )

        lip_wall = min(wall, geometry_utils.mm(2.0))
        lip_inner_l = lip_outer_l - 2.0 * lip_wall
        lip_inner_w = lip_outer_w - 2.0 * lip_wall
        lip_r = max(corner_r - wall - clearance, 0.0)

        lip_sketch = geometry_utils.sketch_on_xy(component)
        _draw_rounded_rect(
            lip_sketch,
            -lip_outer_l / 2, offset_y - lip_outer_w / 2,
            lip_outer_l / 2, offset_y + lip_outer_w / 2,
            lip_r)

        if lip_inner_l >= geometry_utils.mm(4.0) and lip_inner_w >= geometry_utils.mm(4.0):
            inner_r = max(lip_r - lip_wall, 0.0)
            _draw_rounded_rect(
                lip_sketch,
                -lip_inner_l / 2, offset_y - lip_inner_w / 2,
                lip_inner_l / 2, offset_y + lip_inner_w / 2,
                inner_r)
            profiles = [
                lip_sketch.profiles.item(i)
                for i in range(lip_sketch.profiles.count)
                if lip_sketch.profiles.item(i).profileLoops.count == 2
            ]
            if not profiles:
                profiles = [lip_sketch.profiles.item(0)]
        else:
            profiles = [lip_sketch.profiles.item(0)]

        geometry_utils.extrude_join(
            component, geometry_utils.collect(profiles), lip_h, target_body=lid_body)

    def _build_round_lid(self, component, radius, wall, lid_t, lip_h,
                          clearance, overhang, offset_y):
        plate_r = radius + overhang
        sketch = geometry_utils.sketch_on_xy(component)
        geometry_utils.draw_circle(
            sketch, plate_r,
            adsk.core.Point3D.create(0, offset_y, 0))
        lid_body = geometry_utils.extrude_profile(
            component, sketch.profiles.item(0), lid_t)
        lid_body.name = "Lid"

        if lip_h <= 1e-6:
            return

        lip_outer_r = radius - wall - clearance
        if lip_outer_r < geometry_utils.mm(4.0):
            raise ValueError(
                "Lid lip is too small - increase diameter or reduce wall/clearance."
            )
        lip_wall = min(wall, geometry_utils.mm(2.0))
        lip_inner_r = lip_outer_r - lip_wall

        lip_sketch = geometry_utils.sketch_on_xy(component)
        center = adsk.core.Point3D.create(0, offset_y, 0)
        geometry_utils.draw_circle(lip_sketch, lip_outer_r, center)
        if lip_inner_r > geometry_utils.mm(2.0):
            geometry_utils.draw_circle(lip_sketch, lip_inner_r, center)
            profiles = [
                lip_sketch.profiles.item(i)
                for i in range(lip_sketch.profiles.count)
                if lip_sketch.profiles.item(i).profileLoops.count == 2
            ]
            if not profiles:
                profiles = [lip_sketch.profiles.item(0)]
        else:
            profiles = [lip_sketch.profiles.item(0)]

        geometry_utils.extrude_join(
            component, geometry_utils.collect(profiles), lip_h, target_body=lid_body)
