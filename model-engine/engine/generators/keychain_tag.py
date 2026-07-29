"""Motel-style keychain tag with custom text, symbols, and end stripes.

The blank is the classic elongated-hexagon fob (like the user's Keychain 001
blank): rounded corners, ring hole at the left tip, decorative grooves at
the right end. On top of it:

- Text: real font rendering via Fusion's SketchText - any font installed on
  Windows, any phrase, Raised or Engraved.
- Symbols: symbols ARE text - Windows symbol fonts carry hearts, stars,
  moons, anchors, the zodiac and more. Pick a preset or choose Custom and
  paste any character (Win+. opens the emoji/symbol picker) into Symbol
  Text. Zodiac glyphs: type one of these into Symbol Text with Custom:
  Aries-Pisces are U+2648..U+2653.
"""

import adsk.core
import adsk.fusion

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..registry import register

SYMBOL_PRESETS = {
    "None": "",
    "Heart": "♥",
    "Star": "★",
    "Moon": "☽",
    "Sun": "☀",
    "Music": "♫",
    "Peace": "☮",
    "Yin-Yang": "☯",
    "Anchor": "⚓",
    "Snowflake": "❄",
    "Custom (use Symbol Text)": None,
}


@register
class KeychainTag(Generator):
    id = "keychain_tag"
    display_name = "Motel Tag Keychain"
    category = "Keychains"
    parameters = [
        ParamSpec(name="text", label="Text", type="string", default="AQUARIUS"),
        ParamSpec(name="text_height", label="Text Size", type="float",
                  default=10.0, min=4.0, max=25.0, unit="mm"),
        ParamSpec(name="font", label="Font", type="string", default="Arial"),
        ParamSpec(name="text_bold", label="Bold Text", type="bool", default=True),
        ParamSpec(name="symbol", label="Symbol", type="choice", default="None",
                  choices=list(SYMBOL_PRESETS.keys())),
        ParamSpec(name="symbol_text", label="Symbol Text (Custom)", type="string",
                  default=""),
        ParamSpec(name="symbol_size", label="Symbol Size", type="float",
                  default=14.0, min=6.0, max=30.0, unit="mm"),
        ParamSpec(name="relief", label="Relief", type="choice", default="Raised",
                  choices=["Raised", "Engraved"]),
        ParamSpec(name="relief_depth", label="Relief Depth", type="float",
                  default=0.8, min=0.3, max=2.0, unit="mm"),
        ParamSpec(name="length", label="Tag Length", type="float",
                  default=88.0, min=50.0, max=150.0, unit="mm"),
        ParamSpec(name="width", label="Tag Width", type="float",
                  default=44.0, min=25.0, max=80.0, unit="mm"),
        ParamSpec(name="thickness", label="Thickness", type="float",
                  default=3.0, min=2.0, max=6.0, unit="mm"),
        ParamSpec(name="hole_diameter", label="Ring Hole Diameter", type="float",
                  default=5.5, min=3.0, max=10.0, unit="mm"),
        ParamSpec(name="stripe_count", label="End Stripes (0 = none)", type="int",
                  default=5, min=0, max=8),
    ]

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        length = mm(params["length"])
        width = mm(params["width"])
        t = mm(params["thickness"])
        hole_r = mm(params["hole_diameter"]) / 2.0
        depth = mm(params["relief_depth"])
        raised = params["relief"] == "Raised"

        # --- blank: elongated hexagon with rounded corners -----------------
        x_flat = length * 0.15   # where the full width begins
        half_w = width / 2.0
        corners = [
            (-length / 2.0, 0.0), (-x_flat, -half_w), (x_flat, -half_w),
            (length / 2.0, 0.0), (x_flat, half_w), (-x_flat, half_w),
        ]
        sketch = geometry_utils.sketch_on_xy(component)
        pts = [sketch.modelToSketchSpace(adsk.core.Point3D.create(x, y, 0))
               for (x, y) in corners]
        lines = sketch.sketchCurves.sketchLines
        segments = [lines.addByTwoPoints(pts[i], pts[(i + 1) % 6]) for i in range(6)]
        arcs = sketch.sketchCurves.sketchArcs
        for i in range(6):
            radius = mm(7.0) if abs(corners[i][1]) < 1e-9 else mm(9.0)
            try:
                arcs.addFillet(segments[i - 1], pts[i], segments[i], pts[i], radius)
            except Exception:
                pass
        tag_body = geometry_utils.extrude_profile(component, sketch.profiles.item(0), t)

        # Soften the top perimeter like a molded fob.
        top_edges = geometry_utils.edges_at_height(tag_body, t)
        if top_edges:
            geometry_utils.fillet_edges(component, top_edges, mm(0.8))

        extrudes = component.features.extrudeFeatures

        def cut_from_top(profiles, cut_depth):
            cut_input = extrudes.createInput(
                geometry_utils.collect(profiles),
                adsk.fusion.FeatureOperations.CutFeatureOperation)
            cut_input.startExtent = adsk.fusion.OffsetStartDefinition.create(
                adsk.core.ValueInput.createByReal(t - cut_depth))
            cut_input.setOneSideExtent(
                adsk.fusion.DistanceExtentDefinition.create(
                    adsk.core.ValueInput.createByReal(cut_depth + mm(2.0))),
                adsk.fusion.ExtentDirections.PositiveExtentDirection)
            cut_input.participantBodies = [tag_body]
            extrudes.add(cut_input)

        def raise_from_top(profiles, raise_height):
            new_input = extrudes.createInput(
                geometry_utils.collect(profiles),
                adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            new_input.setOneSideExtent(
                adsk.fusion.DistanceExtentDefinition.create(
                    adsk.core.ValueInput.createByReal(t + raise_height)),
                adsk.fusion.ExtentDirections.PositiveExtentDirection)
            feature = extrudes.add(new_input)
            bodies = [feature.bodies.item(i) for i in range(feature.bodies.count)]
            geometry_utils.combine_join(component, tag_body, bodies)

        # --- ring hole with a raised collar at the left tip ------------------
        hole_x = -length / 2.0 + hole_r + mm(4.5)
        collar_sketch = geometry_utils.sketch_on_xy(component)
        center = adsk.core.Point3D.create(hole_x, 0, 0)
        geometry_utils.draw_circle(collar_sketch, hole_r + mm(2.2), center)
        geometry_utils.draw_circle(collar_sketch, hole_r + mm(0.6), center)
        collar_profiles = [collar_sketch.profiles.item(i)
                           for i in range(collar_sketch.profiles.count)
                           if collar_sketch.profiles.item(i).profileLoops.count == 2]
        raise_from_top(collar_profiles, mm(0.6))

        hole_sketch = geometry_utils.sketch_on_xy(component)
        geometry_utils.draw_circle(hole_sketch, hole_r,
                                    adsk.core.Point3D.create(hole_x, 0, 0))
        geometry_utils.extrude_cut(component, hole_sketch.profiles.item(0),
                                    t + mm(3.0), participants=[tag_body])

        # --- decorative grooves at the right end ------------------------------
        stripe_count = params["stripe_count"]
        if stripe_count > 0:
            stripe_sketch = geometry_utils.sketch_on_xy(component)
            stripe_lines = stripe_sketch.sketchCurves.sketchLines
            x0 = length / 2.0 - mm(6.0)
            for i in range(stripe_count):
                x_left = x0 - i * mm(3.4) - mm(1.5)
                rect = [(x_left, -half_w), (x_left + mm(1.5), -half_w),
                        (x_left + mm(1.5), half_w), (x_left, half_w)]
                sk_pts = [stripe_sketch.modelToSketchSpace(
                    adsk.core.Point3D.create(x, y, 0)) for (x, y) in rect]
                for j in range(4):
                    stripe_lines.addByTwoPoints(sk_pts[j], sk_pts[(j + 1) % 4])
            stripe_profiles = [stripe_sketch.profiles.item(i)
                               for i in range(stripe_sketch.profiles.count)]
            cut_from_top(stripe_profiles, mm(0.6))

        # --- text and symbol ---------------------------------------------------
        symbol_char = SYMBOL_PRESETS.get(params["symbol"])
        if symbol_char is None:  # Custom
            symbol_char = params["symbol_text"].strip()
        text = params["text"].strip()

        stripes_zone = mm(6.0) + stripe_count * mm(3.4)
        zone_left = hole_x + hole_r + mm(5.0)
        zone_right = length / 2.0 - stripes_zone - mm(3.0)

        def add_relief_text(content, char_height, y0, y1, font, bold):
            text_sketch = geometry_utils.sketch_on_xy(component)
            texts = text_sketch.sketchTexts
            text_input = texts.createInput2(content, char_height)
            corner = text_sketch.modelToSketchSpace(
                adsk.core.Point3D.create(zone_left, y0, 0))
            diagonal = text_sketch.modelToSketchSpace(
                adsk.core.Point3D.create(zone_right, y1, 0))
            text_input.setAsMultiLine(
                corner, diagonal,
                adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
                adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0)
            text_input.fontName = font
            if bold:
                text_input.textStyle = adsk.fusion.TextStyles.TextStyleBold
            sketch_text = texts.add(text_input)
            profiles = geometry_utils.collect([sketch_text])
            if raised:
                raise_from_top_text(profiles)
            else:
                cut_input = extrudes.createInput(
                    profiles, adsk.fusion.FeatureOperations.CutFeatureOperation)
                cut_input.startExtent = adsk.fusion.OffsetStartDefinition.create(
                    adsk.core.ValueInput.createByReal(t - depth))
                cut_input.setOneSideExtent(
                    adsk.fusion.DistanceExtentDefinition.create(
                        adsk.core.ValueInput.createByReal(depth + mm(2.0))),
                    adsk.fusion.ExtentDirections.PositiveExtentDirection)
                cut_input.participantBodies = [tag_body]
                extrudes.add(cut_input)

        def raise_from_top_text(profiles):
            new_input = extrudes.createInput(
                profiles, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            new_input.setOneSideExtent(
                adsk.fusion.DistanceExtentDefinition.create(
                    adsk.core.ValueInput.createByReal(t + depth)),
                adsk.fusion.ExtentDirections.PositiveExtentDirection)
            feature = extrudes.add(new_input)
            bodies = [feature.bodies.item(i) for i in range(feature.bodies.count)]
            geometry_utils.combine_join(component, tag_body, bodies)

        if text and symbol_char:
            add_relief_text(symbol_char, mm(params["symbol_size"]),
                             mm(1.0), half_w - mm(3.0),
                             "Segoe UI Symbol", False)
            add_relief_text(text, mm(params["text_height"]),
                             -half_w + mm(3.0), -mm(1.0),
                             params["font"], params["text_bold"])
        elif text:
            add_relief_text(text, mm(params["text_height"]),
                             -half_w * 0.6, half_w * 0.6,
                             params["font"], params["text_bold"])
        elif symbol_char:
            add_relief_text(symbol_char, mm(params["symbol_size"]),
                             -half_w * 0.7, half_w * 0.7,
                             "Segoe UI Symbol", False)
