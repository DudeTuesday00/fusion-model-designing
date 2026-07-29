"""Plant stand: a raised platform that elevates a pot off the shelf.

The platform is a shallow drip tray (it catches overflow too); the legs are
separate columns printed lying... no - standing flat, each with an
alignment peg on top. Sockets in the platform's underside locate them for
gluing. Everything prints supportless: platform flat on its base, legs
straight up.
"""

import math

import adsk.core
import adsk.fusion

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..registry import register
from .planter_drip_tray import revolve_round_tray


@register
class PlantStand(Generator):
    id = "planter_stand"
    display_name = "Plant Stand (Round)"
    category = "Planter"
    parameters = [
        ParamSpec(name="pot_bottom_diameter", label="Pot Bottom Diameter", type="float",
                  default=90.0, min=40.0, max=400.0, unit="mm"),
        ParamSpec(name="clearance", label="Clearance Around Pot", type="float",
                  default=3.0, min=0.5, max=20.0, unit="mm"),
        ParamSpec(name="lip_height", label="Platform Lip Height", type="float",
                  default=14.0, min=8.0, max=40.0, unit="mm"),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=2.4, min=1.6, max=8.0, unit="mm"),
        ParamSpec(name="platform_thickness", label="Platform Thickness", type="float",
                  default=5.0, min=3.0, max=12.0, unit="mm"),
        ParamSpec(name="leg_count", label="Legs", type="int", default=3,
                  min=3, max=6),
        ParamSpec(name="leg_length", label="Leg Length", type="float",
                  default=90.0, min=30.0, max=250.0, unit="mm"),
        ParamSpec(name="leg_diameter", label="Leg Diameter", type="float",
                  default=18.0, min=10.0, max=40.0, unit="mm"),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        pot_r = mm(params["pot_bottom_diameter"]) / 2.0
        clearance = mm(params["clearance"])
        lip = mm(params["lip_height"])
        wall = mm(params["wall_thickness"])
        platform_t = mm(params["platform_thickness"])
        leg_count = params["leg_count"]
        leg_len = mm(params["leg_length"])
        leg_r = mm(params["leg_diameter"]) / 2.0

        if platform_t >= lip:
            raise ValueError("Platform thickness must be less than the lip height.")

        floor_r = pot_r + clearance
        rim_r = floor_r + (lip - platform_t) * math.tan(math.radians(12.0))
        platform = revolve_round_tray(component, floor_r, rim_r, lip, wall, platform_t)

        # Legs sit near the platform's edge so the load path is short.
        leg_ring_r = floor_r + wall - leg_r
        if leg_ring_r <= leg_r + mm(5.0):
            raise ValueError("Legs are too wide for this platform size.")

        peg_d = min(mm(9.0), leg_r)
        socket_depth = min(mm(3.0), platform_t - mm(1.5))
        peg_h = socket_depth - mm(0.3)

        # Sockets up into the platform's underside.
        socket_sketch = geometry_utils.sketch_on_xy(component)
        for i in range(leg_count):
            angle = 2.0 * math.pi * i / leg_count
            geometry_utils.draw_circle(
                socket_sketch, (peg_d + mm(0.4)) / 2.0,
                adsk.core.Point3D.create(leg_ring_r * math.cos(angle),
                                          leg_ring_r * math.sin(angle), 0))
        geometry_utils.extrude_cut(
            component,
            geometry_utils.collect([socket_sketch.profiles.item(i)
                                     for i in range(socket_sketch.profiles.count)]),
            socket_depth, participants=[platform])

        # Legs in a row beside the platform, pegs up. Each is a column with
        # a slight taper (wider at the floor) for stability and looks.
        row_y = -(floor_r + wall + leg_r * 2.0 + mm(10.0))
        spacing = leg_r * 2.0 + mm(8.0)
        peg_plane = geometry_utils.offset_plane(component, leg_len)
        for i in range(leg_count):
            fx = (i - (leg_count - 1) / 2.0) * spacing
            # Tapered column via revolve is awkward off-axis; a straight
            # cylinder prints and looks fine at these sizes.
            leg_sketch = geometry_utils.sketch_on_xy(component)
            geometry_utils.draw_circle(leg_sketch, leg_r,
                                        adsk.core.Point3D.create(fx, row_y, 0))
            leg_body = geometry_utils.extrude_profile(
                component, leg_sketch.profiles.item(0), leg_len)
            peg_sketch = component.sketches.add(peg_plane)
            center = peg_sketch.modelToSketchSpace(
                adsk.core.Point3D.create(fx, row_y, leg_len))
            geometry_utils.draw_circle(peg_sketch, peg_d / 2.0, center)
            peg_bodies = geometry_utils.extrude_symmetric_all(
                component, geometry_utils.collect([peg_sketch.profiles.item(0)]),
                2.0 * peg_h)
            geometry_utils.combine_join(component, leg_body, peg_bodies)
