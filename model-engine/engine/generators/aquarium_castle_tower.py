"""Castle tower for aquarium decor.

A tapered hollow tower with a crenellated (battlement) top, an arched
doorway, and a ring of arched windows. Open at the bottom so it sits over
gravel with no trapped air, and open at the top so fish can pass through -
door and windows are swim-throughs too.

Construction notes: the tower shell is one revolve. Every opening is cut
one-sided - the cut profile lives on a construction plane parked outside
one side of the tower and is cut symmetrically just deep enough to pierce
the near wall but never reach the far one. Crenellations and windows are
one such cut repeated with a circular pattern.
"""

import math

import adsk.core
import adsk.fusion

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..registry import register


@register
class CastleTower(Generator):
    id = "aquarium_castle_tower"
    display_name = "Castle Tower"
    category = "Aquarium Decor"
    parameters = [
        ParamSpec(name="bottom_diameter", label="Bottom Diameter", type="float",
                  default=60.0, min=25.0, max=200.0, unit="mm"),
        ParamSpec(name="top_diameter", label="Top Diameter", type="float",
                  default=50.0, min=20.0, max=200.0, unit="mm"),
        ParamSpec(name="height", label="Height", type="float",
                  default=120.0, min=40.0, max=350.0, unit="mm"),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=2.4, min=1.6, max=8.0, unit="mm"),
        ParamSpec(name="crenellation_count", label="Crenellation Notches", type="int",
                  default=8, min=0, max=24),
        ParamSpec(name="crenellation_depth", label="Crenellation Depth", type="float",
                  default=9.0, min=4.0, max=30.0, unit="mm"),
        ParamSpec(name="door_width", label="Door Width (0 = none)", type="float",
                  default=22.0, min=0.0, max=80.0, unit="mm"),
        ParamSpec(name="door_height", label="Door Height", type="float",
                  default=32.0, min=10.0, max=120.0, unit="mm"),
        ParamSpec(name="window_count", label="Windows", type="int",
                  default=4, min=0, max=10),
        ParamSpec(name="window_width", label="Window Width", type="float",
                  default=10.0, min=4.0, max=40.0, unit="mm"),
        ParamSpec(name="window_height", label="Window Height", type="float",
                  default=16.0, min=6.0, max=60.0, unit="mm"),
        ParamSpec(name="window_center_height", label="Window Center Height", type="float",
                  default=78.0, min=10.0, max=330.0, unit="mm"),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        bottom_r = mm(params["bottom_diameter"]) / 2.0
        top_r = mm(params["top_diameter"]) / 2.0
        height = mm(params["height"])
        wall = mm(params["wall_thickness"])

        if wall >= min(bottom_r, top_r) * 0.8:
            raise ValueError("Wall is too thick for this tower diameter.")

        def outer_r(z):
            z = max(0.0, min(height, z))
            return bottom_r + (top_r - bottom_r) * (z / height)

        # --- tower shell: hollow tube, open top AND bottom ------------------
        profile_points = [
            (bottom_r, 0.0),
            (top_r, height),
            (top_r - wall, height),
            (bottom_r - wall, 0.0),
        ]
        sketch = geometry_utils.sketch_on_xz(component)
        geometry_utils.draw_closed_profile_rz(sketch, profile_points)
        tower_body = geometry_utils.revolve_profile(component, sketch.profiles.item(0))

        # One construction plane parked outside the fattest part of the
        # tower serves every opening; all cuts pierce only the near wall.
        max_r = max(bottom_r, top_r)
        plane_offset = max_r + mm(5.0)
        planes = component.constructionPlanes
        plane_input = planes.createInput()
        plane_input.setByOffset(component.xZConstructionPlane,
                                 adsk.core.ValueInput.createByReal(plane_offset))
        cut_plane = planes.add(plane_input)
        plane_y = cut_plane.geometry.origin.y

        def one_sided_cut(profile, z_of_opening, bite_mm=8.0):
            """Symmetric cut sized to pierce the near wall only."""
            reach = abs(plane_y) - (outer_r(z_of_opening) - wall) + mm(bite_mm)
            geometry_utils.extrude_cut_symmetric(
                component, profile, 2.0 * reach, participants=[tower_body])
            return component.features.extrudeFeatures.item(
                component.features.extrudeFeatures.count - 1)

        def draw_rect(sketch_, x0, z0, x1, z1):
            pts = [
                sketch_.modelToSketchSpace(adsk.core.Point3D.create(x0, plane_y, z0)),
                sketch_.modelToSketchSpace(adsk.core.Point3D.create(x1, plane_y, z0)),
                sketch_.modelToSketchSpace(adsk.core.Point3D.create(x1, plane_y, z1)),
                sketch_.modelToSketchSpace(adsk.core.Point3D.create(x0, plane_y, z1)),
            ]
            lines = sketch_.sketchCurves.sketchLines
            for i in range(4):
                lines.addByTwoPoints(pts[i], pts[(i + 1) % 4])

        def draw_arch(sketch_, x_center, z_bottom, width, arch_height):
            """Rectangle with a semicircular top - a castle doorway/window."""
            half = width / 2.0
            z_spring = z_bottom + arch_height - half  # where the arc starts
            p = lambda x, z: sketch_.modelToSketchSpace(
                adsk.core.Point3D.create(x, plane_y, z))
            lines = sketch_.sketchCurves.sketchLines
            arcs = sketch_.sketchCurves.sketchArcs
            lines.addByTwoPoints(p(x_center - half, z_bottom), p(x_center + half, z_bottom))
            lines.addByTwoPoints(p(x_center + half, z_bottom), p(x_center + half, z_spring))
            arcs.addByThreePoints(p(x_center + half, z_spring),
                                   p(x_center, z_bottom + arch_height),
                                   p(x_center - half, z_spring))
            lines.addByTwoPoints(p(x_center - half, z_spring), p(x_center - half, z_bottom))

        # --- crenellations ---------------------------------------------------
        notch_count = params["crenellation_count"]
        if notch_count > 0:
            notch_h = mm(params["crenellation_depth"])
            rim_circumference = 2.0 * math.pi * top_r
            notch_w = rim_circumference / notch_count * 0.45
            if notch_h >= height * 0.4:
                raise ValueError("Crenellation depth is too large for the tower height.")
            notch_sketch = component.sketches.add(cut_plane)
            draw_rect(notch_sketch, -notch_w / 2.0, height - notch_h,
                       notch_w / 2.0, height + mm(3.0))
            notch_feature = one_sided_cut(notch_sketch.profiles.item(0), height)
            if notch_count > 1:
                geometry_utils.circular_pattern(component, notch_feature, notch_count)

        # --- door ------------------------------------------------------------
        door_w = mm(params["door_width"])
        door_h = mm(params["door_height"])
        if door_w > 0:
            if door_h <= door_w / 2.0 + mm(2.0):
                raise ValueError("Door height must be more than half its width plus 2mm "
                                 "(the arch needs room).")
            if door_w >= 2.0 * (bottom_r - wall) * 0.85:
                raise ValueError("Door is too wide for the tower.")
            door_sketch = component.sketches.add(cut_plane)
            draw_arch(door_sketch, 0.0, -mm(2.0), door_w, door_h + mm(2.0))
            one_sided_cut(door_sketch.profiles.item(0), door_h / 2.0)

        # --- windows ----------------------------------------------------------
        window_count = params["window_count"]
        if window_count > 0:
            win_w = mm(params["window_width"])
            win_h = mm(params["window_height"])
            win_z = mm(params["window_center_height"])
            if win_h <= win_w / 2.0 + mm(1.0):
                raise ValueError("Window height must be more than half its width plus 1mm.")
            top_limit = height - (mm(params["crenellation_depth"]) if notch_count else 0) - mm(4.0)
            if win_z + win_h / 2.0 > top_limit:
                raise ValueError("Windows would run into the crenellations - "
                                 "lower the window center height.")
            if door_w > 0 and win_z - win_h / 2.0 < door_h + mm(5.0):
                raise ValueError("Windows would run into the door - "
                                 "raise the window center height.")
            window_sketch = component.sketches.add(cut_plane)
            draw_arch(window_sketch, 0.0, win_z - win_h / 2.0, win_w, win_h)
            window_feature = one_sided_cut(window_sketch.profiles.item(0), win_z)
            if window_count > 1:
                geometry_utils.circular_pattern(component, window_feature, window_count)
