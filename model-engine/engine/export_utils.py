"""Export B-rep bodies from the active design to STL or 3MF."""

import os
import time

import adsk.core
import adsk.fusion

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_OUT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "generated"))


def export_bodies(bodies, folder: str = None, fmt: str = "stl",
                   name_prefix: str = "print_object") -> list:
    """Exports each body to its own file. Returns list of written paths.

    fmt: 'stl' or '3mf'
    """
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        raise ValueError("No active Fusion design.")

    folder = folder or _DEFAULT_OUT
    os.makedirs(folder, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    fmt = fmt.lower().lstrip(".")
    if fmt not in ("stl", "3mf"):
        raise ValueError("Format must be stl or 3mf.")

    export_mgr = design.exportManager
    written = []
    for i, body in enumerate(bodies):
        safe = _safe_name(body.name if body.name else f"body_{i + 1}")
        path = os.path.join(folder, f"{name_prefix}_{safe}_{stamp}_{i + 1}.{fmt}")
        if fmt == "stl":
            options = export_mgr.createSTLExportOptions(body, path)
            options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementMedium
        else:
            options = export_mgr.createC3MFExportOptions(body, path)
        export_mgr.execute(options)
        written.append(path)
    return written


def collect_visible_brep_bodies(design: adsk.fusion.Design) -> list:
    bodies = []
    root = design.rootComponent
    for i in range(root.bRepBodies.count):
        b = root.bRepBodies.item(i)
        if b.isVisible:
            bodies.append(b)
    for occ in root.allOccurrences:
        for i in range(occ.bRepBodies.count):
            b = occ.bRepBodies.item(i)
            if b.isVisible:
                bodies.append(b)
    return bodies


def _safe_name(name: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_" else "_" for c in name.strip())
    return cleaned[:40] or "body"
