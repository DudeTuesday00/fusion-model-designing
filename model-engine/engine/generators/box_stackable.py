"""Stackable storage box with interlocking lip / recess.

Each box has:
- A raised step around the top rim (male stack lip)
- A matching recess under the base (female socket)

Identical boxes stack securely. Optional friction-fit lid still available;
stacking works with or without lids (lid sits inside the top lip).
"""

import adsk.core

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..printability import require_base_below_height, require_min_wall
from ..registry import register
from .box_basic import _draw_rounded_rect, _outer_profile, _ring_profile


@register
class StackableBox(Generator):
    id = "box_stackable"
    display_name = "Stackable Box + Lid"
    category = "Storage"
    parameters = [
        ParamSpec(name="shape", label="Shape", type="choice", default="Rectangle",
                  choices=["Rectangle", "Square"]),
        ParamSpec(name="length", label="Length (X)", type="float",
                  default=100.0, min=30.0, max=400.0, unit="mm"),
        ParamSpec(name="width", label="Width (Y) — Square uses Length", type="float",
                  default=70.0, min=30.0, max=400.0, unit="mm"),
        ParamSpec(name="height", label="Box Height", type="float",
                  default=50.0, min=20.0, max=300.0, unit="mm"),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=2.4, min=1.2, max=12.0, unit="mm"),
        ParamSpec(name="base_thickness", label="Base Thickness", type="float",
                  default=3.0, min=2.0, max=15.0, unit="mm"),
        ParamSpec(name="corner_radius", label="Corner Radius", type="float",
                  default=6.0, min=0.0, max=40.0, unit="mm"),
        ParamSpec(name="stack_depth", label="Stack Lip / Recess Depth", type="float",
                  default=3.0, min=1.5, max=10.0, unit="mm", group="Stack"),
        ParamSpec(name="stack_inset", label="Stack Step Width", type="float",
                  default=2.0, min=1.0, max=6.0, unit="mm", group="Stack"),
        ParamSpec(name="stack_clearance", label="Stack Clearance (per side)", type="float",
                  default=0.3, min=0.1, max=1.0, unit="mm", group="Stack"),
        ParamSpec(name="include_lid", label="Include matching lid", type="bool",
                  default=True),
        ParamSpec(name="lid_thickness", label="Lid Plate Thickness", type="float",
                  default=2.4, min=1.2, max=10.0, unit="mm", group="Lid"),
        ParamSpec(name="lip_height", label="Lid Lip Height", type="float",
                  default=5.0, min=2.0, max=20.0, unit="mm", group="Lid"),
        ParamSpec(name="fit_clearance", label="Lid Lip Clearance", type="float",
                  default=0.25, min=0.05, max=1.5, unit="mm", group="Lid"),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        shape = params["shape"]
        length = mm(params["length"])
        width = mm(params["width"]) if shape == "Rectangle" else length
        height = mm(params["height"])
        wall = mm(params["wall_thickness"])
        base = mm(params["base_thickness"])
        corner_r = mm(params["corner_radius"])
        stack_d = mm(params["stack_depth"])
        stack_inset = mm(params["stack_inset"])
        stack_clr = mm(params["stack_clearance"])

        require_min_wall(params["wall_thickness"])
        require_base_below_height(params["base_thickness"], params["height"],
                                   height_label="box height")

        if base < stack_d + mm(1.0):
            raise ValueError(
                "Base thickness must be greater than stack depth + 1 mm "
                "so the recess does not break through the floor."
            )
        if wall * 2.5 >= min(length, width):
            raise ValueError("Walls are too thick for this box size.")
        if stack_inset + stack_clr >= wall:
            raise ValueError(
                "Stack step + clearance must be less than wall thickness."
            )

        body = self._build_box(
            component, length, width, height, wall, base, corner_r,
            stack_d, stack_inset, stack_clr)
        body.name = "StackableBox"

        if not params["include_lid"]:
            return

        lid_t = mm(params["lid_thickness"])
        lip_h = mm(params["lip_height"])
        fit = mm(params["fit_clearance"])
        offset_y = width + mm(12.0)
        self._build_lid(
            component, length, width, wall, lid_t, lip_h, fit, corner_r, offset_y)

    def _build_box(self, component, length, width, height, wall, base,
                    corner_r, stack_d, stack_inset, stack_clr):
        # Outer solid
        sketch = geometry_utils.sketch_on_xy(component)
        _draw_rounded_rect(sketch, -length / 2, -width / 2, length / 2, width / 2, corner_r)
        body = geometry_utils.extrude_profile(component, _outer_profile(sketch), height)

        # Interior cavity (floor at base)
        overshoot = geometry_utils.mm(2.0)
        cavity_plane = geometry_utils.offset_plane(component, base)
        cavity_sketch = component.sketches.add(cavity_plane)
        inner_r = max(corner_r - wall, 0.0)
        _draw_rounded_rect(
            cavity_sketch,
            -length / 2 + wall, -width / 2 + wall,
            length / 2 - wall, width / 2 - wall,
            inner_r, z=base)
        geometry_utils.extrude_cut(
            component, _outer_profile(cavity_sketch),
            height - base + overshoot, participants=[body])

        # Top stack lip: cut a step around the outside of the rim so the
        # remaining upper collar is smaller and can enter the next box's recess.
        # Outer kept full-size up to (height - stack_d); above that, outer is
        # reduced by stack_inset.
        lip_outer_l = length - 2.0 * stack_inset
        lip_outer_w = width - 2.0 * stack_inset
        lip_r = max(corner_r - stack_inset, 0.0)
        rim_plane = geometry_utils.offset_plane(component, height - stack_d)
        step_sketch = component.sketches.add(rim_plane)
        # Outer rectangle (full size) minus inner (lip size) = ring to cut away.
        _draw_rounded_rect(
            step_sketch,
            -length / 2 - geometry_utils.mm(1.0),
            -width / 2 - geometry_utils.mm(1.0),
            length / 2 + geometry_utils.mm(1.0),
            width / 2 + geometry_utils.mm(1.0),
            corner_r + geometry_utils.mm(1.0),
            z=height - stack_d)
        _draw_rounded_rect(
            step_sketch,
            -lip_outer_l / 2, -lip_outer_w / 2,
            lip_outer_l / 2, lip_outer_w / 2,
            lip_r, z=height - stack_d)
        geometry_utils.extrude_cut(
            component, _ring_profile(step_sketch), stack_d + overshoot,
            participants=[body])

        # Bottom recess (socket): cut into the underside so the lip of a box
        # below can register. Socket is slightly larger than the lip.
        socket_l = lip_outer_l + 2.0 * stack_clr
        socket_w = lip_outer_w + 2.0 * stack_clr
        socket_r = max(lip_r + stack_clr, 0.0)
        # Keep a frame of material: don't cut all the way to the outer edge.
        # Ring = outer footprint minus the central island that matches the lip.
        # We cut only the ring region from Z=0 upward by stack_d.
        bottom_sketch = geometry_utils.sketch_on_xy(component)
        _draw_rounded_rect(
            bottom_sketch,
            -length / 2 + geometry_utils.mm(0.4),
            -width / 2 + geometry_utils.mm(0.4),
            length / 2 - geometry_utils.mm(0.4),
            width / 2 - geometry_utils.mm(0.4),
            max(corner_r - geometry_utils.mm(0.4), 0.0))
        _draw_rounded_rect(
            bottom_sketch,
            -socket_l / 2, -socket_w / 2,
            socket_l / 2, socket_w / 2,
            socket_r)
        geometry_utils.extrude_cut(
            component, _ring_profile(bottom_sketch), stack_d,
            participants=[body])

        return body

    def _build_lid(self, component, length, width, wall, lid_t, lip_h,
                    fit, corner_r, offset_y):
        sketch = geometry_utils.sketch_on_xy(component)
        _draw_rounded_rect(
            sketch,
            -length / 2, offset_y - width / 2,
            length / 2, offset_y + width / 2,
            corner_r)
        lid_body = geometry_utils.extrude_profile(
            component, _outer_profile(sketch), lid_t)
        lid_body.name = "Lid"

        if lip_h <= 1e-6:
            return

        lip_outer_l = length - 2.0 * wall - 2.0 * fit
        lip_outer_w = width - 2.0 * wall - 2.0 * fit
        if lip_outer_l < geometry_utils.mm(8.0) or lip_outer_w < geometry_utils.mm(8.0):
            raise ValueError("Lid lip too small - enlarge the box or thin the walls.")

        lip_wall = min(wall, geometry_utils.mm(2.0))
        lip_r = max(corner_r - wall - fit, 0.0)
        lip_sketch = geometry_utils.sketch_on_xy(component)
        _draw_rounded_rect(
            lip_sketch,
            -lip_outer_l / 2, offset_y - lip_outer_w / 2,
            lip_outer_l / 2, offset_y + lip_outer_w / 2,
            lip_r)

        lip_inner_l = lip_outer_l - 2.0 * lip_wall
        lip_inner_w = lip_outer_w - 2.0 * lip_wall
        if lip_inner_l >= geometry_utils.mm(4.0) and lip_inner_w >= geometry_utils.mm(4.0):
            _draw_rounded_rect(
                lip_sketch,
                -lip_inner_l / 2, offset_y - lip_inner_w / 2,
                lip_inner_l / 2, offset_y + lip_inner_w / 2,
                max(lip_r - lip_wall, 0.0))
            profile = _ring_profile(lip_sketch)
        else:
            profile = _outer_profile(lip_sketch)

        geometry_utils.extrude_join(
            component, profile, lip_h, target_body=lid_body)
