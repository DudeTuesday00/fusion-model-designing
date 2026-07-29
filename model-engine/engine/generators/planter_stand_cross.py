"""Two-piece cross plant stand (slot-together, prints flat, no supports).

Two flat H-shaped plates with half-lap notches in their crossbars - one
notched from the top edge, one from the bottom - slide together into a
perpendicular X. The pot rests on the crossed bars; the four lower legs
are the feet; the four upper arms fence the pot in.

Enter the pot's bottom diameter and the arm spacing sizes itself. The slot
width comes from the plate thickness plus the fit clearance, so the joint
fits regardless of the sizes you pick.
"""

import adsk.core
import adsk.fusion

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..registry import register


def _draw_h_plate(component, params_cm, notch_on_top, x_offset):
    """Draws one H plate outline (with its slot notch) and returns the body.

    2D layout (the piece lies flat): side bars run along Y (legs down, arms
    up), the crossbar joins them at y=0. Values in cm.
    """
    (span, beam, leg_len, arm_len, notch_w, thickness, fillet_r) = params_cm
    b2 = beam / 2.0
    inner = span / 2.0 - b2   # inner face of the side bars
    outer = span / 2.0 + b2

    # Outline path, counterclockwise. Notch points get spliced into the
    # crossbar edge it belongs to.
    top_edge = [(inner, b2)]
    if notch_on_top:
        top_edge += [(notch_w / 2.0, b2), (notch_w / 2.0, 0.0),
                     (-notch_w / 2.0, 0.0), (-notch_w / 2.0, b2)]
    top_edge += [(-inner, b2)]

    bottom_edge = [(-inner, -b2)]
    if not notch_on_top:
        bottom_edge += [(-notch_w / 2.0, -b2), (-notch_w / 2.0, 0.0),
                        (notch_w / 2.0, 0.0), (notch_w / 2.0, -b2)]
    bottom_edge += [(inner, -b2)]

    points = ([(-outer, -leg_len), (-inner, -leg_len), (-inner, -b2)]
              + bottom_edge
              + [(inner, -leg_len), (outer, -leg_len), (outer, arm_len),
                 (inner, arm_len), (inner, b2)]
              + top_edge
              + [(-inner, arm_len), (-outer, arm_len)])
    # Note: bottom_edge starts at (-inner,-b2) which duplicates the point
    # before it; drop consecutive duplicates.
    cleaned = [points[0]]
    for pt in points[1:]:
        if abs(pt[0] - cleaned[-1][0]) > 1e-9 or abs(pt[1] - cleaned[-1][1]) > 1e-9:
            cleaned.append(pt)

    sketch = geometry_utils.sketch_on_xy(component)
    sk_pts = [sketch.modelToSketchSpace(
        adsk.core.Point3D.create(x + x_offset, y, 0)) for (x, y) in cleaned]
    lines = sketch.sketchCurves.sketchLines
    segments = []
    for i in range(len(sk_pts)):
        segments.append(lines.addByTwoPoints(sk_pts[i], sk_pts[(i + 1) % len(sk_pts)]))

    # Fillet the four inner corners where the legs meet the crossbar - the
    # corner points are exactly (+-inner, +-b2).
    if fillet_r > 1e-6:
        arcs = sketch.sketchCurves.sketchArcs
        for i, (x, y) in enumerate(cleaned):
            if abs(abs(x) - inner) < 1e-9 and abs(abs(y) - b2) < 1e-9:
                prev_line = segments[i - 1]
                next_line = segments[i]
                try:
                    arcs.addFillet(prev_line, sk_pts[i], next_line, sk_pts[i], fillet_r)
                except Exception:
                    pass  # cosmetic - skip a corner rather than fail the build

    return geometry_utils.extrude_profile(component, sketch.profiles.item(0), thickness)


@register
class CrossPlantStand(Generator):
    id = "planter_stand_cross"
    display_name = "Plant Stand (2-Piece Cross)"
    category = "Planter"
    parameters = [
        ParamSpec(name="pot_bottom_diameter", label="Pot Bottom Diameter", type="float",
                  default=100.0, min=40.0, max=400.0, unit="mm"),
        ParamSpec(name="clearance", label="Clearance Around Pot", type="float",
                  default=4.0, min=1.0, max=20.0, unit="mm"),
        ParamSpec(name="beam_width", label="Beam Width", type="float",
                  default=16.0, min=8.0, max=40.0, unit="mm"),
        ParamSpec(name="plate_thickness", label="Plate Thickness", type="float",
                  default=11.0, min=6.0, max=25.0, unit="mm"),
        ParamSpec(name="leg_height", label="Leg Height (below pot)", type="float",
                  default=60.0, min=20.0, max=200.0, unit="mm"),
        ParamSpec(name="arm_height", label="Arm Height (above crossbar)", type="float",
                  default=45.0, min=0.0, max=150.0, unit="mm"),
        ParamSpec(name="slot_clearance", label="Slot Fit Clearance", type="float",
                  default=0.3, min=0.1, max=1.0, unit="mm"),
        ParamSpec(name="corner_fillet", label="Corner Fillet", type="float",
                  default=6.0, min=0.0, max=15.0, unit="mm"),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        pot_r = mm(params["pot_bottom_diameter"]) / 2.0
        clearance = mm(params["clearance"])
        beam = mm(params["beam_width"])
        thickness = mm(params["plate_thickness"])
        leg_len = mm(params["leg_height"])
        arm_len = mm(params["arm_height"])
        notch_w = thickness + mm(params["slot_clearance"])
        fillet_r = mm(params["corner_fillet"])

        # Side bars spaced so their inner faces sit clearance off the pot.
        span = 2.0 * pot_r + 2.0 * clearance + beam

        if notch_w >= (span - beam) * 0.5:
            raise ValueError("Plate is too thick relative to the stand size.")
        if arm_len > 0 and arm_len < beam:
            raise ValueError("Arm height should be 0 (no arms) or taller than the beam width.")
        if fillet_r >= beam:
            raise ValueError("Corner fillet must be smaller than the beam width.")

        plate_params = (span, beam, leg_len, arm_len, notch_w, thickness, fillet_r)
        _draw_h_plate(component, plate_params, notch_on_top=True, x_offset=0.0)
        _draw_h_plate(component, plate_params, notch_on_top=False,
                       x_offset=span + beam + mm(15.0))
