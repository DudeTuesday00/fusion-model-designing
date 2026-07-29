"""Organic aquarium decor on the mesh backend: rocks and coral.

Like the Textured Planter, these write print-ready STLs into `generated/`
instead of building Fusion features. Every generator has a Variation Seed -
same settings + different seed = a different individual rock or coral, so
you can print a whole natural-looking cluster from one dialog.

Print in PLA or PETG; rinse before tank use.
"""

from ..base import Generator, ParamSpec
from ..meshrunner import RESOLUTIONS, run_mesh_job
from ..registry import register

# Voxel size (mm) for the SDF/marching-cubes objects at each resolution.
SDF_VOXELS = {"Draft": 1.1, "Standard": 0.7, "Fine": 0.5, "Ultra": 0.35}

_COMMON_TAIL = [
    ParamSpec(name="seed", label="Variation Seed", type="int", default=1,
              min=1, max=9999),
    ParamSpec(name="resolution", label="Mesh Resolution", type="choice",
              default="Standard", choices=list(RESOLUTIONS.keys())),
    ParamSpec(name="import_mesh", label="Import mesh into Fusion (slow)",
              type="bool", default=False),
]


def _run(component, params, object_name, keys, prefix):
    segments = RESOLUTIONS[params["resolution"]]
    mesh_params = {key: params[key] for key in keys}
    mesh_params["object"] = object_name
    mesh_params["seed"] = params["seed"]
    mesh_params["segments_around"] = segments[0]
    mesh_params["segments_vertical"] = segments[1]
    mesh_params["voxel_mm"] = SDF_VOXELS[params["resolution"]]
    run_mesh_job(component, mesh_params, prefix, params["import_mesh"])


@register
class AquariumRock(Generator):
    id = "aquarium_rock"
    display_name = "Rock"
    category = "Aquarium Decor"
    parameters = [
        ParamSpec(name="width", label="Width", type="float", default=80.0,
                  min=15.0, max=300.0, unit="mm"),
        ParamSpec(name="depth", label="Depth", type="float", default=60.0,
                  min=15.0, max=300.0, unit="mm"),
        ParamSpec(name="height", label="Height", type="float", default=50.0,
                  min=10.0, max=250.0, unit="mm"),
        ParamSpec(name="roughness", label="Roughness", type="float", default=0.25,
                  min=0.05, max=0.55),
        ParamSpec(name="detail_scale", label="Detail Density", type="float",
                  default=1.0, min=0.3, max=3.0),
        ParamSpec(name="flatten", label="Base Flattening", type="float",
                  default=6.0, min=0.0, max=40.0, unit="mm"),
    ] + _COMMON_TAIL

    def build(self, component, params: dict) -> None:
        _run(component, params, "rock",
              ("width", "depth", "height", "roughness", "detail_scale", "flatten"),
              "rock")


@register
class BrainCoral(Generator):
    id = "aquarium_brain_coral"
    display_name = "Brain Coral"
    category = "Aquarium Decor"
    parameters = [
        ParamSpec(name="diameter", label="Diameter", type="float", default=90.0,
                  min=25.0, max=250.0, unit="mm"),
        ParamSpec(name="height", label="Height", type="float", default=45.0,
                  min=12.0, max=150.0, unit="mm"),
        ParamSpec(name="ridge_depth", label="Ridge Depth", type="float", default=3.0,
                  min=1.0, max=8.0, unit="mm"),
        ParamSpec(name="ridge_scale", label="Ridge Density", type="float",
                  default=1.0, min=0.3, max=3.0),
    ] + _COMMON_TAIL

    def build(self, component, params: dict) -> None:
        _run(component, params, "brain_coral",
              ("diameter", "height", "ridge_depth", "ridge_scale"),
              "brain_coral")


@register
class FingerCoral(Generator):
    id = "aquarium_finger_coral"
    display_name = "Finger Coral"
    category = "Aquarium Decor"
    parameters = [
        ParamSpec(name="base_diameter", label="Base Diameter", type="float",
                  default=70.0, min=25.0, max=200.0, unit="mm"),
        ParamSpec(name="base_height", label="Base Height", type="float",
                  default=25.0, min=8.0, max=80.0, unit="mm"),
        ParamSpec(name="finger_count", label="Fingers", type="int", default=7,
                  min=3, max=16),
        ParamSpec(name="finger_length", label="Finger Length", type="float",
                  default=45.0, min=15.0, max=120.0, unit="mm"),
        ParamSpec(name="finger_diameter", label="Finger Diameter", type="float",
                  default=14.0, min=6.0, max=40.0, unit="mm"),
        ParamSpec(name="waviness", label="Waviness", type="float", default=6.0,
                  min=0.0, max=20.0, unit="mm"),
    ] + _COMMON_TAIL

    def build(self, component, params: dict) -> None:
        _run(component, params, "finger_coral",
              ("base_diameter", "base_height", "finger_count", "finger_length",
               "finger_diameter", "waviness"),
              "finger_coral")


@register
class AquariumLog(Generator):
    id = "aquarium_log"
    display_name = "Hollow Log"
    category = "Aquarium Decor"
    parameters = [
        ParamSpec(name="length", label="Length", type="float", default=150.0,
                  min=60.0, max=300.0, unit="mm"),
        ParamSpec(name="diameter", label="Diameter", type="float", default=60.0,
                  min=30.0, max=150.0, unit="mm"),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=6.0, min=3.0, max=20.0, unit="mm"),
        ParamSpec(name="window_width", label="Side Opening Width (0 = none)",
                  type="float", default=45.0, min=0.0, max=100.0, unit="mm"),
        ParamSpec(name="bark_depth", label="Bark Depth", type="float",
                  default=2.8, min=0.5, max=6.0, unit="mm"),
    ] + _COMMON_TAIL

    def build(self, component, params: dict) -> None:
        _run(component, params, "log",
              ("length", "diameter", "wall_thickness", "window_width", "bark_depth"),
              "log")


