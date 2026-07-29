"""Square scoop with a handle on the short (low-lip) side of the mouth.

A hollow rounded-square cup (built the same way as the polygon planters -
geometry_utils.build_polygon_shell) with the same angled scoop mouth cut
used on the Turned-Handle Scoop (angled_plane_through_x + cut_half_space -
a knife-cut through a solid works the same regardless of what the solid's
cross-section is). The handle mounts on the FRONT wall - the short/low
side of the angled mouth - so the tall back wall extends away from your
hand as a deep backstop, maximizing how much you can scoop up in one pass.

Two handle styles:
- "Square Bracket" (default): three straight extruded bars forming a "["
  staple - flat faces, no curves in space, the most reliably printable
  option and the recommended default.
- "Arched Loop": a curved mug-style handle swept along a fitted spline
  (see _build_arched_loop for why a spline and not a raw circular arc).

Wall attachment (both styles): a handle thicker than the wall - the usual
case, since a 9mm handle vs a 2.4mm wall is normal - must NOT be centered
on the wall; centering it would push the inner half of its cross-section
straight through the inner wall surface into the hollow cavity. Both
builders instead pin the attachment's near EDGE just inside the outer
wall surface (by a small `overlap`, comfortably less than the wall
thickness) and let the handle's full thickness extend outward from there -
so the handle bar/tube's thickness can never reach the interior, no matter
how thick it is relative to the wall.
"""

import math

import adsk.core
import adsk.fusion

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..registry import register


def _draw_rect(sketch, y0, y1, z0, z1):
    """Axis-aligned rectangle in the sketch's (model Y, model Z) plane."""
    pts = [
        sketch.modelToSketchSpace(adsk.core.Point3D.create(0.0, min(y0, y1), min(z0, z1))),
        sketch.modelToSketchSpace(adsk.core.Point3D.create(0.0, max(y0, y1), min(z0, z1))),
        sketch.modelToSketchSpace(adsk.core.Point3D.create(0.0, max(y0, y1), max(z0, z1))),
        sketch.modelToSketchSpace(adsk.core.Point3D.create(0.0, min(y0, y1), max(z0, z1))),
    ]
    lines = sketch.sketchCurves.sketchLines
    for i in range(4):
        lines.addByTwoPoints(pts[i], pts[(i + 1) % 4])


def _draw_diagonal_bar(sketch, y0, z0, y1, z1, half_thick):
    """A `half_thick*2`-wide bar running from (y0,z0) to (y1,z1). The far end
    (y1,z1) is cut perpendicular to the bar's own direction - it's absorbed
    into the crossbar there, so its exact shape doesn't matter. The near end
    (y0,z0) - the wall attachment - is instead cut FLUSH VERTICAL (a plane
    of constant y0), matching the wall's own surface, rather than
    perpendicular to the bar's slope: a perpendicular cut at an angle has one
    corner land outside the wall's outer face and above the attach point, a
    small floating tab poking past the body with only a sliver actually
    fused to it."""
    dy, dz = y1 - y0, z1 - z0
    length = math.hypot(dy, dz)
    ny, nz = -dz / length, dy / length  # unit perpendicular
    if nz < 0:
        # Flip so +offset always means "toward +z" - otherwise the far
        # end's "+offset" corner can land on the opposite (lower) side from
        # the near end's fixed +half_thick corner, and connecting them in
        # order self-intersects into a bowtie instead of a simple quad.
        ny, nz = -ny, -nz
    corners = [
        (y0, z0 + half_thick),
        (y1 + ny * half_thick, z1 + nz * half_thick),
        (y1 - ny * half_thick, z1 - nz * half_thick),
        (y0, z0 - half_thick),
    ]
    pts = [sketch.modelToSketchSpace(adsk.core.Point3D.create(0.0, y, z)) for (y, z) in corners]
    lines = sketch.sketchCurves.sketchLines
    for i in range(4):
        lines.addByTwoPoints(pts[i], pts[(i + 1) % 4])


