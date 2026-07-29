"""Organic aquarium decor meshes: rocks and coral.

All three builders produce closed, consistently-wound shells:
- build_rock: noise-displaced ellipsoid with a flattened underside.
- build_brain_coral: squashed dome with ridged-noise convolutions.
- build_finger_coral: a rocky base mound plus wavy tapered fingers. The
  fingers are separate closed shells that overlap the base - slicers union
  overlapping shells within one STL, so the print comes out as one piece.

Each accepts a `seed` so the same parameters can produce endless variants.
"""

import numpy as np

try:
    from .textures import _smoothstep
except ImportError:  # running as a plain script via generate.py
    from textures import _smoothstep


# --- hash-based 3D value noise (no lattice storage, stable per seed) -------

def _hash01(ix, iy, iz, seed):
    # uint32 wraparound is the whole point of the hash - silence the warning.
    with np.errstate(over="ignore"):
        n = (ix.astype(np.uint32) * np.uint32(73856093)
             ^ iy.astype(np.uint32) * np.uint32(19349663)
             ^ iz.astype(np.uint32) * np.uint32(83492791))
        n = n + np.uint32((seed * 1013904223) & 0xFFFFFFFF)
        n = (n ^ (n >> np.uint32(13))) * np.uint32(1274126177)
        n = n ^ (n >> np.uint32(16))
    return (n & np.uint32(0x7FFFFFFF)).astype(np.float64) / float(0x7FFFFFFF)


def noise3(points, cell_mm, seed=1, octaves=3):
    """Fractal value noise sampled at (n, 3) points, in [0, 1]."""
    total = np.zeros(points.shape[:-1])
    amp, norm = 1.0, 0.0
    for octave in range(octaves):
        g = points / (cell_mm / (2 ** octave))
        i0 = np.floor(g).astype(np.int64)
        f = _smoothstep(g - i0)
        result = np.zeros(points.shape[:-1])
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    corner = _hash01(i0[..., 0] + dx, i0[..., 1] + dy,
                                      i0[..., 2] + dz, seed + octave * 977)
                    weight = ((f[..., 0] if dx else 1 - f[..., 0])
                              * (f[..., 1] if dy else 1 - f[..., 1])
                              * (f[..., 2] if dz else 1 - f[..., 2]))
                    result += corner * weight
        total += amp * result
        norm += amp
        amp *= 0.5
    return total / norm


# --- shared triangulation helpers -------------------------------------------

def _latlong_shell(rings, top_point, bottom_point=None, bottom_center=None):
    """Triangulates a stack of rings (list of (n_th, 3)) top to bottom, with
    either a bottom pole point or a flat fan to bottom_center."""
    tris = []

    def strip(upper, lower):
        a, b = upper, np.roll(upper, -1, axis=0)
        c, d = lower, np.roll(lower, -1, axis=0)
        tris.append(np.stack([a, b, c], axis=1))
        tris.append(np.stack([b, d, c], axis=1))

    first = rings[0]
    a, b = first, np.roll(first, -1, axis=0)
    tris.append(np.stack([np.broadcast_to(top_point, a.shape), b, a], axis=1))

    for i in range(len(rings) - 1):
        strip(rings[i], rings[i + 1])

    last = rings[-1]
    a, b = last, np.roll(last, -1, axis=0)
    closure = bottom_point if bottom_point is not None else bottom_center
    tris.append(np.stack([np.broadcast_to(closure, a.shape), a, b], axis=1))

    return np.concatenate(tris, axis=0)


def _fix_winding(tris):
    """Flips all triangles if the shell is inside-out (negative volume)."""
    volume = np.einsum("ij,ij->i", tris[:, 0],
                        np.cross(tris[:, 1], tris[:, 2])).sum() / 6.0
    return tris[:, ::-1] if volume < 0 else tris


