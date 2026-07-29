"""Textured trays and display bowls on the mesh backend.

Matches the Textured Planter's design language: pick the SAME texture,
depth, density and twist you used for the pot and the tray carries its
pattern. Two styles:
- Saucer: shallow flared dish with an optional raised seat ring inside.
- Tilted Bowl: the sculptural slant-rim bowl a pot nests inside - rim
  sweeps from full height at the back down to the front.

Writes a print-ready STL to generated/, like all mesh objects.
"""

from ..base import Generator, ParamSpec
from ..meshrunner import RESOLUTIONS, run_mesh_job
from ..registry import register


@register
class TexturedTray(Generator):
    id = "planter_tray_mesh"
    display_name = "Textured Tray / Display Bowl (Mesh)"
    category = "Planter"
    parameters = [
        ParamSpec(name="style", label="Style", type="choice", default="Saucer",
                  choices=["Saucer", "Tilted Bowl"]),
        ParamSpec(name="cross_section", label="Cross-Section (match your pot)",
                  type="choice", default="Round",
                  choices=["Round", "Square", "Triangle"]),
        ParamSpec(name="pot_bottom_diameter", label="Pot Bottom Diameter", type="float",
                  default=100.0, min=40.0, max=400.0, unit="mm"),
        ParamSpec(name="clearance", label="Clearance Around Pot", type="float",
                  default=4.0, min=1.0, max=25.0, unit="mm"),
        ParamSpec(name="height", label="Height (back rim)", type="float",
                  default=20.0, min=10.0, max=120.0, unit="mm"),
        ParamSpec(name="tilt_percent", label="Rim Tilt (%: 0 = level)", type="float",
                  default=0.0, min=0.0, max=75.0),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=2.8, min=1.6, max=8.0, unit="mm"),
        ParamSpec(name="base_thickness", label="Base Thickness", type="float",
                  default=3.0, min=1.6, max=10.0, unit="mm"),
        ParamSpec(name="seat_ring", label="Raised seat ring inside", type="bool",
                  default=True),
        ParamSpec(name="texture", label="Texture (match your pot)", type="choice",
                  default="None",
                  choices=["None", "Knurl", "Scales", "Pinecone", "Pleats", "Pills",
                            "Bark", "Bubbles", "Drips", "Pinstripe", "Lobes",
                            "Shingles", "Arcs", "Hearts", "Honeycomb",
                            "Triangle Ribs", "Weave", "Y-Tiles", "Soft Cutout"]),
        ParamSpec(name="texture_depth", label="Texture Depth", type="float",
                  default=1.5, min=0.2, max=6.0, unit="mm"),
        ParamSpec(name="texture_scale", label="Texture Density", type="float",
                  default=1.0, min=0.3, max=3.0),
        ParamSpec(name="texture_twist", label="Texture Twist (deg)", type="float",
                  default=0.0, min=0.0, max=360.0),
        ParamSpec(name="resolution", label="Mesh Resolution", type="choice",
                  default="Standard", choices=list(RESOLUTIONS.keys())),
        ParamSpec(name="import_mesh", label="Import mesh into Fusion (slow)",
                  type="bool", default=False),
    ]

    def build(self, component, params: dict) -> None:
        segments = RESOLUTIONS[params["resolution"]]
        mesh_params = {key: params[key] for key in (
            "style", "cross_section", "pot_bottom_diameter", "clearance", "height",
            "tilt_percent", "wall_thickness", "base_thickness", "seat_ring",
            "texture", "texture_depth", "texture_scale", "texture_twist",
        )}
        mesh_params["object"] = "tray"
        mesh_params["segments_around"] = segments[0]
        mesh_params["segments_vertical"] = segments[1]
        run_mesh_job(component, mesh_params,
                      f"tray_{params['style'].lower().replace(' ', '_')}",
                      params["import_mesh"])
