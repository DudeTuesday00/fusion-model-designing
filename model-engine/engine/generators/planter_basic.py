"""Basic planter: a tapered, hollowed pot with optional drainage holes.

Three shapes share the same parameters:
- Round: one closed cross-section revolved around the vertical axis. No
  separate shell step, so wall and base thickness are exactly what the
  parameters say.
- Hexagon / Square: the outer shell is lofted between a bottom and top
  polygon, then the cavity is lofted out the same way, inset by the wall
  thickness. "Diameter" for these means width across the flats.

Drainage holes are then cut straight up through the base: one centered
hole, or a ring of evenly spaced holes.
"""

import math

import adsk.core
import adsk.fusion

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..registry import register


@register
class BasicPlanter(Generator):
    id = "planter_basic"
    display_name = "Basic Planter"
    category = "Planter"
    parameters = [
        ParamSpec(name="shape", label="Shape", type="choice", default="Round",
                  choices=["Round", "Hexagon", "Square", "Terracotta"]),
        ParamSpec(name="top_diameter", label="Top Width / Diameter", type="float", default=120.0,
                  min=20.0, max=500.0, unit="mm"),
        ParamSpec(name="bottom_diameter", label="Bottom Width / Diameter", type="float", default=90.0,
                  min=20.0, max=500.0, unit="mm"),
        ParamSpec(name="height", label="Height", type="float", default=100.0,
                  min=20.0, max=500.0, unit="mm"),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float", default=3.0,
                  min=1.2, max=20.0, unit="mm"),
        ParamSpec(name="base_thickness", label="Base Thickness", type="float", default=4.0,
                  min=1.2, max=30.0, unit="mm"),
        ParamSpec(name="corner_radius", label="Corner Radius (Square only)", type="float",
                  default=10.0, min=0.0, max=50.0, unit="mm"),
        ParamSpec(name="rim_height", label="Collar Height (Terracotta only)", type="float",
                  default=14.0, min=6.0, max=60.0, unit="mm"),
        ParamSpec(name="rim_protrude", label="Collar Protrusion (Terracotta only)", type="float",
                  default=4.0, min=1.5, max=15.0, unit="mm"),
        ParamSpec(name="drainage_hole_count", label="Drainage Holes", type="int", default=5,
                  min=0, max=20),
        ParamSpec(name="drainage_hole_diameter", label="Drainage Hole Diameter", type="float",
                  default=8.0, min=2.0, max=30.0, unit="mm"),
        ParamSpec(name="rim_style", label="Rim Style", type="choice", default="Flat",
                  choices=["Flat", "Rounded"]),
        ParamSpec(name="flute_count", label="Flutes (Round only, 0 = none)", type="int",
                  default=0, min=0, max=48),
        ParamSpec(name="flute_depth", label="Flute Depth", type="float",
                  default=1.2, min=0.4, max=5.0, unit="mm"),
        ParamSpec(name="flute_style", label="Flute Style", type="choice", default="Straight",
                  choices=["Straight", "Spiral", "CrissCross"]),
        ParamSpec(name="relief", label="Flute/Rib Relief", type="choice", default="Recessed",
                  choices=["Recessed", "Raised"]),
        ParamSpec(name="flute_twist", label="Flute Twist (deg)", type="float",
                  default=20.0, min=5.0, max=180.0),
        ParamSpec(name="texture", label="Surface Texture (Round only)", type="choice",
                  default="None", choices=["None", "Ribbed", "Bubbles", "Bark"]),
        ParamSpec(name="texture_depth", label="Texture Depth", type="float",
                  default=0.8, min=0.3, max=3.0, unit="mm"),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        top_r = mm(params["top_diameter"]) / 2.0
        bottom_r = mm(params["bottom_diameter"]) / 2.0
        height = mm(params["height"])
        wall = mm(params["wall_thickness"])
        base = mm(params["base_thickness"])
        shape = params["shape"]

        if wall >= min(top_r, bottom_r):
            raise ValueError("Wall thickness must be less than half the smallest width/diameter.")
        if base >= height:
            raise ValueError("Base thickness must be less than the planter height.")

        # For Terracotta, top_diameter is the collar (widest point); the body
        # itself tapers to a slightly smaller radius that the collar rings.
        rim_protrude = mm(params["rim_protrude"]) if shape == "Terracotta" else 0.0
        body_top_r = top_r - rim_protrude

        def outer_radius_at(z):
            # Straight taper of the pot BODY (across-flats for polygons).
            return bottom_r + (body_top_r - bottom_r) * (z / height)

        # Flutes/textures run to the top of the pot, except on Terracotta
        # where they stop below the collar (like real fluted clay pots).
        deco_top = height
        if shape == "Terracotta":
            deco_top = height - mm(params["rim_height"]) - rim_protrude - mm(2.0)

        if shape == "Round":
            pot_body = self._build_round(component, top_r, bottom_r, height, wall, base,
                                          outer_radius_at)
        elif shape == "Terracotta":
            pot_body = self._build_terracotta(component, top_r, bottom_r, height, wall,
                                               base, mm(params["rim_height"]),
                                               rim_protrude, outer_radius_at)
        else:
            sides = 6 if shape == "Hexagon" else 4
            corner_r = mm(params["corner_radius"]) if shape == "Square" else 0.0
            if corner_r >= min(top_r, bottom_r):
                raise ValueError("Corner radius must be less than half the smallest width.")
            pot_body = self._build_polygon(component, sides, top_r, bottom_r, height,
                                            wall, base, corner_r, outer_radius_at)

        if params["rim_style"] == "Rounded":
            # Round the rim before flutes are cut - fillets on a wavy fluted
            # rim are fragile, on a clean rim they always succeed.
            rim_edges = geometry_utils.edges_at_height(pot_body, height)
            if rim_edges:
                geometry_utils.fillet_edges(component, rim_edges,
                                             min(wall * 0.35, mm(1.5)))

        if params["texture"] != "None":
            if shape not in ("Round", "Terracotta"):
                raise ValueError("Surface textures are only supported on Round and "
                                 "Terracotta planters for now.")
            self._apply_texture(component, pot_body, params, deco_top, base,
                                 outer_radius_at, wall)

        if params["flute_count"] > 0:
            if shape not in ("Round", "Terracotta"):
                raise ValueError("Flutes are only supported on Round and Terracotta "
                                 "planters for now.")
            self._cut_flutes(component, pot_body, params, deco_top, base,
                              outer_radius_at, wall)

        self._cut_drainage_holes(component, pot_body, params, wall, base, outer_radius_at)

    def _build_round(self, component, top_r, bottom_r, height, wall, base, outer_radius_at):
        # Cross-section as (radius, height) points, walked counterclockwise:
        # center-bottom, out along the base, up the outer wall, in across the
        # rim, down the inner wall, across the cavity floor, back to center.
        profile_points = [
            (0.0, 0.0),
            (bottom_r, 0.0),
            (top_r, height),
            (top_r - wall, height),
            (outer_radius_at(base) - wall, base),
            (0.0, base),
        ]
        sketch = geometry_utils.sketch_on_xz(component)
        geometry_utils.draw_closed_profile_rz(sketch, profile_points)
        return geometry_utils.revolve_profile(component, sketch.profiles.item(0))

    def _build_terracotta(self, component, top_r, bottom_r, height, wall, base,
                           rim_h, rim_protrude, outer_radius_at):
        """Classic clay flowerpot: tapered body with a thick collar ringing
        the rim. The interior stays a smooth taper - the collar is extra
        material on the outside, exactly like a real thrown pot. A 45-degree
        chamfer eases into the collar's underside so it prints supportless.
        """
        if rim_h + rim_protrude >= height * 0.45:
            raise ValueError("The collar is too tall for this pot - reduce the "
                             "collar height or protrusion.")
        if wall >= outer_radius_at(height) * 0.8:
            raise ValueError("Wall is too thick for the pot body inside the collar - "
                             "thin the wall or reduce the collar protrusion.")

        collar_bottom = height - rim_h
        chamfer_start = collar_bottom - rim_protrude  # 45-degree lead-in

        profile_points = [
            (0.0, 0.0),
            (bottom_r, 0.0),
            (outer_radius_at(chamfer_start), chamfer_start),  # up the body
            (top_r, collar_bottom),                           # chamfer out
            (top_r, height),                                  # collar band
            (outer_radius_at(height) - wall, height),         # rim top face
            (outer_radius_at(base) - wall, base),             # smooth interior
            (0.0, base),
        ]
        sketch = geometry_utils.sketch_on_xz(component)
        geometry_utils.draw_closed_profile_rz(sketch, profile_points)
        return geometry_utils.revolve_profile(component, sketch.profiles.item(0))

    def _build_polygon(self, component, sides, top_r, bottom_r, height, wall, base,
                        corner_r, outer_radius_at):
        # Rounded corners shrink with the wall inset (sharp once the wall eats them).
        inner_corner_r = max(corner_r - wall, 0.0) if corner_r > 0 else 0.0
        return geometry_utils.build_polygon_shell(
            component, sides,
            outer_bottom_r=bottom_r, outer_top_r=top_r,
            inner_floor_r=outer_radius_at(base) - wall, inner_top_r=top_r - wall,
            height_cm=height, base_cm=base,
            outer_corner_r=corner_r, inner_corner_r=inner_corner_r,
        )

    def _cut_groove(self, component, pot_body, z0, z1, outer_radius_at,
                     groove_r, depth, twist_deg, start_deg=0.0, raised=False):
        """Builds ONE vertical/spiral groove (recessed) or rib (raised) on
        the outer wall. Returns the feature list to circular-pattern.

        The shape is lofted through intermediate circle sections - one per
        ~10 degrees of twist - so a twisted groove follows the pot's surface
        instead of cutting a straight chord through it. Recessed: each circle
        bites `depth` into the wall. Raised: each circle bulges `depth` out
        of the wall, and the lofted body is fused onto the pot.
        """
        section_count = max(2, int(abs(twist_deg) / 10.0) + 2)
        lofts = component.features.loftFeatures
        operation = (adsk.fusion.FeatureOperations.NewBodyFeatureOperation if raised
                     else adsk.fusion.FeatureOperations.CutFeatureOperation)
        loft_input = lofts.createInput(operation)
        for k in range(section_count):
            frac = k / (section_count - 1)
            z = z0 + (z1 - z0) * frac
            angle = math.radians(start_deg + twist_deg * frac)
            if raised:
                r_center = outer_radius_at(z) - groove_r + depth
            else:
                r_center = outer_radius_at(z) + groove_r - depth
            plane = geometry_utils.offset_plane(component, z)
            sketch = component.sketches.add(plane)
            center = sketch.modelToSketchSpace(adsk.core.Point3D.create(
                r_center * math.cos(angle), r_center * math.sin(angle), z))
            geometry_utils.draw_circle(sketch, groove_r, center)
            loft_input.loftSections.add(sketch.profiles.item(0))
        if raised:
            loft_feature = lofts.add(loft_input)
            rib_bodies = [loft_feature.bodies.item(i) for i in range(loft_feature.bodies.count)]
            combine_feature = geometry_utils.combine_join(component, pot_body, rib_bodies)
            return [loft_feature, combine_feature]
        loft_input.participantBodies = [pot_body]
        return [lofts.add(loft_input)]

    def _cut_flutes(self, component, pot_body, params, height, base, outer_radius_at, wall):
        """Straight, spiral, or crisscrossing flutes around the pot."""
        mm = geometry_utils.mm
        count = params["flute_count"]
        depth = mm(params["flute_depth"])
        style = params["flute_style"]
        twist = params["flute_twist"] if style in ("Spiral", "CrissCross") else 0.0
        raised = params["relief"] == "Raised"

        if not raised and depth >= wall - mm(1.2):
            raise ValueError("Flute depth would leave the wall thinner than 1.2mm - "
                             "reduce the depth or thicken the wall.")

        # The groove is the intersection of a circle with the wall: circle
        # radius 2x depth gives a shallow, wide scallop (~3.5x depth wide).
        groove_r = depth * 2.0
        groove_w = 2.0 * math.sqrt(depth * (2.0 * groove_r - depth))
        z_start = base + mm(3.0)  # keep the bottom edge of the pot clean

        bottom_spacing = 2.0 * math.pi * outer_radius_at(z_start) / count
        if bottom_spacing < groove_w + mm(2.0):
            raise ValueError("Too many flutes for this pot - reduce the flute "
                             "count or depth.")

        first = self._cut_groove(component, pot_body, z_start, height,
                                  outer_radius_at, groove_r, depth, twist,
                                  raised=raised)
        geometry_utils.circular_pattern(component, first, count)

        if style == "CrissCross":
            second = self._cut_groove(component, pot_body, z_start, height,
                                       outer_radius_at, groove_r, depth, -twist,
                                       raised=raised)
            geometry_utils.circular_pattern(component, second, count)

    def _apply_texture(self, component, pot_body, params, height, base, outer_radius_at, wall):
        mm = geometry_utils.mm
        texture = params["texture"]
        depth = mm(params["texture_depth"])

        if depth >= wall - mm(1.0):
            raise ValueError("Texture depth would leave the wall thinner than 1mm - "
                             "reduce the depth or thicken the wall.")

        if texture == "Ribbed":
            # Horizontal wave rings: a half-round profile revolved around the
            # pot, repeated up the wall. Each ring is sized at its own height
            # because the taper changes the radius as we climb. Recessed
            # rings are cut in; raised rings are revolved as new bodies and
            # fused on.
            raised = params["relief"] == "Raised"
            groove_r = depth * 2.0
            pitch = groove_r * 3.0
            z = base + groove_r * 3.0
            while z <= height - groove_r * 2.0:
                sketch = geometry_utils.sketch_on_xz(component)
                r_center = (outer_radius_at(z) - groove_r + depth if raised
                            else outer_radius_at(z) + groove_r - depth)
                center = sketch.modelToSketchSpace(adsk.core.Point3D.create(r_center, 0, z))
                geometry_utils.draw_circle(sketch, groove_r, center)
                if raised:
                    ring_body = geometry_utils.revolve_profile(component,
                                                                 sketch.profiles.item(0))
                    geometry_utils.combine_join(component, pot_body, [ring_body])
                else:
                    geometry_utils.revolve_cut(component, sketch.profiles.item(0),
                                                participants=[pot_body])
                z += pitch

        elif texture == "Bubbles":
            # Rows of round dimples. Each row gets its own master dimple and
            # circular pattern, sized at its own height (taper again).
            dimple_r = max(depth * 2.5, mm(2.5))
            row_pitch = dimple_r * 2.0 + mm(2.5)
            z = base + dimple_r + mm(3.0)
            row = 0
            while z <= height - dimple_r - mm(2.0):
                r_wall = outer_radius_at(z)
                plane_offset = r_wall + mm(5.0)
                plane = component.constructionPlanes
                plane_input = plane.createInput()
                plane_input.setByOffset(component.xZConstructionPlane,
                                         adsk.core.ValueInput.createByReal(plane_offset))
                dimple_plane = plane.add(plane_input)
                sketch = component.sketches.add(dimple_plane)
                # Read back where the plane actually landed (offset direction
                # from the XZ plane isn't guaranteed) and cut symmetrically
                # through it so we always reach the wall.
                plane_y = dimple_plane.geometry.origin.y
                center = sketch.modelToSketchSpace(adsk.core.Point3D.create(0, plane_y, z))
                geometry_utils.draw_circle(sketch, dimple_r, center)
                reach = 2.0 * (abs(plane_y) - (r_wall - depth))
                feature = geometry_utils.extrude_cut_symmetric(
                    component, sketch.profiles.item(0), reach, participants=[pot_body])
                per_row = int(2.0 * math.pi * r_wall / (dimple_r * 2.0 + mm(2.0)))
                if per_row > 1:
                    geometry_utils.circular_pattern(component, feature, per_row)
                z += row_pitch
                row += 1

        elif texture == "Bark":
            # Three overlapping sets of vertical striations with different
            # widths, depths, and slight opposing leans - irregular enough
            # to read as bark without any random numbers.
            z_start = base + mm(2.0)
            recipes = [
                # (count, depth scale, groove radius scale, twist deg, start deg)
                (10, 1.00, 2.0, 4.0, 0.0),
                (8, 0.60, 3.2, -6.0, 17.0),
                (13, 0.80, 1.4, 9.0, 31.0),
            ]
            for (count, d_scale, r_scale, twist, start) in recipes:
                d = depth * d_scale
                feature = self._cut_groove(component, pot_body, z_start, height,
                                            outer_radius_at, d * r_scale, d,
                                            twist, start)
                geometry_utils.circular_pattern(component, feature, count)

    def _cut_drainage_holes(self, component, pot_body, params, wall, base, outer_radius_at):
        mm = geometry_utils.mm
        hole_count = params["drainage_hole_count"]
        if hole_count == 0:
            return

        hole_r = mm(params["drainage_hole_diameter"]) / 2.0
        # Across-flats inner radius at floor level - for polygons this is the
        # tightest direction, so holes that fit here fit everywhere.
        floor_r = outer_radius_at(base) - wall
        margin = mm(2.0)  # keep holes clear of the wall

        if hole_count == 1:
            centers = [(0.0, 0.0)]
            if hole_r > floor_r - margin:
                raise ValueError("Drainage hole is too big for the planter base.")
        else:
            ring_r = floor_r * 0.55
            if ring_r + hole_r > floor_r - margin:
                raise ValueError(
                    "Drainage holes are too big for the planter base - "
                    "reduce the hole diameter or hole count."
                )
            # Adjacent holes on the ring must not overlap each other.
            gap_between_centers = 2.0 * ring_r * math.sin(math.pi / hole_count)
            if gap_between_centers < hole_r * 2.0 + mm(1.0):
                raise ValueError(
                    "Too many drainage holes to fit on the base - "
                    "reduce the hole count or hole diameter."
                )
            centers = [
                (ring_r * math.cos(2.0 * math.pi * i / hole_count),
                 ring_r * math.sin(2.0 * math.pi * i / hole_count))
                for i in range(hole_count)
            ]

        hole_sketch = geometry_utils.sketch_on_xy(component)
        for (cx, cy) in centers:
            geometry_utils.draw_circle(
                hole_sketch, hole_r, adsk.core.Point3D.create(cx, cy, 0)
            )
        profiles = geometry_utils.collect(
            [hole_sketch.profiles.item(i) for i in range(hole_sketch.profiles.count)]
        )
        geometry_utils.extrude_cut(component, profiles, base, participants=[pot_body])
