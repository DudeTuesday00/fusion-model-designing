"""Shared plumbing for mesh-backend generators.

Collects parameters into JSON, runs mesh_engine/generate.py on the system
Python, and reports the resulting STL. Used by the textured planter and the
aquarium decor generators.
"""

import json
import os
import subprocess
import tempfile
import time

import adsk.core
import adsk.fusion

from .syspython import CREATE_NO_WINDOW, find_system_python

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ADDIN_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_GENERATE_PY = os.path.join(_ADDIN_DIR, "mesh_engine", "generate.py")
OUTPUT_DIR = os.path.abspath(os.path.join(_ADDIN_DIR, "..", "generated"))

RESOLUTIONS = {
    "Draft": (288, 180),
    "Standard": (512, 320),
    "Fine": (768, 480),
    "Ultra": (1024, 640),
}


def run_mesh_job(component, mesh_params: dict, filename_prefix: str,
                  import_mesh: bool) -> None:
    """Generates an STL via the system Python and tells the user where it is."""
    python_exe = find_system_python()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(OUTPUT_DIR, f"{filename_prefix}_{stamp}.stl")

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                      encoding="utf-8") as tmp:
        json.dump(mesh_params, tmp)
        params_path = tmp.name

    try:
        result = subprocess.run(
            [python_exe, _GENERATE_PY, params_path, out_path],
            capture_output=True, text=True, timeout=300,
            creationflags=CREATE_NO_WINDOW,
        )
    finally:
        try:
            os.remove(params_path)
        except OSError:
            pass

    if result.returncode != 0:
        raise ValueError(
            "Mesh generation failed:\n"
            + (result.stderr or result.stdout or "no output").strip()[-1500:]
        )

    stats = json.loads(result.stdout.strip().splitlines()[-1])

    if import_mesh:
        _import_mesh(component, out_path)

    adsk.core.Application.get().userInterface.messageBox(
        "Mesh written to:\n{path}\n\n"
        "{tris:,} triangles, {dims[0]} x {dims[1]} x {dims[2]} mm, "
        "generated in {secs}s.\n\n"
        "The STL is print-ready - open it directly in your slicer.".format(
            path=out_path, tris=stats["triangles"],
            dims=stats["dimensions_mm"], secs=stats["seconds"]),
        "Print Engine",
    )


def _import_mesh(component, stl_path):
    # Parametric designs require mesh bodies to live inside a base feature.
    design = component.parentDesign
    if design.designType == adsk.fusion.DesignTypes.ParametricDesignType:
        base_feature = component.features.baseFeatures.add()
        base_feature.startEdit()
        try:
            component.meshBodies.add(
                stl_path, adsk.fusion.MeshUnits.MillimeterMeshUnit, base_feature)
        finally:
            base_feature.finishEdit()
    else:
        component.meshBodies.add(stl_path, adsk.fusion.MeshUnits.MillimeterMeshUnit)