def _rest_on_floor(tris, flatten_mm=0.0):
    """Optionally squashes everything below a plane, then sits the mesh on z=0."""
    z = tris[..., 2]
    if flatten_mm > 0:
        z_floor = z.min() + flatten_mm
        np.clip(z, z_floor, None, out=z)
    tris[..., 2] -= tris[..., 2].min()
    return tris


# --- rock --------------------------------------------------------------------

def build_rock(params):
    a = params["width"] / 2.0
    b = params["depth"] / 2.0
    c = params["height"] / 2.0
    roughness = params.get("roughness", 0.25)
    detail = params.get("detail_scale", 1.0)
    seed = int(params.get("seed", 1))
    n_th = params["segments_around"]
    n_ph = params["segments_vertical"]

    theta = np.linspace(0, 2 * np.pi, n_th, endpoint=False)
    phi = np.linspace(0, np.pi, n_ph)[1:-1]
    TH, PH = np.meshgrid(theta, phi)
    dirs = np.stack([np.sin(PH) * np.cos(TH),
                      np.sin(PH) * np.sin(TH),
                      np.cos(PH)], axis=-1)
    p0 = dirs * np.array([a, b, c])

    big = noise3(p0, 26.0 / detail, seed)
    small = noise3(p0, 8.0 / detail, seed + 5)
    mult = 1.0 + roughness * (2.0 * big - 1.0) + 0.3 * roughness * (2.0 * small - 1.0)
    p = p0 * mult[..., None]

    top = np.array([0.0, 0.0, c * (1.0 + roughness * (2.0 * float(
        noise3(np.array([[0.0, 0.0, c]]), 26.0 / detail, seed)[0]) - 1.0))])
    bottom = np.array([0.0, 0.0, -c])

    rings = [p[i] for i in range(p.shape[0])]
    tris = _latlong_shell(rings, top, bottom_point=bottom)
    tris = _fix_winding(tris)
    return _rest_on_floor(tris, params.get("flatten", 6.0))


# --- brain coral ---------------------------------------------------------------

