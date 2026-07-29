"""First creature: the axolotl - a chunky, support-free figurine.

Runs on the SDF mesh backend: body, tail fin, stubby legs, frilly gills and
eye bumps are all distance fields melted together, so limbs grow smoothly
out of the body like a sculpted figure. The belly and feet are floor-cut
flat, so it prints lying down with no supports.
"""

from ..base import Generator, ParamSpec
from ..meshrunner import run_mesh_job
from ..registry import register
from .aquarium_mesh_decor import SDF_VOXELS


@register
class Axolotl(Generator):
    id = "creature_axolotl"
    display_name = "Axolotl"
    category = "Creatures"
    parameters = [
        ParamSpec(name="length", label="Length (nose to tail)", type="float",
                  default=110.0, min=40.0, max=300.0, unit="mm"),
        ParamSpec(name="chubbiness", label="Chubbiness", type="float",
                  default=1.0, min=0.7, max=1.4),
        ParamSpec(name="leg_length", label="Leg Length", type="float",
                  default=14.0, min=6.0, max=40.0, unit="mm"),
        ParamSpec(name="gill_length", label="Gill Length", type="float",
                  default=13.0, min=5.0, max=35.0, unit="mm"),
        ParamSpec(name="tail_height", label="Tail Fin Height", type="float",
                  default=20.0, min=8.0, max=60.0, unit="mm"),
        ParamSpec(name="noise_amp", label="Skin Texture", type="float",
                  default=0.25, min=0.0, max=1.5, unit="mm"),
        ParamSpec(name="seed", label="Variation Seed", type="int", default=1,
                  min=1, max=9999),
        ParamSpec(name="resolution", label="Mesh Resolution", type="choice",
                  default="Standard", choices=list(SDF_VOXELS.keys())),
        ParamSpec(name="import_mesh", label="Import mesh into Fusion (slow)",
                  type="bool", default=False),
    ]

    def build(self, component, params: dict) -> None:
        mesh_params = {key: params[key] for key in (
            "length", "chubbiness", "leg_length", "gill_length",
            "tail_height", "noise_amp", "seed",
        )}
        mesh_params["object"] = "axolotl"
        mesh_params["voxel_mm"] = SDF_VOXELS[params["resolution"]]
        run_mesh_job(component, mesh_params, "axolotl", params["import_mesh"])