@register
class TirePile(Generator):
    id = "aquarium_tire_pile"
    display_name = "Tire Pile"
    category = "Aquarium Decor"
    parameters = [
        ParamSpec(name="tire_diameter", label="Tire Diameter", type="float",
                  default=90.0, min=40.0, max=200.0, unit="mm"),
        ParamSpec(name="tire_thickness", label="Tire Thickness", type="float",
                  default=30.0, min=15.0, max=60.0, unit="mm"),
        ParamSpec(name="tread_depth", label="Tread Depth", type="float",
                  default=1.5, min=0.5, max=4.0, unit="mm"),
        ParamSpec(name="tire_count", label="Tires (1 flat ... 4 = pile)",
                  type="int", default=2, min=1, max=4),
    ] + _COMMON_TAIL

    def build(self, component, params: dict) -> None:
        _run(component, params, "tire_pile",
              ("tire_diameter", "tire_thickness", "tread_depth", "tire_count"),
              "tires")


@register
class Anchor(Generator):
    id = "aquarium_anchor"
    display_name = "Anchor"
    category = "Aquarium Decor"
    parameters = [
        ParamSpec(name="height", label="Height", type="float", default=120.0,
                  min=50.0, max=250.0, unit="mm"),
        ParamSpec(name="chunkiness", label="Chunkiness", type="float",
                  default=1.0, min=0.6, max=1.8),
    ] + _COMMON_TAIL

    def build(self, component, params: dict) -> None:
        _run(component, params, "anchor", ("height", "chunkiness"), "anchor")


@register
class SunkenShip(Generator):
    id = "aquarium_sunken_ship"
    display_name = "Sunken Ship"
    category = "Aquarium Decor"
    parameters = [
        ParamSpec(name="length", label="Hull Length", type="float", default=160.0,
                  min=80.0, max=350.0, unit="mm"),
        ParamSpec(name="width", label="Hull Width", type="float", default=55.0,
                  min=30.0, max=120.0, unit="mm"),
        ParamSpec(name="hull_depth", label="Hull Depth", type="float", default=40.0,
                  min=20.0, max=90.0, unit="mm"),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=5.0, min=3.0, max=12.0, unit="mm"),
        ParamSpec(name="heel_angle", label="Heel Angle (deg)", type="float",
                  default=18.0, min=0.0, max=35.0),
        ParamSpec(name="mast_count", label="Broken Masts", type="int",
                  default=2, min=0, max=2),
        ParamSpec(name="mast_height", label="Mast Height", type="float",
                  default=45.0, min=15.0, max=120.0, unit="mm"),
        ParamSpec(name="breach_width", label="Hull Breach (0 = none)", type="float",
                  default=30.0, min=0.0, max=70.0, unit="mm"),
        ParamSpec(name="plank_depth", label="Planking Depth", type="float",
                  default=0.8, min=0.0, max=2.5, unit="mm"),
    ] + _COMMON_TAIL

    def build(self, component, params: dict) -> None:
        _run(component, params, "sunken_ship",
              ("length", "width", "hull_depth", "wall_thickness", "heel_angle",
               "mast_count", "mast_height", "breach_width", "plank_depth"),
              "shipwreck")


@register
class StaghornCoral(Generator):
    id = "aquarium_staghorn_coral"
    display_name = "Staghorn Coral (branching)"
    category = "Aquarium Decor"
    parameters = [
        ParamSpec(name="height", label="Height", type="float", default=95.0,
                  min=30.0, max=250.0, unit="mm"),
        ParamSpec(name="branch_levels", label="Branching Levels", type="int",
                  default=4, min=2, max=6),
        ParamSpec(name="spread", label="Branch Spread (deg)", type="float",
                  default=38.0, min=15.0, max=70.0),
        ParamSpec(name="thickness", label="Trunk Thickness", type="float",
                  default=9.0, min=4.0, max=25.0, unit="mm"),
        ParamSpec(name="noise_amp", label="Surface Bumpiness", type="float",
                  default=0.6, min=0.0, max=2.5, unit="mm"),
    ] + _COMMON_TAIL

    def build(self, component, params: dict) -> None:
        _run(component, params, "staghorn_coral",
              ("height", "branch_levels", "spread", "thickness", "noise_amp"),
              "staghorn")


@register
class RockCave(Generator):
    id = "aquarium_rock_cave"
    display_name = "Rock Cave / Arch"
    category = "Aquarium Decor"
    parameters = [
        ParamSpec(name="width", label="Width", type="float", default=110.0,
                  min=50.0, max=300.0, unit="mm"),
        ParamSpec(name="height", label="Height", type="float", default=70.0,
                  min=30.0, max=200.0, unit="mm"),
        ParamSpec(name="depth", label="Depth", type="float", default=60.0,
                  min=25.0, max=200.0, unit="mm"),
        ParamSpec(name="boulder_size", label="Boulder Size", type="float",
                  default=26.0, min=10.0, max=80.0, unit="mm"),
        ParamSpec(name="boulder_count", label="Boulders Per Side", type="int",
                  default=9, min=5, max=16),
        ParamSpec(name="noise_amp", label="Surface Bumpiness", type="float",
                  default=1.6, min=0.0, max=4.0, unit="mm"),
    ] + _COMMON_TAIL

    def build(self, component, params: dict) -> None:
        _run(component, params, "rock_cave",
              ("width", "height", "depth", "boulder_size", "boulder_count",
               "noise_amp"),
              "rock_cave")
