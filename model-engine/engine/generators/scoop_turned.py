"""Turned-handle scoop: a hollow cylindrical bowl with an angled scoop
mouth, on a lathe-turned handle - the classic flour/coffee scoop shape.

Built as ONE closed revolve profile (same trick as the planters): starting
on the axis at the handle tip, the outline runs up through the turned
handle, up a short neck, up the bowl's outer wall, across the open rim,
back down the inner wall to the cavity floor, and closes back to the axis.
Revolving that single profile produces the whole solid - hollow bowl and
solid handle - in one feature. The angled mouth is then sliced with a
tilted construction plane (geometry_utils.angled_plane_through_x) and a
one-sided cut, exactly like slicing a tube with a knife.
"""

import math

import adsk.core

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..registry import register

# --- turned-profile building blocks -----------------------------------------
# Each appends (r, z) points to `pts` and returns the new current z.
#
# This whole profile is printed standing on the handle tip (z=0) with the
# revolve axis vertical, so any region where radius INCREASES as z increases
# is a horizontal-ish overhang (flaring outward going up) - the local slope
# angle from vertical is arctan(dr/dz), and FDM needs support past ~45deg.
# Every helper below that can flare outward auto-extends its own `length`
# (or the equivalent height parameter) so its steepest point never exceeds
# MAX_OVERHANG_DEG, regardless of what radii the caller passes in - this
# fixes the flaring shape structurally rather than relying on every caller
# (or every future handle style) to pick a large-enough length by hand. A
# narrowing segment (radius decreasing going up) is always self-supporting
# and is left alone.

MAX_OVERHANG_DEG = 45.0
_MAX_OVERHANG_TAN = math.tan(math.radians(MAX_OVERHANG_DEG))


def _hemisphere_tip(pts, z0, radius, n=10):
    """Rounded tip starting ON the axis (r=0) and flaring out to `radius`
    at its equator - the rounded bottom of a knob/ball end. Its steepest
    point is fixed at the pole (z0), where dr/dz = pi/2 (~57.5deg from
    vertical) no matter how big or small `radius` is - a real hemisphere's
    tangent at its pole is horizontal. Unlike the other helpers this can't
    be fixed by lengthening it (stretching would make it an ellipsoid, not
    a hemisphere), and in practice slicers print small rounded tips like
    this fine without support since each layer's overhang area near a point
    is tiny - left as-is rather than distorting the shape for a marginal,
    small-scale gain."""
    for i in range(1, n + 1):
        t = i / n
        z = z0 + radius * t
        r = radius * math.sin(t * math.pi / 2.0)
        pts.append((r, z))
    return z0 + radius


def _cone_tip(pts, z0, radius, length, n=6):
    """Slender pointed tip starting ON the axis - a straight cone."""
    length = max(length, radius / _MAX_OVERHANG_TAN)
    for i in range(1, n + 1):
        t = i / n
        pts.append((radius * t, z0 + length * t))
    return z0 + length


def _taper(pts, z0, r_end, length):
    """Straight segment from the current radius to r_end."""
    r0 = pts[-1][0]
    if r_end > r0:
        length = max(length, (r_end - r0) / _MAX_OVERHANG_TAN)
    pts.append((r_end, z0 + length))
    return z0 + length


def _bead(pts, z0, r_base, r_bulge, length, n=14):
    """Convex outward bulge (a decorative ring), base radius to base radius,
    peaking at r_bulge in the middle. The rising half's steepest point is at
    its own start (t=0), where dr/dz = pi*(r_bulge-r_base)/length."""
    if r_bulge > r_base:
        length = max(length, math.pi * (r_bulge - r_base) / _MAX_OVERHANG_TAN)
    for i in range(1, n + 1):
        t = i / n
        r = r_base + (r_bulge - r_base) * math.sin(t * math.pi)
        pts.append((r, z0 + length * t))
    return z0 + length


def _cove(pts, z0, r_base, r_dip, length, n=14):
    """Concave inward groove - the mirror of a bead."""
    for i in range(1, n + 1):
        t = i / n
        r = r_base - (r_base - r_dip) * math.sin(t * math.pi)
        pts.append((r, z0 + length * t))
    return z0 + length


def _cylinder(pts, z0, radius, length):
    pts.append((radius, z0 + length))
    return z0 + length