@register
class LoopHandleScoop(Generator):
    id = "scoop_loop_handle"
    display_name = "Loop-Handle Scoop (Square)"
    category = "Scoops"
    parameters = [
        ParamSpec(name="body_width", label="Body Width", type="float",
                  default=55.0, min=25.0, max=120.0, unit="mm"),
        ParamSpec(name="body_depth", label="Body Depth (front lip to floor)",
                  type="float", default=70.0, min=25.0, max=180.0, unit="mm"),
        ParamSpec(name="mouth_angle", label="Mouth Angle (deg)", type="float",
                  default=35.0, min=10.0, max=50.0),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=2.4, min=1.4, max=6.0, unit="mm"),
        ParamSpec(name="base_thickness", label="Base Thickness", type="float",
                  default=4.0, min=1.6, max=15.0, unit="mm"),
        ParamSpec(name="corner_radius", label="Body Corner Radius", type="float",
                  default=6.0, min=0.0, max=20.0, unit="mm"),
        ParamSpec(name="handle_style", label="Handle Style", type="choice",
                  default="Square Bracket", choices=["Square Bracket", "Arched Loop"]),
        ParamSpec(name="handle_diameter", label="Handle Thickness", type="float",
                  default=9.0, min=4.0, max=20.0, unit="mm"),
        ParamSpec(name="handle_reach", label="Handle Reach (grip clearance)",
                  type="float", default=32.0, min=12.0, max=80.0, unit="mm"),
        ParamSpec(name="handle_top_offset", label="Handle Top Attach (below rim)",
                  type="float", default=10.0, min=5.0, max=80.0, unit="mm"),
        ParamSpec(name="handle_bottom_offset", label="Handle Bottom Attach (above base, 0 = flush with bed)",
                  type="float", default=0.0, min=0.0, max=40.0, unit="mm"),
        ParamSpec(name="handle_top_angle", label="Handle Top Angle (Square Bracket, deg from vertical)",
                  type="float", default=45.0, min=15.0, max=75.0),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        half_w = mm(params["body_width"]) / 2.0
        body_depth = mm(params["body_depth"])
        angle = params["mouth_angle"]
        wall = mm(params["wall_thickness"])
        base = mm(params["base_thickness"])
        corner_r = mm(params["corner_radius"])
        handle_r = mm(params["handle_diameter"]) / 2.0
        handle_reach = mm(params["handle_reach"])
        top_offset = mm(params["handle_top_offset"])
        bottom_offset = mm(params["handle_bottom_offset"])

        if wall >= half_w * 0.85:
            raise ValueError("Wall thickness must be less than half the body width.")
        if corner_r >= half_w:
            raise ValueError("Corner radius must be less than half the body width.")

        inner_half_w = half_w - wall

        # front_lip_z is the low point of the mouth ("Bowl Depth" measured
        # from there); pivot_z is where the cut plane crosses the box's own
        # axis, offset so the plane meets the right heights at the front
        # (-Y, low/short) and back (+Y, tall) faces.
        floor_z = base
        front_lip_z = floor_z + body_depth
        pivot_z = front_lip_z + half_w * math.tan(math.radians(angle))
        back_lip_z = pivot_z + half_w * math.tan(math.radians(angle))
        top_z = back_lip_z + mm(1.0)

        body = geometry_utils.build_polygon_shell(
            component, 4,
            outer_bottom_r=half_w, outer_top_r=half_w,
            inner_floor_r=inner_half_w, inner_top_r=inner_half_w,
            height_cm=top_z, base_cm=floor_z,
            outer_corner_r=corner_r,
            inner_corner_r=max(corner_r - wall, 0.0),
        )

        # --- angled mouth cut (tilts about X: front = -Y low, back = +Y tall)
        cut_plane = geometry_utils.angled_plane_through_x(component, pivot_z, angle)
        reach = top_z + half_w * 2.0
        pivot_point = adsk.core.Point3D.create(0, 0, pivot_z)
        geometry_utils.cut_half_space(component, cut_plane, reach, [body],
                                       on_plane_point=pivot_point)

        # --- handle on the FRONT wall (-Y, the SHORT side of the mouth) -
        # the tall back wall then extends away from your hand as a deep
        # backstop, maximizing how much a single scoop can hold.
        handle_top_z = min(front_lip_z - top_offset, front_lip_z - mm(4.0))
        # Anchored from the object's true base (z=0, the surface that sits on
        # the print bed) rather than the interior cavity floor - centering the
        # bottom leg/tube at (handle_r + bottom_offset) puts its lowest edge
        # at exactly z=bottom_offset, so the default (0) sits flush with the
        # bed with nothing floating underneath it and needing support.
        handle_bottom_z = handle_r + bottom_offset
        if handle_top_z <= handle_bottom_z + handle_r * 2.0:
            raise ValueError("Handle attachment points are too close together - "
                             "reduce the top/bottom offsets, increase the mouth "
                             "angle, or deepen the body.")
        attach_span = handle_top_z - handle_bottom_z
        # 1.1x let a genuinely self-intersecting case (ASM_SELF_INTER, a raw
        # Fusion API crash rather than this guard) through on a small body -
        # confirmed live that case fails at this ratio regardless of the
        # stub fix below, so the margin itself was too loose, not something
        # the stub broke. 0.9x was checked against that failing case (now
        # correctly rejected) and the default-sized body (still comfortably
        # allowed).
        if params["handle_style"] == "Arched Loop" and handle_reach > attach_span * 0.9:
            raise ValueError(
                "Handle reach is too large relative to its attachment span "
                f"({attach_span * 10:.0f}mm) - the loop would be too flat "
                "for a clean turn at the tip. Reduce Handle Reach, or "
                "increase the top/bottom attach offsets or body depth.")

        # The attachment's near EDGE sits just inside the outer wall surface
        # (by `overlap`, well under the wall thickness) so the handle's own
        # thickness - extending outward from there - can never reach the
        # inner wall surface and poke into the hollow interior, no matter
        # how thick the handle is relative to the wall.
        overlap = min(mm(1.5), wall * 0.6)
        near_depth = half_w - overlap  # magnitude; front wall is at y = -half_w

        if params["handle_style"] == "Square Bracket":
            self._build_square_bracket(component, body, near_depth,
                                        handle_top_z, handle_bottom_z,
                                        handle_reach, handle_r,
                                        params["handle_top_angle"])
        else:
            self._build_arched_loop(component, body, near_depth,
                                     handle_top_z, handle_bottom_z,
                                     handle_reach, handle_r)

    def _build_square_bracket(self, component, body, near_depth, z_top, z_bottom,
                               reach, bar, top_angle_deg):
        """A "flag" bracket: horizontal bottom leg (finger rest) plus a
        DIAGONAL top brace instead of a flat horizontal top leg. A flat top
        leg is a horizontal shelf cantilevered off the wall - the textbook
        unsupported overhang. Angling it, like the diagonal brace on a real
        wall shelf bracket, keeps every surface within the self-supporting
        overhang angle (measured here from vertical, so smaller = steeper
        = safer) instead of printing a sudden full-width horizontal shelf.
        """
        near_y = -near_depth
        far_y = -(near_depth + reach)

        # Drop the diagonal's outer end low enough for this angle; never
        # let it collide with the bottom leg - keep a minimum finger gap.
        rise = reach / max(math.tan(math.radians(top_angle_deg)), 1e-6)
        min_gap = max(bar * 1.2, geometry_utils.mm(6.0))  # finger clearance
        diag_far_z = z_top - rise
        if diag_far_z < z_bottom + bar * 2.0 + min_gap:
            raise ValueError(
                "Handle Top Angle is too steep for this attach span - the "
                "diagonal brace would collide with the bottom leg. Use a "
                "larger angle, or increase the top/bottom attach offsets.")

        sketch = geometry_utils.sketch_on_yz_at_x(component, 0.0)
        _draw_rect(sketch, near_y, far_y, z_bottom - bar, z_bottom + bar)  # bottom leg
        _draw_diagonal_bar(sketch, near_y, z_top, far_y, diag_far_z, bar)  # angled top brace
        _draw_rect(sketch, far_y, far_y + math.copysign(2.0 * bar, near_y - far_y),
                   z_bottom - bar, diag_far_z + bar)  # crossbar joining them

        profiles = geometry_utils.collect(
            [sketch.profiles.item(i) for i in range(sketch.profiles.count)])
        bodies = geometry_utils.extrude_symmetric_all(component, profiles, bar * 2.0)
        geometry_utils.combine_join(component, body, bodies)

    def _build_arched_loop(self, component, body, near_depth, z_top, z_bottom,
                            reach, handle_r):
        """A short straight stub at each wall attachment, then a single
        smooth spline out to a bulge and back to the other stub. A tube's
        wall/body intersection is only a clean round hole if the tube meets
        the wall PERPENDICULARLY - a tube arriving at an angle intersects a
        flat wall in a tilted ellipse, which can't be made flush by sliding
        the whole centerline back and forth: one side of the ellipse still
        pokes into the interior while the opposite side gaps away from the
        wall outside, and the tilted end cap itself shows as a visible seam
        (all three symptoms an angled centerline-only attachment produced
        here). Forcing each stub to run straight in -Y (perpendicular to the
        wall) for a short run guarantees a clean perpendicular entry: the
        stub's own cross-section is confined to a constant-Y plane for its
        whole length, so its near (wall-facing) end can sit exactly at the
        near-EDGE depth `near_depth` (the same quantity the Square Bracket's
        bars start from) with no risk of the tube's radius reaching back past
        it - unlike the tube's centerline itself, which can't be trusted to
        predict the swept surface's true extent once it starts curving. The
        fitted spline only needs to connect the stubs' OUTER ends through the
        tip; it's still tangent-continuous into each stub (no sharp corner
        for the swept tube to fail on) since a smooth curve into a straight
        run doesn't introduce a real kink the way two arcs meeting head-on
        would.
        """
        wall_y = -near_depth
        stub = max(handle_r * 1.5, geometry_utils.mm(5.0))
        mid_z = (z_top + z_bottom) / 2.0

        top_attach = adsk.core.Point3D.create(0.0, wall_y, z_top)
        top_stub_end = adsk.core.Point3D.create(0.0, wall_y - stub, z_top)
        bottom_attach = adsk.core.Point3D.create(0.0, wall_y, z_bottom)
        bottom_stub_end = adsk.core.Point3D.create(0.0, wall_y - stub, z_bottom)
        tip = adsk.core.Point3D.create(0.0, wall_y - reach, mid_z)

        path_sketch = geometry_utils.sketch_on_yz_at_x(component, 0.0)
        p_top_attach = path_sketch.modelToSketchSpace(top_attach)
        p_top_stub = path_sketch.modelToSketchSpace(top_stub_end)
        p_bottom_stub = path_sketch.modelToSketchSpace(bottom_stub_end)
        p_bottom_attach = path_sketch.modelToSketchSpace(bottom_attach)
        p_tip = path_sketch.modelToSketchSpace(tip)

        lines = path_sketch.sketchCurves.sketchLines
        line_top = lines.addByTwoPoints(p_top_attach, p_top_stub)
        spline_points = adsk.core.ObjectCollection.create()
        for p in (p_top_stub, p_tip, p_bottom_stub):
            spline_points.add(p)
        spline = path_sketch.sketchCurves.sketchFittedSplines.add(spline_points)
        line_bottom = lines.addByTwoPoints(p_bottom_stub, p_bottom_attach)

        # A fitted spline's own tangent at its start/end points isn't
        # forced to match a curve it happens to share an endpoint with -
        # confirmed live, the stub-to-spline junction showed a visible sharp
        # kink (a real tangent discontinuity, not just a render artifact).
        # Explicit tangent constraints force G1 continuity across both
        # joints, so the swept tube bends smoothly out of each straight stub
        # instead of creasing.
        path_sketch.geometricConstraints.addTangent(line_top, spline)
        path_sketch.geometricConstraints.addTangent(line_bottom, spline)

        # isChain=True on a single curve only followed the chain ONE curve
        # deep (confirmed live: path.count came back 2, not 3, silently
        # dropping the bottom stub) rather than walking the full connected
        # run - so the swept tube stopped short of the wall at the bottom
        # attachment, a visible gap. Passing all three curves explicitly
        # sidesteps that chain-detection limit entirely.
        path_curves = adsk.core.ObjectCollection.create()
        for c in (line_top, spline, line_bottom):
            path_curves.add(c)
        path = component.features.createPath(path_curves, False)

        # Profile plane normal to Y (the wall's own normal direction), so it
        # starts perpendicular to the path at the wall attachment, where the
        # path is now a straight run in -Y by construction (exactly
        # perpendicular), not just approximately so.
        xz_offset_input = component.constructionPlanes.createInput()
        xz_offset_input.setByOffset(
            component.xZConstructionPlane, adsk.core.ValueInput.createByReal(wall_y))
        profile_plane = component.constructionPlanes.add(xz_offset_input)

        profile_sketch = component.sketches.add(profile_plane)
        circle_center = profile_sketch.modelToSketchSpace(top_attach)
        geometry_utils.draw_circle(profile_sketch, handle_r, circle_center)

        sweeps = component.features.sweepFeatures
        sweep_input = sweeps.createInput(
            profile_sketch.profiles.item(0), path,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        feature = sweeps.add(sweep_input)
        handle_bodies = [feature.bodies.item(i) for i in range(feature.bodies.count)]
        geometry_utils.combine_join(component, body, handle_bodies)
