"""CLI entry point the Fusion add-in calls on the SYSTEM Python.

Usage:  python generate.py <params.json> <output.stl>

params.json keys (all lengths in mm):
  profile: Straight | Barrel | Bowl | Hourglass
  bottom_diameter, top_diameter, height, bulge
  wall_thickness, base_thickness, drainage_hole_diameter (0 = none)
  texture: see textures.TEXTURES
  texture_depth, texture_scale
  segments_around, segments_vertical

Prints a one-line JSON result to stdout on success; exits non-zero with a
message on stderr on failure.
"""

import json
import sys
import time


def main():
    if len(sys.argv) != 3:
        print("usage: generate.py <params.json> <output.stl>", file=sys.stderr)
        return 2

    try:
        import numpy  # noqa: F401
    except ImportError:
        print("numpy is not installed for this Python. Run: pip install numpy",
              file=sys.stderr)
        return 3

    from surface import build_pot
    from stl_io import save_stl
    import creatures
    import decor
    import tray

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        params = json.load(f)

    builders = {
        "pot": build_pot,
        "rock": decor.build_rock,
        "brain_coral": decor.build_brain_coral,
        "finger_coral": decor.build_finger_coral,
        "staghorn_coral": decor.build_staghorn_coral,
        "rock_cave": decor.build_rock_cave,
        "log": decor.build_log,
        "tire_pile": decor.build_tire_pile,
        "anchor": decor.build_anchor,
        "sunken_ship": decor.build_sunken_ship,
        "axolotl": creatures.build_axolotl,
        "tray": tray.build_tray,
    }
    builder = builders[params.get("object", "pot")]

    started = time.time()
    tris = builder(params)
    save_stl(sys.argv[2], tris)

    mins = tris.reshape(-1, 3).min(axis=0)
    maxs = tris.reshape(-1, 3).max(axis=0)
    print(json.dumps({
        "triangles": int(len(tris)),
        "dimensions_mm": [round(float(d), 1) for d in (maxs - mins)],
        "seconds": round(time.time() - started, 1),
        "path": sys.argv[2],
    }))
    return 0


if __name__ == "__main__":
    # Allow running as a plain script: make sibling modules importable.
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