# --- handle styles -----------------------------------------------------------
# Each takes (pts, handle_length, max_r, top_r), fills in the handle
# silhouette from z=0 (tip, on-axis) up toward z=handle_length at radius
# top_r where the neck will continue, and RETURNS the actual final z - which
# may run past handle_length, since the helpers above are free to auto-
# extend a segment to stay within MAX_OVERHANG_DEG. The caller must use this
# returned z (not the nominal handle_length) to place the neck, or an
# extended handle can overrun into where the neck/bowl were about to start,
# producing a non-monotonic (self-intersecting) profile. Fractions of
# handle_length are tuned by eye. Absolute mm-scale features (hemisphere/
# cylinder sizes given as a fraction of max_r rather than length) are capped
# to a fraction of length too, so a fat-but-short handle can't blow its own
# budget before the style even gets to its final taper.

def _style_classic_baluster(pts, length, max_r, top_r):
    """Rounded tip, thin waist, one long smooth taper up to a collar bead
    right below the neck - matches the reference scoops' handles."""
    tip_r = min(max_r * 0.42, length * 0.12)
    z = _hemisphere_tip(pts, 0.0, tip_r)
    z = _taper(pts, z, max_r * 0.30, length * 0.08)
    z = _taper(pts, z, max_r * 0.62, length * 0.62)
    z = _bead(pts, z, max_r * 0.62, top_r * 1.02, length * 0.14)
    return _taper(pts, z, top_r, max(length - z, length * 0.02))


def _style_multi_bead(pts, length, max_r, top_r):
    """Three well-spaced beads separated by plain cylinder sections, so
    each ring reads as distinct rather than blurring into a screw thread."""
    z = _cone_tip(pts, 0.0, max_r * 0.30, length * 0.10)
    z = _cylinder(pts, z, max_r * 0.30, length * 0.06)
    for i in range(3):
        z = _bead(pts, z, max_r * 0.34, max_r * (0.68 + 0.10 * i), length * 0.10)
        z = _cylinder(pts, z, max_r * 0.34, length * 0.11)
    return _taper(pts, z, top_r, max(length - z, length * 0.02))


def _style_simple_taper(pts, length, max_r, top_r):
    tip_r = min(max_r * 0.55, length * 0.30)
    z = _hemisphere_tip(pts, 0.0, tip_r)
    return _taper(pts, z, top_r, max(length - z, length * 0.02))


def _style_stubby_knob(pts, length, max_r, top_r):
    tip_r = min(max_r, length * 0.30)
    z = _hemisphere_tip(pts, 0.0, tip_r)
    z = _cylinder(pts, z, tip_r, length * 0.55)
    z = _bead(pts, z, tip_r, tip_r * 1.08, length * 0.14)
    return _taper(pts, z, top_r, max(length - z, length * 0.02))


HANDLE_STYLES = {
    "Classic Baluster": _style_classic_baluster,
    "Multi-Bead Spindle": _style_multi_bead,
    "Simple Taper": _style_simple_taper,
    "Stubby Knob": _style_stubby_knob,
}


