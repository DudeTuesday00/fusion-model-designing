"""Creature builders on the SDF backend.

A creature is an SDF composition: a spine of tapered segments for the body,
limbs and appendages as more segments, flattened ellipsoids for fins, all
melted together with smooth-min and skinned with a whisper of noise. The
belly dips slightly below z=0 and gets floor-cut flat, so figures sit flat
on the print bed with no supports.
"""

import numpy as np

try:
    from .decor import _require_sdf, _floor_wrap, _unit
except ImportError:  # running as a plain script via generate.py
    from decor import _require_sdf, _floor_wrap, _unit


def build_axolotl(params):
    sdf = _require_sdf()
    L = params["length"]
    chub = params.get("chubbiness", 1.0)
    leg_len = params.get("leg_length", 14.0)
    gill_len = params.get("gill_length", 13.0)
    tail_h = params.get("tail_height", 20.0)
    seed = int(params.get("seed", 1))
    voxel = params.get("voxel_mm", 0.6)

    rng = np.random.default_rng(seed)
    jig = lambda s: rng.uniform(-s, s)  # tiny pose jitter per seed

    r_head = 0.150 * L * chub
    r_body = 0.120 * L * chub
    zc = r_head * 0.92  # spine height: belly dips below z=0 -> flat after cut

    scene = sdf.Scene(blend_mm=max(2.5, 0.032 * L),
                       noise_amp=params.get("noise_amp", 0.25),
                       noise_cell=7.0, seed=seed)
    key_points = []

    def note(*pts):
        key_points.extend(np.asarray(p, dtype=float) for p in pts)

    # --- head: wide, blunt and rounded --------------------------------------
    head_center = np.array([0.16 * L, 0.0, zc])
    scene.add(sdf.ellipsoid(head_center, [0.155 * L, 0.145 * L * chub, 0.105 * L]))
    note(head_center + [0.16 * L, 0.15 * L, 0.11 * L],
         head_center - [0.16 * L, 0.15 * L, 0.11 * L])

    # --- body: head -> hips, with a plump belly ------------------------------
    scene.add(sdf.round_cone([0.28 * L, 0.0, zc], [0.62 * L, 0.0, zc * 0.98],
                              r_body, 0.055 * L))
    scene.add(sdf.ellipsoid([0.44 * L, 0.0, zc * 0.92],
                             [0.20 * L, r_body * 1.06, r_body * 0.92]))
    note([0.28 * L, -r_body * 1.1, 0.0], [0.62 * L, r_body * 1.1, 2 * zc])

    # --- tail: a vertical fin blade that arcs up and tapers to a tip --------
    n_tail = 8
    for i in range(n_tail):
        t = i / (n_tail - 1.0)
        x = 0.60 * L + t * 0.38 * L
        z = zc * (1.0 - 0.15 * t) + 0.42 * tail_h * np.sin(np.pi * t * 0.6)
        envelope = np.sin(np.pi * min(t * 0.85 + 0.15, 1.0))
        half_height = max(0.62 * tail_h * envelope * (1.0 - 0.2 * t), 0.06 * L)
        thin = 0.024 * L * (1.0 - 0.6 * t) + 0.5
        center = np.array([x, jig(0.004 * L), z])
        scene.add(sdf.ellipsoid(center, [0.055 * L, thin, half_height]))
        note(center + [0.06 * L, 3, half_height + 2],
             center - [0.06 * L, 3, half_height + 2])

    # --- legs: four stubby limbs, feet flattened by the floor cut ------------
    for x_frac, forward in ((0.315, 0.020), (0.565, -0.010)):
        for side in (1.0, -1.0):
            hip = np.array([x_frac * L, side * r_body * 0.72, zc * 0.55])
            foot = hip + np.array([forward * L + jig(0.01 * L),
                                     side * leg_len * 0.85,
                                     -zc * 0.62])
            scene.add(sdf.round_cone(hip, foot, 0.034 * L * chub, 0.026 * L * chub))
            scene.add(sdf.ellipsoid(foot + [0.006 * L, side * 0.004 * L, -0.004 * L],
                                     [0.034 * L, 0.030 * L, 0.020 * L]))
            note(foot + [0.05 * L, side * 0.05 * L, 0], hip)

    # --- gills: three frilly stalks per side, ball-tipped ---------------------
    for i, x_frac in enumerate((0.175, 0.225, 0.275)):
        droop = i * 0.12
        length = gill_len * (1.0 - 0.18 * i)
        for side in (1.0, -1.0):
            root = np.array([x_frac * L, side * r_head * 0.78, zc + r_head * 0.30])
            direction = _unit([0.35 + droop, side * 1.0, 0.55 - droop])
            tip = root + direction * length
            scene.add(sdf.capsule(root, tip, 0.013 * L))
            scene.add(sdf.ellipsoid(tip, [0.020 * L] * 3))
            note(tip + [0.03 * L, side * 0.03 * L, 0.03 * L])

    # --- eyes: two subtle domes on top of the head ----------------------------
    for side in (1.0, -1.0):
        scene.add(sdf.ellipsoid([0.115 * L, side * r_head * 0.58, zc + r_head * 0.52],
                                 [0.020 * L, 0.020 * L, 0.016 * L]))

    scene_cut = _floor_wrap(sdf, scene)
    pts = np.array(key_points)
    lo, hi = sdf.bounds_for_points(pts, 4.0)
    lo[2] = -voxel * 1.5  # z=0 must fall between grid planes
    tris = sdf.mesh_scene(scene_cut, lo, hi, voxel)
    tris[..., 2] -= tris[..., 2].min()
    # Center on x/y origin for tidy slicer placement.
    flat = tris.reshape(-1, 3)
    tris[..., 0] -= (flat[:, 0].min() + flat[:, 0].max()) / 2.0
    tris[..., 1] -= (flat[:, 1].min() + flat[:, 1].max()) / 2.0
    return tris
