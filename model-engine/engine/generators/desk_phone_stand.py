"""Parametric phone / tablet stand.

A single-piece stand with an adjustable lean angle, device slot width/depth,
and a rear support lip. Prints flat on the base — no supports for typical angles.
"""

import math

import adsk.core

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..printability import require_min_wall
from ..registry import register


@register
class DeskPhoneStand(Generator):
    id = "desk_phone_stand"
    display_name = "Phone / Tablet Stand"
    category = "Desk"
    parameters = [
        ParamSpec(name="width", label="Stand Width", type="float",
                  default=80.0, min=40.0, max=200.0, unit="mm"),
        ParamSpec(name="depth", label="Base Depth", type="float",
                  default=90.0, min=50.0, max=200.0, unit="mm"),
        ParamSpec(name="lean_angle", label="Lean Angle (deg from vertical)", type="float",
                  default=20.0, min=5.0, max=40.0),
        ParamSpec(name="slot_width", label="Device Slot Width", type="float",
                  default=12.0, min=8.0, max=25.0, unit="mm"),
        ParamSpec(name="slot_depth", label="Slot Depth (into stand)", type="float",
                  default=14.0, min=6.0, max=30.0, unit="mm"),
        ParamSpec(name="back_height", label="Back Support Height", type="float",
                  default=55.0, min=25.0, max=120.0, unit="mm"),
        ParamSpec(name="front_lip", label="Front Lip Height", type="float",
                  default=8.0, min=3.0, max=20.0, unit="mm"),
        ParamSpec(name="thickness", label="Wall / Base Thickness", type="float",
                  default=4.0, min=2.0, max=10.0, unit="mm"),
        ParamSpec(name="cable_notch", label="Cable Notch Width (0 = none)", type="float",
                  default=10.0, min=0.0, max=25.0, unit="mm"),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        require_min_wall(params["thickness"], minimum_mm=2.0)

        width = mm(params["width"])
        depth = mm(params["depth"])
        angle = math.radians(params["lean_angle"])
        slot_w = mm(params["slot_width"])
        slot_d = mm(params["slot_depth"])
        back_h = mm(params["back_height"])
        lip_h = mm(params["front_lip"])
        t = mm(params["thickness"])
        notch = mm(params["cable_notch"])

        # Side-profile points in XZ (width along Y). Build as thin solid extruded in Y.
        # Base from x=0 to x=depth on the desk. Slot near front, back panel leans.
        #
        # Profile (counter-clockwise):
        #   origin front-bottom → back-bottom → up back → top of back → down to slot
        #   → slot floor → front lip → back to origin.

        # Horizontal run of the leaning back face projected on the base:
        lean_run = back_h * math.tan(angle)
        if lean_run + slot_d + t > depth:
            raise ValueError(
                "Stand is too shallow for this lean angle and back height — "
                "increase base depth or reduce angle/height."
            )

        # x increases toward the back of the stand.
        front = 0.0
        slot_front = t
        slot_back = slot_front + slot_d
        back_base = depth
        back_top_x = back_base - lean_run

        # Cross-section on XZ plane, extruded symmetrically along Y.
        pts = [
            (front, 0.0),
            (back_base, 0.0),
            (back_base, t),
            (back_top_x, t + back_h),
            (back_top_x - t * math.cos(angle), t + back_h - t * math.sin(angle)),
            # inside of back down toward slot
            (slot_back, t + lip_h),
            (slot_back, t),
            (slot_front, t),
            (slot_front, t + lip_h),
            (front + t, t + lip_h),
            (front + t, t),
            (front, t),
        ]

        sketch = geometry_utils.sketch_on_xz(component)
        lines = sketch.sketchCurves.sketchLines
        sk_pts = [
            sketch.modelToSketchSpace(adsk.core.Point3D.create(x, 0, z))
            for (x, z) in pts
        ]
        for i in range(len(sk_pts)):
            lines.addByTwoPoints(sk_pts[i], sk_pts[(i + 1) % len(sk_pts)])

        if sketch.profiles.count == 0:
            raise ValueError("Could not form stand profile — try milder angles.")

        body = geometry_utils.extrude_symmetric(
            component, sketch.profiles.item(0), width)
        body.name = "PhoneStand"

        # Optional cable notch in the front lip / base
        if notch > geometry_utils.mm(1.0):
            notch_sketch = geometry_utils.sketch_on_xy(component)
            half = notch / 2.0
            # Notch from front edge back through the lip zone
            npts = [
                notch_sketch.modelToSketchSpace(adsk.core.Point3D.create(front - mm(1), -half, 0)),
                notch_sketch.modelToSketchSpace(adsk.core.Point3D.create(slot_front + mm(1), -half, 0)),
                notch_sketch.modelToSketchSpace(adsk.core.Point3D.create(slot_front + mm(1), half, 0)),
                notch_sketch.modelToSketchSpace(adsk.core.Point3D.create(front - mm(1), half, 0)),
            ]
            nlines = notch_sketch.sketchCurves.sketchLines
            for i in range(4):
                nlines.addByTwoPoints(npts[i], npts[(i + 1) % 4])
            if notch_sketch.profiles.count > 0:
                geometry_utils.extrude_cut(
                    component, notch_sketch.profiles.item(0),
                    t + lip_h + mm(2), participants=[body])