@register
class TurnedHandleScoop(Generator):
    id = "scoop_turned"
    display_name = "Turned-Handle Scoop"
    category = "Scoops"
    parameters = [
        ParamSpec(name="bowl_diameter", label="Bowl Diameter", type="float",
                  default=55.0, min=25.0, max=120.0, unit="mm"),
        ParamSpec(name="bowl_depth", label="Bowl Depth (front lip to floor)",
                  type="float", default=65.0, min=25.0, max=180.0, unit="mm"),
        ParamSpec(name="mouth_angle", label="Mouth Angle (deg)", type="float",
                  default=38.0, min=15.0, max=55.0),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=2.4, min=1.4, max=6.0, unit="mm"),
        ParamSpec(name="base_thickness", label="Base Thickness (below cavity)",
                  type="float", default=5.0, min=2.0, max=20.0, unit="mm"),
        ParamSpec(name="bottom_style", label="Bowl Bottom", type="choice",
                  default="Rounded", choices=["Rounded", "Flat"]),
        ParamSpec(name="handle_style", label="Handle Style", type="choice",
                  default="Classic Baluster", choices=list(HANDLE_STYLES.keys())),
        ParamSpec(name="handle_length", label="Handle Length", type="float",
                  default=110.0, min=40.0, max=250.0, unit="mm"),
        ParamSpec(name="handle_diameter", label="Handle Max Diameter", type="float",
                  default=22.0, min=10.0, max=45.0, unit="mm"),
        ParamSpec(name="neck_length", label="Neck Length (minimum)", type="float",
                  default=14.0, min=4.0, max=50.0, unit="mm"),
        ParamSpec(name="neck_angle", label="Neck Taper Angle (deg from vertical)",
                  type="float", default=45.0, min=25.0, max=70.0),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        bowl_r = mm(params["bowl_diameter"]) / 2.0
        bowl_depth = mm(params["bowl_depth"])
        angle = params["mouth_angle"]
        wall = mm(params["wall_thickness"])
        base_thickness = mm(params["base_thickness"])
        handle_len = mm(params["handle_length"])
        handle_r = mm(params["handle_diameter"]) / 2.0
        neck_len_min = mm(params["neck_length"])
        neck_angle = params["neck_angle"]

        if wall >= bowl_r * 0.85:
            raise ValueError("Wall thickness must be less than the bowl radius.")
        if handle_r >= bowl_r:
            raise ValueError("Handle diameter must be smaller than the bowl diameter.")

        inner_r = bowl_r - wall

        # --- handle + neck silhouette, from the axis at the tip up to the
        # bowl's outer wall ---------------------------------------------------
        pts = [(0.0, 0.0)]
        # The style functions can auto-extend a decorative feature (bead,
        # taper, etc) to keep its own overhang under 45deg, so the handle's
        # ACTUAL final height can run past the nominal handle_len - using
        # handle_len directly to place the neck would then produce a
        # non-monotonic (self-intersecting) profile if the handle silhouette
        # ran past where the neck was about to start.
        handle_top_z = HANDLE_STYLES[params["handle_style"]](pts, handle_len, handle_r, handle_r)
        if handle_top_z > handle_len * 1.4:
            raise ValueError(
                "This handle style needs more room for its decorative detail "
                f"than Handle Length allows ({params['handle_length']:.0f}mm "
                f"requested, ~{handle_top_z * 10:.0f}mm needed to keep every "
                "bead/taper printable without support) - increase Handle "
                "Length, reduce Handle Max Diameter, or choose a different "
                "Handle Style.")
        # The neck is a straight cone from the handle's top radius out to
        # the full bowl radius - a flare that can be a steep, unsupported
        # overhang if the bowl is much wider than the handle and the neck is
        # short (confirmed: the *default* parameters alone put this past
        # 45deg). Auto-extend neck_length (never shrink it) so the neck's
        # own slope never exceeds neck_angle, regardless of how large the
        # bowl/handle radius gap is.
        radius_gap = bowl_r - handle_r
        neck_len = max(neck_len_min, radius_gap / math.tan(math.radians(neck_angle)))
        neck_top_z = handle_top_z + neck_len
        pts.append((bowl_r, neck_top_z))

        # --- bowl: floor sits base_thickness above the neck/handle junction,
        # so the cavity (including a rounded dome) can never dig into the
        # solid handle material below it. bowl_depth (capacity) is then
        # measured from the FRONT lip (the low point of the angled mouth)
        # down to that floor, matching how a real scoop's capacity reads.
        floor_z = neck_top_z + base_thickness
        front_lip_z = floor_z + bowl_depth
        pivot_z = front_lip_z + bowl_r * math.tan(math.radians(angle))
        back_lip_z = pivot_z + bowl_r * math.tan(math.radians(angle))
        top_z = back_lip_z + mm(1.0)  # tiny safety margin, the cut defines the real edge

        pts.append((bowl_r, top_z))       # outer wall, straight up to the top
        pts.append((inner_r, top_z))      # rim: inward across the open top
        pts.append((inner_r, floor_z))    # inner wall, straight down

        if params["bottom_style"] == "Rounded":
            # Clamped to base_thickness (with a safety margin) so the dome
            # can never dip into the solid neck material below the floor.
            dome_r = min(inner_r, bowl_depth * 0.8, base_thickness * 0.85)
            n = 10
            for i in range(1, n + 1):
                t = i / n
                r = inner_r * math.cos(t * math.pi / 2.0)
                z = floor_z - dome_r * math.sin(t * math.pi / 2.0)
                pts.append((r, z))
        else:
            pts.append((0.0, floor_z))

        sketch = geometry_utils.sketch_on_xz(component)
        geometry_utils.draw_closed_profile_rz(sketch, pts)
        body = geometry_utils.revolve_profile(component, sketch.profiles.item(0))

        # --- angled mouth cut --------------------------------------------------
        cut_plane = geometry_utils.angled_plane_through_x(component, pivot_z, angle)
        reach = top_z + bowl_r * 2.0
        pivot_point = adsk.core.Point3D.create(0, 0, pivot_z)
        geometry_utils.cut_half_space(component, cut_plane, reach, [body],
                                       on_plane_point=pivot_point)
