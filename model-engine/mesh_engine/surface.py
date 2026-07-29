"""Builds a watertight textured pot mesh.

The pot is a displacement surface: outer radius(theta, z) = profile(z) +
texture(theta, z), with a smooth inner wall offset by the wall thickness, a
rim strip joining them at the top, and a floor. An optional center drainage
hole punches through the base as a tube (no mesh booleans needed - the hole
is built into the triangulation).

Triangle winding is consistent and outward throughout; verify_mesh() checks
closedness (every directed edge used exactly once) and positive volume.
"""

import numpy as np

try:
    from .textures import TEXTURES, _smoothstep
except ImportError:  # running as a plain script via generate.py
    from textures import TEXTURES, _smoothstep

MIN_WALL_MM = 0.9      # texture may never thin the wall below this
FADE_MM = 3.0          # texture fades out over this span at top and bottom


def profile_function(kind: str, bottom_r: float, top_r: float,
                      height: float, bulge: float):
    """Returns r(z) for the pot silhouette (all mm)."""
    def base(z):
        return bottom_r + (top_r - bottom_r) * (z / height)

    if kind == "Straight":
        return base
    if kind == "Barrel":
        return lambda z: base(z) + bulge * np.sin(np.pi * z / height)
    if kind == "Bowl":
        return lambda z: base(z) + bulge * np.sin(np.pi * (z / height) ** 0.65)
    if kind == "Hourglass":
        return lambda z: base(z) - bulge * np.sin(np.pi * z / height)
    raise ValueError(f"Unknown profile: {kind}")


def cross_section_multiplier(theta, kind):
    """Radius multiplier turning the circular cross-section into a rounded
    square or triangle (flats stay at the profile radius; corners bulge).
    Corners are rounded by circular smoothing of the exact polygon radius."""
    if kind in (None, "Round"):
        return np.ones_like(theta)
    n = 4 if kind == "Square" else 3
    a = theta % (2.0 * np.pi / n)
    mult = 1.0 / np.cos(a - np.pi / n)
    from scipy.ndimage import uniform_filter1d
    window = max(3, int(len(theta) / n * 0.30))
    mult = uniform_filter1d(mult, window, mode="wrap")
    mult = uniform_filter1d(mult, window, mode="wrap")
    return mult


