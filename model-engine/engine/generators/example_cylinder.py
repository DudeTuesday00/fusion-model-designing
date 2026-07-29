"""Placeholder generator - proves the dialog-to-geometry pipeline works end to end.

This isn't a real product (no planter is just a plain cylinder). Once the
engine plumbing is confirmed working in Fusion, this should be replaced by
the first real planter generator following the same pattern.
"""

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..registry import register


@register
class ExampleCylinder(Generator):
    id = "example_cylinder"
    display_name = "Example Cylinder (placeholder)"
    category = "Examples"
    parameters = [
        ParamSpec(name="diameter", label="Diameter", type="float", default=60.0,
                  min=5.0, max=300.0, unit="mm"),
        ParamSpec(name="height", label="Height", type="float", default=80.0,
                  min=5.0, max=300.0, unit="mm"),
    ]

    def build(self, component, params: dict) -> None:
        radius_cm = geometry_utils.mm(params["diameter"]) / 2.0
        height_cm = geometry_utils.mm(params["height"])

        sketch = geometry_utils.sketch_on_xy(component)
        geometry_utils.draw_circle(sketch, radius_cm)
        profile = sketch.profiles.item(0)

        geometry_utils.extrude_profile(component, profile, height_cm)
