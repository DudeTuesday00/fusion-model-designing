"""Combined Basic Planter + matching Drip Tray in one dialog.

Builds the planter first, then a drip tray sized from the planter's bottom
width/shape and shared clearance/wall settings. Tray-only options (ribs,
feet, rim finish, flare) live in their own parameter groups.
"""

from ..base import Generator, ParamSpec
from ..registry import register
from .planter_basic import BasicPlanter
from .planter_drip_tray import DripTray, FOOT_PARAMS, RIM_PARAMS


@register
class PlanterWithMatchingTray(Generator):
    id = "planter_with_tray"
    display_name = "Planter + Matching Drip Tray"
    category = "Planter"
    parameters = [
        # --- Planter (core) ---
        ParamSpec(name="shape", label="Shape", type="choice", default="Round",
                  choices=["Round", "Hexagon", "Square"]),
        ParamSpec(name="top_diameter", label="Top Width / Diameter", type="float",
                  default=120.0, min=20.0, max=500.0, unit="mm"),
        ParamSpec(name="bottom_diameter", label="Bottom Width / Diameter", type="float",
                  default=90.0, min=20.0, max=500.0, unit="mm"),
        ParamSpec(name="height", label="Planter Height", type="float",
                  default=100.0, min=20.0, max=500.0, unit="mm"),
        ParamSpec(name="wall_thickness", label="Planter Wall Thickness", type="float",
                  default=3.0, min=1.2, max=20.0, unit="mm"),
        ParamSpec(name="base_thickness", label="Planter Base Thickness", type="float",
                  default=4.0, min=1.2, max=30.0, unit="mm"),
        ParamSpec(name="corner_radius", label="Corner Radius (Square only)", type="float",
                  default=10.0, min=0.0, max=50.0, unit="mm"),
        ParamSpec(name="drainage_hole_count", label="Drainage Holes", type="int",
                  default=5, min=0, max=20),
        ParamSpec(name="drainage_hole_diameter", label="Drainage Hole Diameter", type="float",
                  default=8.0, min=2.0, max=30.0, unit="mm"),
        ParamSpec(name="rim_style", label="Planter Rim Style", type="choice",
                  default="Flat", choices=["Flat", "Rounded"]),
        # --- Planter decoration ---
        ParamSpec(name="flute_count", label="Flutes (Round only, 0 = none)", type="int",
                  default=0, min=0, max=48, group="Decoration"),
        ParamSpec(name="flute_depth", label="Flute Depth", type="float",
                  default=1.2, min=0.4, max=5.0, unit="mm", group="Decoration"),
        ParamSpec(name="flute_style", label="Flute Style", type="choice",
                  default="Straight",
                  choices=["Straight", "Spiral", "CrissCross"], group="Decoration"),
        ParamSpec(name="relief", label="Flute/Rib Relief", type="choice",
                  default="Recessed", choices=["Recessed", "Raised"], group="Decoration"),
        ParamSpec(name="flute_twist", label="Flute Twist (deg)", type="float",
                  default=20.0, min=5.0, max=180.0, group="Decoration"),
        ParamSpec(name="texture", label="Surface Texture (Round only)", type="choice",
                  default="None", choices=["None", "Ribbed", "Bubbles", "Bark"],
                  group="Decoration"),
        ParamSpec(name="texture_depth", label="Texture Depth", type="float",
                  default=0.8, min=0.3, max=3.0, unit="mm", group="Decoration"),
        # --- Tray sizing / fit ---
        ParamSpec(name="clearance", label="Tray Clearance Around Pot", type="float",
                  default=3.0, min=0.5, max=20.0, unit="mm", group="Tray"),
        ParamSpec(name="tray_height", label="Tray Height", type="float",
                  default=15.0, min=5.0, max=60.0, unit="mm", group="Tray"),
        ParamSpec(name="tray_wall_thickness", label="Tray Wall Thickness", type="float",
                  default=2.4, min=1.2, max=10.0, unit="mm", group="Tray"),
        ParamSpec(name="tray_base_thickness", label="Tray Base Thickness", type="float",
                  default=3.0, min=1.2, max=15.0, unit="mm", group="Tray"),
        ParamSpec(name="flare_angle", label="Tray Wall Flare Angle (deg)", type="float",
                  default=15.0, min=0.0, max=45.0, group="Tray"),
        ParamSpec(name="tray_corner_radius", label="Tray Corner Radius (Square)", type="float",
                  default=13.0, min=0.0, max=60.0, unit="mm", group="Tray"),
        ParamSpec(name="rib_count", label="Support Ribs (Round tray)", type="int",
                  default=4, min=0, max=8, group="Tray"),
        ParamSpec(name="rib_width", label="Rib Width", type="float",
                  default=8.0, min=4.0, max=20.0, unit="mm", group="Tray"),
        ParamSpec(name="standoff_height", label="Standoff Height", type="float",
                  default=4.0, min=1.0, max=15.0, unit="mm", group="Tray"),
        ParamSpec(name="foot_length", label="Foot Length Under Pot", type="float",
                  default=12.0, min=5.0, max=40.0, unit="mm", group="Tray"),
        ParamSpec(name="centering_gap", label="Centering Gap", type="float",
                  default=1.0, min=0.2, max=5.0, unit="mm", group="Tray"),
    ] + [
        ParamSpec(name=p.name, label=p.label, type=p.type, default=p.default,
                  min=p.min, max=p.max, unit=p.unit, choices=list(p.choices),
                  group=p.group or "Tray")
        for p in RIM_PARAMS
    ] + [
        ParamSpec(name=p.name, label=p.label, type=p.type, default=p.default,
                  min=p.min, max=p.max, unit=p.unit, choices=list(p.choices),
                  group=p.group or "Feet")
        for p in FOOT_PARAMS
    ]

    def build(self, component, params: dict) -> None:
        planter = BasicPlanter()
        tray = DripTray()

        planter_params = {
            "shape": params["shape"],
            "top_diameter": params["top_diameter"],
            "bottom_diameter": params["bottom_diameter"],
            "height": params["height"],
            "wall_thickness": params["wall_thickness"],
            "base_thickness": params["base_thickness"],
            "corner_radius": params["corner_radius"],
            "rim_height": 14.0,
            "rim_protrude": 4.0,
            "drainage_hole_count": params["drainage_hole_count"],
            "drainage_hole_diameter": params["drainage_hole_diameter"],
            "rim_style": params["rim_style"],
            "flute_count": params["flute_count"],
            "flute_depth": params["flute_depth"],
            "flute_style": params["flute_style"],
            "relief": params["relief"],
            "flute_twist": params["flute_twist"],
            "texture": params["texture"],
            "texture_depth": params["texture_depth"],
        }
        planter.build(component, planter_params)

        tray_params = {
            "shape": params["shape"],
            "pot_bottom_diameter": params["bottom_diameter"],
            "clearance": params["clearance"],
            "tray_height": params["tray_height"],
            "wall_thickness": params["tray_wall_thickness"],
            "base_thickness": params["tray_base_thickness"],
            "flare_angle": params["flare_angle"],
            "corner_radius": params["tray_corner_radius"],
            "rib_count": params["rib_count"],
            "rib_width": params["rib_width"],
            "standoff_height": params["standoff_height"],
            "foot_length": params["foot_length"],
            "centering_gap": params["centering_gap"],
            "rim_finish": params["rim_finish"],
            "base_style": params["base_style"],
            "base_attachment": params["base_attachment"],
            "foot_height": params["foot_height"],
            "foot_size": params["foot_size"],
            "foot_count": params["foot_count"],
        }
        tray.build(component, tray_params)
