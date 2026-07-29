"""Axolotl figurine on the SDF mesh backend."""

from ..base import Generator, ParamSpec
from ..meshrunner import RESOLUTIONS, run_mesh_job
from ..registry import register

SDF_VOXELS = {"Draft": 1.1, "Standard": 0.7, "Fine": 0.5, "Ultra": 0.35}


@register
class Axolotl(Generator):
    id = "creature_axolotl"
    display_name = "Axolotl"
    category = "Creature"
    supports_preview = False
    parameters = [
        ParamSpec(name="length", label="Length", type="float", default=90.0,
                  min=40.0, max=200.0, unit="mm"),
        ParamSpec(name="chubbiness", label="Chubbiness", type="float", default=1.0,
                  min=0.7, max=1.4),
        ParamSpec(name="leg_size", label="Leg Size", type="float", default=1.0,
                  min=0.6, max=1.5),
        ParamSpec(name="gill_size", label="Gill Size", type="float", default=1.0,
                  min=0.5, max=1.6),
        ParamSpec(name="tail_size", label="Tail Size", type="float", default=1.0,
                  min=0.5, max=1.6),
        ParamSpec(name="seed", label="Variation Seed", type="int", default=1,
                  min=1, max=9999),
        ParamSpec(name="resolution", label="Mesh Resolution", type="choice",
                  default="Standard", choices=list(RESOLUTIONS.keys())),
        ParamSpec(name="import_mesh", label="Import mesh into Fusion (slow)",
                  type="bool", default=False),
    ]

    def build(self, component, params: dict) -> None:
        mesh_params = {
            "object": "axolotl",
            "length": params["length"],
            "chubbiness": params["chubbiness"],
            "leg_size": params["leg_size"],
            "gill_size": params["gill_size"],
            "tail_size": params["tail_size"],
            "seed": params["seed"],
            "voxel_mm": SDF_VOXELS[params["resolution"]],
        }
        run_mesh_job(component, mesh_params, "axolotl", params["import_mesh"])
