"""Textured planter - the mesh backend generator.

Unlike the other generators, this one doesn't build Fusion B-rep features.
It hands the parameters to mesh_engine/generate.py running on the system
Python (which has numpy), which computes a displacement-surface pot -
hundreds of thousands of triangles, like commercial textured-vase models -
and writes a print-ready STL into the project's `generated` folder.

Optionally the STL is also imported into Fusion as a mesh body for preview
(slower for high resolutions - the file is already printable without it).
"""

from ..base import Generator, ParamSpec
from ..meshrunner import RESOLUTIONS as _RESOLUTIONS
from ..meshrunner import run_mesh_job
from ..registry import register


@register
class TexturedPlanter(Generator):
    id = "planter_textured"
    display_name = "Textured Planter (Mesh/STL)"
    category = "Planter"
    parameters = [
        ParamSpec(name="texture", label="Texture", type="choice", default="Knurl",
                  choices=["None", "Knurl", "Scales", "Pinecone", "Pleats", "Pills",
                            "Bark", "Bubbles", "Drips", "Pinstripe", "Lobes",
                            "Shingles", "Arcs", "Hearts", "Honeycomb",
                            "Triangle Ribs", "Weave", "Y-Tiles", "Soft Cutout"]),
        ParamSpec(name="cross_section", label="Cross-Section", type="choice",
                  default="Round", choices=["Round", "Square", "Triangle"]),
        ParamSpec(name="texture_twist", label="Texture Twist (deg)", type="float",
                  default=0.0, min=0.0, max=360.0),
        ParamSpec(name="interior", label="Interior Wall", type="choice",
                  default="Smooth", choices=["Smooth", "Follow Texture"]),
        ParamSpec(name="profile", label="Silhouette", type="choice", default="Barrel",
                  choices=["Straight", "Barrel", "Bowl", "Hourglass"]),
        ParamSpec(name="bottom_diameter", label="Bottom Diameter", type="float",
                  default=100.0, min=40.0, max=400.0, unit="mm"),
        ParamSpec(name="top_diameter", label="Top Diameter", type="float",
                  default=130.0, min=40.0, max=400.0, unit="mm"),
        ParamSpec(name="height", label="Height", type="float",
                  default=105.0, min=30.0, max=400.0, unit="mm"),
        ParamSpec(name="bulge", label="Silhouette Bulge", type="float",
                  default=8.0, min=0.0, max=40.0, unit="mm"),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=3.0, min=1.6, max=10.0, unit="mm"),
        ParamSpec(name="base_thickness", label="Base Thickness", type="float",
                  default=4.0, min=1.6, max=12.0, unit="mm"),
        ParamSpec(name="drainage_hole_diameter", label="Drainage Hole (0 = none)",
                  type="float", default=12.0, min=0.0, max=40.0, unit="mm"),
        ParamSpec(name="texture_depth", label="Texture Depth", type="float",
                  default=1.8, min=0.2, max=10.0, unit="mm"),
        ParamSpec(name="texture_scale", label="Texture Density", type="float",
                  default=1.0, min=0.3, max=3.0),
        ParamSpec(name="resolution", label="Mesh Resolution", type="choice",
                  default="Standard", choices=list(_RESOLUTIONS.keys())),
        ParamSpec(name="import_mesh", label="Import mesh into Fusion (slow)",
                  type="bool", default=False),
    ]

    def build(self, component, params: dict) -> None:
        segments = _RESOLUTIONS[params["resolution"]]
        mesh_params = {key: params[key] for key in (
            "texture", "profile", "bottom_diameter", "top_diameter", "height",
            "bulge", "wall_thickness", "base_thickness", "drainage_hole_diameter",
            "texture_depth", "texture_scale", "cross_section", "texture_twist",
            "interior",
        )}
        mesh_params["segments_around"] = segments[0]
        mesh_params["segments_vertical"] = segments[1]

        run_mesh_job(component, mesh_params,
                      f"planter_{params['texture'].lower()}", params["import_mesh"])