def build_pot(params: dict) -> np.ndarray:
    """Returns (n, 3, 3) triangle array in mm. See generate.py for params."""
    height = params["height"]
    wall = params["wall_thickness"]
    base = params["base_thickness"]
    bottom_r = params["bottom_diameter"] / 2.0
    top_r = params["top_diameter"] / 2.0
    hole_r = params.get("drainage_hole_diameter", 0.0) / 2.0
    n_th = params["segments_around"]
    n_z = params["segments_vertical"]

    if hole_r > 0.1 and hole_r > bottom_r - 4.0:
        raise ValueError("Drainage hole must be at least 8mm smaller than the "
                         "bottom diameter (the floor needs a printable ring).")

    profile = profile_function(params.get("profile", "Straight"),
                                bottom_r, top_r, height, params.get("bulge", 0.0))
    texture_fn = TEXTURES[params.get("texture", "None")]
    depth = params.get("texture_depth", 1.5)
    scale = params.get("texture_scale", 1.0)

    twist_deg = params.get("texture_twist", 0.0)
    follow = params.get("interior", "Smooth") == "Follow Texture"
    mult = cross_section_multiplier(
        np.linspace(0.0, 2.0 * np.pi, n_th, endpoint=False),
        params.get("cross_section", "Round"))

    theta = np.linspace(0.0, 2.0 * np.pi, n_th, endpoint=False)
    mean_r = float(np.mean([profile(z) for z in np.linspace(0, height, 32)]))
    circumference = 2.0 * np.pi * mean_r

    def displaced(z_values):
        """Outer radius grid (rows, n_th) at the given heights: profile
        shaped by the cross-section, plus (optionally twisted) texture."""
        TH_g, Z_g = np.meshgrid(theta, z_values)
        u_g = TH_g / (2.0 * np.pi) * circumference
        if twist_deg:
            u_g = u_g + circumference * (twist_deg / 360.0) * (Z_g / height)
        disp_g = texture_fn(u_g, Z_g, circumference, depth, scale)
        fade = _smoothstep(Z_g / FADE_MM) * _smoothstep((height - Z_g) / FADE_MM)
        disp_g = disp_g * fade
        if not follow:
            disp_g = np.maximum(disp_g, -(wall - MIN_WALL_MM))  # protect the wall
        return profile(Z_g) * mult[None, :] + disp_g

    z_rows = np.linspace(0.0, height, n_z)
    r_outer = displaced(z_rows)

    inner_z = np.linspace(height, base, max(2, n_z // 2))
    if follow:
        # Interior tracks the textured outside at constant wall thickness -
        # deep sculptural textures flow through the whole wall.
        r_inner_rows = displaced(inner_z) - wall
    else:
        r_inner_rows = profile(inner_z)[:, None] * mult[None, :] - wall
    floor_clear = hole_r + 1.0 if hole_r > 0.1 else 1.5
    r_inner_rows = np.maximum(r_inner_rows, floor_clear)

    def ring(r_values, z_value):
        r_values = np.broadcast_to(r_values, theta.shape)
        return np.column_stack([r_values * np.cos(theta),
                                 r_values * np.sin(theta),
                                 np.full(n_th, z_value)])

    tris = []

    def strip(ring_a, ring_b, flip=False):
        a, b = ring_a, np.roll(ring_a, -1, axis=0)
        c, d = ring_b, np.roll(ring_b, -1, axis=0)
        t1 = np.stack([a, b, c], axis=1)
        t2 = np.stack([b, d, c], axis=1)
        if flip:
            t1, t2 = t1[:, ::-1], t2[:, ::-1]
        tris.append(t1)
        tris.append(t2)

    def fan(ring_pts, apex, flip=False):
        a, b = ring_pts, np.roll(ring_pts, -1, axis=0)
        t = np.stack([b, a, np.broadcast_to(apex, a.shape)], axis=1)
        if flip:
            t = t[:, ::-1]
        tris.append(t)

    # Outer wall, bottom to top.
    previous = ring(r_outer[0], z_rows[0])
    outer_bottom = previous
    for i in range(1, n_z):
        current = ring(r_outer[i], z_rows[i])
        strip(previous, current)
        previous = current
    outer_top = previous

    # Rim: outer top -> inner top.
    inner_top = ring(r_inner_rows[0], height)
    strip(outer_top, inner_top)

    # Inner wall, top down to the cavity floor.
    previous = inner_top
    for i in range(1, len(inner_z)):
        current = ring(r_inner_rows[i], inner_z[i])
        strip(previous, current)
        previous = current
    inner_bottom = previous

    if hole_r <= 0.1:
        fan(outer_bottom, np.array([0.0, 0.0, 0.0]))                  # bottom cap
        fan(inner_bottom, np.array([0.0, 0.0, base]), flip=True)      # cavity floor
    else:
        hole_bottom = ring(hole_r, 0.0)
        hole_top = ring(hole_r, base)
        strip(outer_bottom, hole_bottom, flip=True)   # bottom annulus (faces down)
        strip(hole_bottom, hole_top, flip=True)       # hole tube (faces inward)
        strip(hole_top, inner_bottom, flip=True)      # floor annulus (faces up)

    return np.concatenate(tris, axis=0)


def verify_mesh(tris: np.ndarray) -> dict:
    """Closed-manifold and orientation check. Cheap enough below ~500k tris."""
    flat = tris.reshape(-1, 3)
    quantized = np.round(flat / 1e-4).astype(np.int64)
    _, ids = np.unique(quantized, axis=0, return_inverse=True)
    face_ids = ids.reshape(-1, 3)

    edges = np.concatenate([face_ids[:, [0, 1]], face_ids[:, [1, 2]], face_ids[:, [2, 0]]])
    directed = {}
    bad = 0
    for e0, e1 in edges:
        key = (e0, e1)
        directed[key] = directed.get(key, 0) + 1
        if directed[key] > 1:
            bad += 1
    unmatched = sum(1 for (a, b) in directed if (b, a) not in directed)

    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    volume = float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)

    return {
        # closed: perfect 2-manifold, every edge shared by exactly 2 faces.
        "closed": bad == 0 and unmatched == 0,
        # watertight: no boundary edges - no holes. Marching-cubes output can
        # be watertight yet have a few "pinch" edges (4 faces sharing an
        # edge) where the surface self-touches at sub-voxel scale; slicers
        # repair those automatically on import.
        "watertight": unmatched == 0,
        "pinch_edges": bad,
        "unmatched_edges": unmatched,
        "volume_mm3": volume,
    }