def build_brain_coral(params):
    a = params["diameter"] / 2.0
    c = params["height"]
    ridge_depth = params.get("ridge_depth", 3.0)
    scale = params.get("ridge_scale", 1.0)
    seed = int(params.get("seed", 1))
    n_th = params["segments_around"]
    n_ph = max(24, params["segments_vertical"] // 2)

    theta = np.linspace(0, 2 * np.pi, n_th, endpoint=False)
    phi = np.linspace(0, np.pi / 2, n_ph)[1:]  # skip the pole row itself
    TH, PH = np.meshgrid(theta, phi)
    p0 = np.stack([a * np.sin(PH) * np.cos(TH),
                    a * np.sin(PH) * np.sin(TH),
                    c * np.cos(PH)], axis=-1)

    # Meandering ridges: ridged fractal noise, faded out toward the rim so
    # the bottom edge stays a clean circle sitting flat on the sand.
    n = noise3(p0, 11.0 / scale, seed, octaves=2)
    ridged = (1.0 - np.abs(2.0 * n - 1.0)) ** 1.6
    rim_fade = _smoothstep((np.pi / 2 - PH) / 0.3)
    normals = p0 / np.maximum(np.linalg.norm(p0, axis=-1, keepdims=True), 1e-9)
    p = p0 + normals * (ridge_depth * ridged * rim_fade)[..., None]

    top = np.array([0.0, 0.0, c + ridge_depth * (1.0 - abs(2.0 * float(
        noise3(np.array([[0.0, 0.0, c]]), 11.0 / scale, seed, octaves=2)[0]) - 1.0)) ** 1.6])

    rings = [p[i] for i in range(p.shape[0])]
    tris = _latlong_shell(rings, top, bottom_center=np.array([0.0, 0.0, 0.0]))
    tris = _fix_winding(tris)
    tris[..., 2] -= tris[..., 2].min()
    return tris


# --- SDF-based objects (smoothly blended organic shapes) -----------------------
#
# These import sdf lazily so the lat-long objects above still work even if
# scikit-image isn't installed.

def _require_sdf():
    try:
        try:
            from . import sdf
        except ImportError:
            import sdf
        from skimage import measure  # noqa: F401
        return sdf
    except ImportError:
        raise RuntimeError(
            "This object needs scikit-image on the system Python. "
            "Run: pip install scikit-image")


def build_staghorn_coral(params):
    """Branching staghorn coral: recursive skeleton of tapered branches,
    smooth-blended so forks melt together like the real thing."""
    sdf = _require_sdf()
    height = params["height"]
    levels = int(params.get("branch_levels", 4))
    spread_deg = params.get("spread", 38.0)
    thickness = params.get("thickness", 9.0)
    seed = int(params.get("seed", 1))
    voxel = params.get("voxel_mm", 0.65)

    rng = np.random.default_rng(seed)
    segments = []  # (a, b, r1, r2)

    def grow(base, direction, length, radius, level):
        # Each branch is two sub-segments with a slight bend for natural curve.
        bend = _unit(direction + rng.normal(0, 0.16, 3) + [0, 0, 0.10])
        mid = base + direction * (length * 0.5)
        tip = mid + bend * (length * 0.5)
        r_mid = radius * 0.82
        r_tip = radius * (0.62 if level > 0 else 0.45)
        segments.append((base, mid, radius, r_mid))
        segments.append((mid, tip, r_mid, r_tip))
        if level == 0:
            return
        child_count = int(rng.choice([2, 2, 2, 3]))
        base_azimuth = rng.uniform(0, 2 * np.pi)
        for c in range(child_count):
            azimuth = base_azimuth + 2 * np.pi * c / child_count + rng.uniform(-0.4, 0.4)
            tilt = np.radians(spread_deg * rng.uniform(0.7, 1.25))
            perp = _perpendicular(bend, azimuth)
            child_dir = _unit(bend * np.cos(tilt) + perp * np.sin(tilt) + [0, 0, 0.18])
            grow(tip, child_dir, length * rng.uniform(0.62, 0.78),
                  r_tip, level - 1)

    trunk_r = thickness / 2.0
    grow(np.array([0.0, 0.0, 0.0]), _unit([0.05, 0.02, 1.0]),
          height * 0.30, trunk_r, levels)

    # Scale the whole skeleton so the requested height comes out exact.
    all_pts = np.array([p for seg in segments for p in (seg[0], seg[1])])
    current_h = all_pts[:, 2].max()
    scale = height / max(current_h, 1e-6)
    segments = [(a * scale, b * scale, r1 * scale, r2 * scale)
                for (a, b, r1, r2) in segments]
    all_pts = all_pts * scale

    scene = sdf.Scene(blend_mm=max(2.0, trunk_r * scale * 0.5),
                       noise_amp=params.get("noise_amp", 0.6),
                       noise_cell=5.0, seed=seed)
    # Trumpet base flare anchoring the colony.
    scene.add(sdf.round_cone([0, 0, -3.0], [0, 0, height * 0.10],
                              trunk_r * scale * 2.4, trunk_r * scale * 1.1))
    for (a, b, r1, r2) in segments:
        scene.add(sdf.round_cone(a, b, r1, r2))
    scene_cut = _floor_wrap(sdf, scene)

    margin = trunk_r * scale * 3.0 + 4.0
    lo, hi = sdf.bounds_for_points(all_pts, margin)
    lo[2] = -voxel * 1.5  # half-voxel offset: z=0 must fall BETWEEN grid planes
    tris = sdf.mesh_scene(scene_cut, lo, hi, voxel)
    tris[..., 2] -= tris[..., 2].min()
    return tris


def build_rock_cave(params):
    """A boulder-pile arch with a swim-through tunnel."""
    sdf = _require_sdf()
    width = params["width"]
    height = params["height"]
    depth = params["depth"]
    boulder = params.get("boulder_size", 26.0) / 2.0
    count = int(params.get("boulder_count", 9))
    seed = int(params.get("seed", 1))
    voxel = params.get("voxel_mm", 0.8)

    rng = np.random.default_rng(seed)
    rx = width / 2.0 - boulder * 0.7
    rz = height - boulder * 0.8

    scene = sdf.Scene(blend_mm=boulder * 0.45,
                       noise_amp=params.get("noise_amp", 1.6),
                       noise_cell=11.0, seed=seed)
    centers = []
    for row_offset in (-depth / 4.0, depth / 4.0):
        for i in range(count):
            t = (i + 0.5) / count
            angle = np.pi * t
            center = np.array([
                rx * np.cos(angle) * rng.uniform(0.92, 1.08),
                row_offset + rng.uniform(-depth * 0.08, depth * 0.08),
                max(rz * np.sin(angle) * rng.uniform(0.9, 1.05), boulder * 0.35),
            ])
            radii = boulder * rng.uniform(0.65, 1.25, 3)
            radii[1] = min(radii[1], depth / 4.0)  # keep the tunnel open
            scene.add(sdf.ellipsoid(center, radii))
            centers.append(center)

    scene_cut = _floor_wrap(sdf, scene)
    lo, hi = sdf.bounds_for_points(np.array(centers), boulder * 1.6 + 4.0)
    lo[2] = -voxel * 1.5  # half-voxel offset: z=0 must fall BETWEEN grid planes
    tris = sdf.mesh_scene(scene_cut, lo, hi, voxel)
    tris[..., 2] -= tris[..., 2].min()
    return tris


def _floor_wrap(sdf, scene):
    """Wraps a scene so everything below z=0 is cut flat (sits on the sand)."""
    class _Cut:
        def eval(self, points):
            return np.maximum(scene.eval(points), -points[:, 2])
    return _Cut()


def _unit(v):
    v = np.asarray(v, dtype=np.float64)
    return v / max(np.linalg.norm(v), 1e-12)


def _perpendicular(direction, azimuth):
    ref = np.array([1.0, 0.0, 0.0])
    if abs(direction @ ref) > 0.9:
        ref = np.array([0.0, 1.0, 0.0])
    u = _unit(np.cross(direction, ref))
    v = np.cross(direction, u)
    return u * np.cos(azimuth) + v * np.sin(azimuth)


# --- finger coral ---------------------------------------------------------------

def build_finger_coral(params):
    """Wavy tapered fingers growing out of a rocky mound - SDF version, so
    fingers melt smoothly into the base and each other, with a noisy skin."""
    sdf = _require_sdf()
    base_r = params["base_diameter"] / 2.0
    base_h = params["base_height"]
    count = int(params["finger_count"])
    length = params["finger_length"]
    finger_r = params["finger_diameter"] / 2.0
    waviness = params.get("waviness", 6.0)
    seed = int(params.get("seed", 1))
    voxel = params.get("voxel_mm", 0.7)

    rng = np.random.default_rng(seed)
    scene = sdf.Scene(blend_mm=max(2.5, finger_r * 0.5),
                       noise_amp=params.get("noise_amp", 1.0),
                       noise_cell=6.5, seed=seed)

    scene.add(sdf.ellipsoid([0.0, 0.0, 0.0], [base_r, base_r, base_h * 1.35]))

    key_points = [np.array([base_r, base_r, base_h]),
                  np.array([-base_r, -base_r, 0.0])]
    for i in range(count):
        azimuth = 2 * np.pi * i / count + rng.uniform(-0.25, 0.25)
        spread = rng.uniform(0.15, 0.55)
        direction = _unit([np.cos(azimuth) * spread,
                            np.sin(azimuth) * spread,
                            1.0 - spread * 0.5])
        start_r = base_r * rng.uniform(0.1, 0.5)
        point = np.array([np.cos(azimuth) * start_r,
                           np.sin(azimuth) * start_r,
                           base_h * 0.3])
        this_len = length * rng.uniform(0.7, 1.15)
        this_rad = finger_r * rng.uniform(0.8, 1.1)

        # Chain of bending segments = a wavy finger; smooth union melts the
        # elbows so it reads as one curved digit.
        n_seg = 4
        radius = this_rad
        for s in range(n_seg):
            seg_len = this_len / n_seg
            tilt = np.radians(waviness * 2.6) * rng.uniform(-1.0, 1.0)
            perp = _perpendicular(direction, rng.uniform(0, 2 * np.pi))
            direction = _unit(direction * np.cos(tilt) + perp * np.sin(tilt)
                               + [0, 0, 0.05])
            tip = point + direction * seg_len
            r_next = radius * (0.55 if s == n_seg - 1 else 0.87)
            scene.add(sdf.round_cone(point, tip, radius, r_next))
            point, radius = tip, r_next
            key_points.append(tip.copy())

    scene_cut = _floor_wrap(sdf, scene)
    lo, hi = sdf.bounds_for_points(np.array(key_points), finger_r * 2.0 + 5.0)
    lo[2] = -voxel * 1.5  # half-voxel offset: z=0 must fall BETWEEN grid planes
    tris = sdf.mesh_scene(scene_cut, lo, hi, voxel)
    tris[..., 2] -= tris[..., 2].min()
    return tris


def build_log(params):
    """Hollow log lying on its side: bark-ridged trunk, open bored ends, an
    optional oval swim-through window in the wall, flattened belly."""
    sdf = _require_sdf()
    length = params["length"]
    radius = params["diameter"] / 2.0
    wall = params.get("wall_thickness", 6.0)
    window_w = params.get("window_width", 45.0)
    bark_depth = params.get("bark_depth", 2.0)
    seed = int(params.get("seed", 1))
    voxel = params.get("voxel_mm", 0.8)

    rng = np.random.default_rng(seed)
    center_z = radius * 0.82  # belly dips below z=0 -> flattened by floor cut
    half = length / 2.0
    bore_r = max(radius - wall, radius * 0.45)

    body = sdf.capsule([-half - 5, 0, center_z], [half + 5, 0, center_z], radius)
    bore = sdf.capsule([-half - 20, 0, center_z], [half + 20, 0, center_z], bore_r)
    win_len = window_w * rng.uniform(1.25, 1.6)
    win_x = length * rng.uniform(-0.12, 0.12)
    window = sdf.ellipsoid([win_x, 0.0, center_z + radius * 0.55],
                            [win_len / 2.0, radius * 2.0, window_w / 2.0])

    class _LogField:
        def eval(self, points):
            d = body(points)
            d = np.maximum(d, np.abs(points[:, 0]) - half)   # flat-cut ends
            # Bark: ridged noise stretched along the trunk. Only evaluate
            # near the surface band - the empty grid is most of the volume.
            band = np.abs(d) < (bark_depth + 3.0)
            if band.any():
                # Two bark layers: long deep furrows + fine ridges, both
                # stretched along the trunk so they read as grain.
                p_coarse = points[band] * np.array([0.12, 1.0, 1.0])
                furrows = (1.0 - np.abs(2.0 * noise3(p_coarse, 15.0, seed + 7,
                                                      octaves=2) - 1.0)) ** 2.2
                p_fine = points[band] * np.array([0.30, 1.0, 1.0])
                ridges = (1.0 - np.abs(2.0 * noise3(p_fine, 8.0, seed,
                                                     octaves=3) - 1.0)) ** 2.0
                d[band] = d[band] - bark_depth * (0.6 * furrows + 0.4 * ridges)
            d = np.maximum(d, -bore(points))                 # hollow it out
            if window_w > 0:
                d = np.maximum(d, -window(points))           # side doorway
            return np.maximum(d, -points[:, 2])              # flat belly
    lo = np.array([-half - bark_depth - 4, -radius - bark_depth - 4, -voxel * 1.5])
    hi = np.array([half + bark_depth + 4, radius + bark_depth + 4,
                    center_z + radius + bark_depth + 4])
    tris = sdf.mesh_scene(_LogField(), lo, hi, voxel)
    tris[..., 2] -= tris[..., 2].min()
    return tris


def build_tire_pile(params):
    """Old tires: one flat on the sand, more leaning/stacked against it.
    Treaded toruses, fused where they touch, floor-cut flat."""
    sdf = _require_sdf()
    tire_d = params["tire_diameter"]
    section = params.get("tire_thickness", 30.0)
    tread_depth = params.get("tread_depth", 1.5)
    count = int(params.get("tire_count", 2))
    seed = int(params.get("seed", 1))
    voxel = params.get("voxel_mm", 0.7)

    rng = np.random.default_rng(seed)
    r_minor = section / 2.0
    R = tire_d / 2.0 - r_minor
    squash = 0.78  # sidewalls flatter than the tread

    def make_tire(center, tilt_deg, azimuth_deg, block_count):
        cos_t, sin_t = np.cos(np.radians(tilt_deg)), np.sin(np.radians(tilt_deg))
        cos_a, sin_a = np.cos(np.radians(azimuth_deg)), np.sin(np.radians(azimuth_deg))
        rot_x = np.array([[1, 0, 0], [0, cos_t, -sin_t], [0, sin_t, cos_t]])
        rot_z = np.array([[cos_a, -sin_a, 0], [sin_a, cos_a, 0], [0, 0, 1]])
        rot = rot_x @ rot_z
        center = np.asarray(center, dtype=np.float64)

        def fn(points):
            p = (points - center) @ rot.T
            ring = np.hypot(p[:, 0], p[:, 1]) - R
            d = np.hypot(ring, p[:, 2] / squash) - r_minor
            theta = np.arctan2(p[:, 1], p[:, 0])
            phi = np.arctan2(p[:, 2] / squash, ring)
            raw = np.sin(block_count * theta + 1.1 * np.sin(3.0 * phi))
            blocks = np.clip((raw + 0.15) / 0.45, 0.0, 1.0) ** 0.8  # flat-top blocks
            tread_zone = np.clip((np.radians(68) - np.abs(phi)) / 0.35, 0.0, 1.0)
            groove = np.clip((np.radians(7) - np.abs(phi)) / np.radians(7), 0.0, 1.0)
            return (d - tread_depth * blocks * tread_zone
                    + tread_depth * 0.9 * groove)
        reach = R + r_minor + tread_depth + 2.0
        fn.bounds = (center - reach, center + reach)
        return fn

    outer = R + r_minor * squash
    tires = [make_tire([0, 0, r_minor * squash + 0.2], 0.0,
                        rng.uniform(0, 360), int(rng.integers(22, 30)))]
    if count >= 2:  # leaning against the flat one
        tires.append(make_tire([0, outer * 0.75, R + r_minor * 0.4],
                                72.0 + rng.uniform(-6, 6), rng.uniform(0, 360),
                                int(rng.integers(22, 30))))
    if count >= 3:  # second flat tire stacked, slightly offset
        tires.append(make_tire([r_minor * 0.5, -r_minor * 0.4,
                                 3.0 * r_minor * squash + 0.2],
                                rng.uniform(-6, 6), rng.uniform(0, 360),
                                int(rng.integers(22, 30))))
    if count >= 4:  # another leaning on the other side
        tires.append(make_tire([-outer * 0.7, -outer * 0.45, R + r_minor * 0.5],
                                68.0 + rng.uniform(-6, 6), rng.uniform(30, 60),
                                int(rng.integers(22, 30))))

    scene = sdf.Scene(blend_mm=1.8, noise_amp=0.0, seed=seed)
    for t in tires:
        scene.add(t)
    scene_cut = _floor_wrap(sdf, scene)

    los = np.array([t.bounds[0] for t in tires])
    his = np.array([t.bounds[1] for t in tires])
    lo, hi = los.min(axis=0), his.max(axis=0)
    lo[2] = -voxel * 1.5
    tris = sdf.mesh_scene(scene_cut, lo, hi, voxel)
    tris[..., 2] -= tris[..., 2].min()
    return tris


def build_anchor(params):
    """Classic admiralty anchor lying flat: ring, shank, stock crossbar,
    curved arms with flukes. Smooth-min melts it into one cast piece; the
    flat back prints on the bed with no supports."""
    sdf = _require_sdf()
    H = params["height"]
    chunk = params.get("chunkiness", 1.0)
    voxel = params.get("voxel_mm", 0.6)

    rr = H * 0.042 * chunk          # shank radius
    zc = rr * 0.85                  # member centers: back gets floor-cut flat
    ring_r = H * 0.085

    scene = sdf.Scene(blend_mm=max(2.0, rr * 0.8))
    # Ring at the top (lies flat, so a Z-axis torus).
    ring_c = np.array([0.0, H / 2.0 - ring_r, zc])
    scene.add(sdf.torus(ring_c, ring_r, rr * 0.72))
    # Shank down the middle.
    crown = np.array([0.0, -H * 0.34, zc])
    scene.add(sdf.round_cone([0.0, H / 2.0 - 2.0 * ring_r, zc], crown,
                              rr * 0.95, rr * 1.15))
    # Stock: the crossbar near the top, ball-ended.
    stock_y = H / 2.0 - 2.6 * ring_r
    scene.add(sdf.capsule([-H * 0.19, stock_y, zc], [H * 0.19, stock_y, zc],
                           rr * 0.78))
    # Arms: circular arcs from the crown up to the fluke tips, 3 segments each.
    tip_x, tip_y = H * 0.30, -H * 0.04
    for side in (1.0, -1.0):
        prev = crown
        ctrl = np.array([side * H * 0.24, -H * 0.36, zc])
        end = np.array([side * tip_x, tip_y, zc])
        ks = np.linspace(0.0, 1.0, 9)[1:]
        for k in ks:
            # Quadratic arc through a low outboard control point; fine
            # segments + linear taper keep the arm smooth, not beaded.
            pt = ((1 - k) ** 2) * crown + 2 * (1 - k) * k * ctrl + (k ** 2) * end
            r_here = rr * (1.1 - 0.35 * (k - 0.125))
            r_next = rr * (1.1 - 0.35 * k)
            scene.add(sdf.round_cone(prev, pt, r_here, r_next))
            prev = pt
        # Fluke: flattened spade at the arm tip, pointing up-outward.
        scene.add(sdf.ellipsoid([side * (tip_x + H * 0.008), tip_y + H * 0.055, zc],
                                 [H * 0.055, H * 0.105, zc * 0.95]))

    class _Cut:
        def eval(self, pts):
            return np.maximum(scene.eval(pts), -pts[:, 2])
    lo = np.array([-H * 0.42, -H * 0.55, -voxel * 1.5])
    hi = np.array([H * 0.42, H * 0.55, zc + rr * 1.6 + 4.0])
    tris = sdf.mesh_scene(_Cut(), lo, hi, voxel)
    tris[..., 2] -= tris[..., 2].min()
    return tris


def build_sunken_ship(params):
    """Shipwreck: an open-top hull heeled over and buried to the sand line,
    with broken masts, a cabin, planking ridges and a hull breach."""
    sdf = _require_sdf()
    L = params["length"]
    W = params["width"]
    D = params.get("hull_depth", 40.0)
    wall = params.get("wall_thickness", 5.0)
    heel = np.radians(params.get("heel_angle", 18.0))
    mast_count = int(params.get("mast_count", 2))
    mast_h = params.get("mast_height", 45.0)
    plank = params.get("plank_depth", 0.8)
    breach_w = params.get("breach_width", 30.0)
    seed = int(params.get("seed", 1))
    voxel = params.get("voxel_mm", 0.8)

    rng = np.random.default_rng(seed)
    pitch = np.radians(rng.uniform(2.0, 6.0))
    cos_h, sin_h = np.cos(heel), np.sin(heel)
    cos_p, sin_p = np.cos(pitch), np.sin(pitch)
    rot_x = np.array([[1, 0, 0], [0, cos_h, -sin_h], [0, sin_h, cos_h]])
    rot_y = np.array([[cos_p, 0, sin_p], [0, 1, 0], [-sin_p, 0, cos_p]])
    R = rot_x @ rot_y
    lift = D * 0.55  # how high the deck plane sits; keel below gets buried

    cabin = sdf.rounded_box([-L * 0.22, 0.0, 9.0],
                             [L * 0.095, W * 0.30, 10.0], 3.0)
    mast_specs = []
    xs = [L * 0.16, -L * 0.34][:max(mast_count, 0)]
    for i, mx in enumerate(xs):
        h = mast_h * rng.uniform(0.55, 1.0) if i else mast_h
        lean = rng.uniform(-0.12, 0.12)
        mast_specs.append((np.array([mx, 0.0, -2.0]),
                            np.array([mx + lean * h, lean * h * 0.5, h]),
                            h))
    breach_c = np.array([L * rng.uniform(0.05, 0.25),
                          -W * 0.5, -D * 0.45])

    def smin(a, b, k=3.0):
        h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
        return b * (1.0 - h) + a * h - k * h * (1.0 - h)

    class _ShipField:
        def eval(self, points):
            pl = (points - np.array([0.0, 0.0, lift])) @ R
            x, y, z = pl[:, 0], pl[:, 1], pl[:, 2]
            nx = np.clip(2.0 * x / L, -1.0, 1.0)
            # Bow (x>0) sharper than the stern.
            expo = np.where(nx > 0, 2.6, 2.0)
            w_env = (W / 2.0) * np.maximum(1.0 - np.abs(nx) ** expo, 1e-3) ** 0.55
            d_env = D * (1.0 - 0.55 * nx ** 4) + 1e-3

            def shell(w_e, d_e):
                rho = np.sqrt((y / w_e) ** 2 + (np.minimum(z, 0.0) / d_e) ** 2)
                return (rho - 1.0) * np.minimum(w_e, d_e) * 0.85

            # End slabs kill the degenerate axis sliver that the clipped
            # width envelope leaves running past the bow and stern.
            hull_solid = np.maximum(np.maximum(shell(w_env, d_env), z),
                                     np.abs(x) - L / 2.0)              # closed at deck
            cavity = np.maximum(shell(np.maximum(w_env - wall, 1.0),
                                        np.maximum(d_env - wall, 2.0)),
                                 z - 30.0)
            d = np.maximum(hull_solid, -cavity)                       # open boat

            # Planking ridges on the OUTER hull only - keyed to the outer
            # shell distance so the cavity walls stay smooth.
            so = shell(w_env, d_env)
            band = (np.abs(so) < plank + 2.5) & (z < -1.0)
            if band.any():
                ridges = (0.5 + 0.5 * np.sin(2.0 * np.pi * z[band] / 6.0)) ** 3
                d[band] = d[band] - plank * ridges

            d = smin(d, cabin(pl), 3.0)
            for (a, b, h) in mast_specs:
                mast = sdf.round_cone(a, b, 3.2, 2.4)(pl)
                mast = np.maximum(mast, z - h)                        # broken top
                d = smin(d, mast, 2.5)
            if breach_w > 0:
                hole = sdf.ellipsoid(breach_c, [breach_w / 2.0, wall * 3.0,
                                                  breach_w / 2.8])(pl)
                d = np.maximum(d, -hole)
            return np.maximum(d, -points[:, 2])                       # sand line
    margin = 12.0
    lo = np.array([-L / 2.0 - margin, -W / 2.0 - W * sin_h - margin, -voxel * 1.5])
    hi = np.array([L / 2.0 + margin, W / 2.0 + margin,
                    lift + mast_h + margin])
    tris = sdf.mesh_scene(_ShipField(), lo, hi, voxel)
    tris[..., 2] -= tris[..., 2].min()
    return tris
