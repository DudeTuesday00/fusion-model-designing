"""Texture displacement functions for the mesh backend.

Every texture is a function f(u, v, depth, scale) -> displacement in mm,
where:
  u = arc length around the pot in mm (0 .. circumference), computed from a
      mean radius so pattern cells stay roughly square regardless of pot size
  v = height in mm (0 at the pot bottom)
Textures are periodic in u (the pattern must tile seamlessly around the pot),
which every function below guarantees by sizing cells from `wrap_cells`.

depth scales the bump height; scale multiplies pattern density (2.0 = twice
as fine, 0.5 = twice as chunky). Displacements should be mostly positive
(outward); the surface builder clamps inward excursions to protect the wall.
"""

import numpy as np

TWO_PI = 2.0 * np.pi


def _smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def _cells(u, circumference, target_mm):
    """Splits the circumference into a whole number of cells near target_mm
    wide (so the pattern tiles), returning (cell_coordinate, cell_count)."""
    count = max(3, int(round(circumference / target_mm)))
    return u / circumference * count, count


def _value_noise(uc, vc, gu, gv, seed=7, octaves=3):
    """Periodic-in-u fractal value noise. uc in [0,gu), vc in cell units."""
    total = np.zeros_like(uc)
    amp = 1.0
    norm = 0.0
    for octave in range(octaves):
        mult = 2 ** octave
        g_u, g_v = gu * mult, gv * mult
        rng = np.random.default_rng(seed + octave * 101)
        grid = rng.random((g_v + 2, g_u))
        x = (uc * mult) % g_u
        y = np.clip(vc * mult, 0, g_v)
        ix0 = x.astype(int) % g_u
        ix1 = (ix0 + 1) % g_u
        iy0 = np.clip(y.astype(int), 0, g_v)
        iy1 = np.clip(iy0 + 1, 0, g_v + 1)
        fx = _smoothstep(x - np.floor(x))
        fy = _smoothstep(y - np.floor(y))
        n00 = grid[iy0, ix0]; n10 = grid[iy0, ix1]
        n01 = grid[iy1, ix0]; n11 = grid[iy1, ix1]
        total += amp * ((n00 * (1 - fx) + n10 * fx) * (1 - fy)
                        + (n01 * (1 - fx) + n11 * fx) * fy)
        norm += amp
        amp *= 0.5
    return total / norm


def _staggered_grid(u, v, circumference, cell_w, cell_h, stagger=0.5):
    """Returns (du, dv) distances from each point to its nearest bump center
    on a staggered grid, in units of half-cell (so 1.0 = cell edge)."""
    uc, _ = _cells(u, circumference, cell_w)
    vc = v / cell_h
    row = np.floor(vc)
    uc_off = uc + (row % 2) * stagger
    du = (uc_off - np.floor(uc_off)) - 0.5
    dv = (vc - row) - 0.5
    return du * 2.0, dv * 2.0


# --- texture library -------------------------------------------------------

def none(u, v, circumference, depth, scale):
    return np.zeros_like(u)


def knurl(u, v, circumference, depth, scale):
    """Diamond knurl dots (like 130.stl, 150mm (2).stl)."""
    uc, _ = _cells(u, circumference, 7.0 / scale)
    vc = v / (7.0 / scale)
    a = np.sin(np.pi * (uc + vc)) * np.sin(np.pi * (uc - vc))
    return depth * np.clip(a, 0.0, None) ** 1.2


def scales(u, v, circumference, depth, scale):
    """Staggered quilted scale domes (like small.stl, 175.stl)."""
    du, dv = _staggered_grid(u, v, circumference, 12.0 / scale, 7.5 / scale)
    d2 = du ** 2 + dv ** 2
    return depth * np.clip(1.0 - d2, 0.0, None) ** 1.3


def pinecone(u, v, circumference, depth, scale):
    """Pointed shingles - scale rows with a downward-pointing tip."""
    uc, _ = _cells(u, circumference, 13.0 / scale)
    vc = v / (9.0 / scale)
    row = np.floor(vc)
    uf = (uc + (row % 2) * 0.5) % 1.0
    vf = vc - row
    across = np.sin(np.pi * uf) ** 1.6
    updown = _smoothstep(vf / 0.55) * (1.0 - _smoothstep((vf - 0.55) / 0.45)) ** 0.7
    return depth * across * updown


def pleats(u, v, circumference, depth, scale):
    """Smooth twisted lobes (like 140mm.stl, 160mm.stl, top.stl).
    Use a big depth (4-8mm) for the sculptural look."""
    count = max(3, int(round(circumference / (42.0 / scale))))
    height_span = np.max(v) - np.min(v) + 1e-9
    twist = 0.6 * TWO_PI * (v - np.min(v)) / height_span
    return depth * 0.5 * (1.0 + np.sin(count * (u / circumference * TWO_PI) + twist))


def pills(u, v, circumference, depth, scale):
    """Tire-tread pill bumps in slanted rows (like 140+x+140mm.stl)."""
    slant_v = v * 0.45
    du, dv = _staggered_grid(u + slant_v, v, circumference, 22.0 / scale, 12.0 / scale)
    # Pill = superellipse dome, wider than tall.
    e = np.abs(du / 0.85) ** 4 + np.abs(dv / 0.62) ** 4
    return depth * np.clip(1.0 - e, 0.0, None) ** 1.4


def bark(u, v, circumference, depth, scale):
    """Vertical ridged bark striations (like 64mm.stl)."""
    uc, gu = _cells(u, circumference, 9.0 / scale)
    vc = v / 34.0  # tall cells -> vertically stretched streaks
    n = _value_noise(uc, vc, gu, max(2, int(np.max(vc)) + 1), seed=11)
    fine = _value_noise(uc * 3.0, vc * 2.0, gu * 3, max(2, int(np.max(vc) * 2) + 1), seed=23)
    ridged = 1.0 - np.abs(2.0 * n - 1.0)
    return depth * (0.75 * ridged ** 1.6 + 0.25 * fine)


def bubbles(u, v, circumference, depth, scale):
    """Packed hemispherical pebbles (like large.stl)."""
    du, dv = _staggered_grid(u, v, circumference, 13.0 / scale, 11.5 / scale)
    d2 = du ** 2 + dv ** 2
    return depth * np.sqrt(np.clip(1.0 - d2 * 0.95, 0.0, None))


def drips(u, v, circumference, depth, scale):
    """Teardrop drops in rows (like 150mm+diameter.stl)."""
    du, dv = _staggered_grid(u, v, circumference, 16.0 / scale, 16.0 / scale)
    # Stretch the lower half of each bump downward into a tail.
    dv_shaped = np.where(dv < 0, dv * 0.55, dv * 1.35)
    d2 = du ** 2 + dv_shaped ** 2
    return depth * np.clip(1.0 - d2, 0.0, None) ** 1.2


def pinstripe(u, v, circumference, depth, scale):
    """Fine vertical ribs (like 136+x+96+solid+print.stl)."""
    uc, _ = _cells(u, circumference, 3.2 / scale)
    return depth * (0.5 + 0.5 * np.sin(TWO_PI * uc)) ** 2.2


def lobes(u, v, circumference, depth, scale):
    """Few large smooth organic lobes (like 160mm.stl). Big depth advised."""
    count = max(3, int(round(circumference / (70.0 / scale))))
    height_span = np.max(v) - np.min(v) + 1e-9
    t = (v - np.min(v)) / height_span
    twist = 0.9 * np.pi * t
    wave = np.sin(count * (u / circumference * TWO_PI) + twist)
    # sharpen the valleys, keep crests smooth - reads as tucked fabric
    return depth * (0.5 + 0.5 * wave) ** 1.6


def shingles(u, v, circumference, depth, scale):
    """True overlapping-scale look (like pinecone/dragon-scale pots).

    Each scale is a dome across its cell that ramps outward toward its
    DOWNWARD tip, then steps sharply back where the next row tucks under -
    the sawtooth reads as real overlap without needing undercuts (which a
    displacement surface can't express, and which the reference models
    don't actually have either)."""
    cell_w = 24.0 / scale
    cell_h = 15.0 / scale
    uc, _ = _cells(u, circumference, cell_w)
    vc = v / cell_h
    row = np.floor(vc)
    vf = vc - row                       # 0 at the scale's tip, 1 tucked under
    uf = (uc + (row % 2) * 0.5) % 1.0   # staggered like roof shingles
    across = np.sqrt(np.clip(1.0 - (2.0 * uf - 1.0) ** 2, 0.0, None))
    # Quarter-ellipse profile: domed and proud at the tip, tucking steeply
    # under the row above - reads as a fat overlapping pinecone scale.
    bulge = np.sqrt(np.clip(1.0 - vf ** 2, 0.0, None))
    return depth * across ** 0.85 * bulge


def arcs(u, v, circumference, depth, scale):
    """Art-deco fans: concentric arc ridges rising from staggered centers,
    laid over a fine pinstripe background (like the 'arcs' designer pots).
    max() keeps the fans sitting ON the stripes instead of adding."""
    # Background: fine vertical pinstripe at ~35% of the fan depth.
    stripe_c, _ = _cells(u, circumference, 3.2 / scale)
    stripes = 0.35 * depth * (0.5 + 0.5 * np.sin(TWO_PI * stripe_c)) ** 2.0

    # Fans: staggered cells, each with rings radiating from its bottom center.
    cell_w = 46.0 / scale
    cell_h = 30.0 / scale
    uc, nu = _cells(u, circumference, cell_w)
    cell_w_mm = circumference / nu
    vc = v / cell_h
    row = np.floor(vc)
    uf = (uc + (row % 2) * 0.5) % 1.0
    vf = vc - row
    du = (uf - 0.5) * cell_w_mm
    dv = vf * cell_h
    dist = np.hypot(du, dv)
    rings = np.sin(TWO_PI * dist / (5.0 / scale)) ** 2
    mask = _smoothstep((cell_h * 0.92 - dist) / 2.0)
    fans = depth * rings * mask
    return np.maximum(stripes, fans)


def _lattice_local(u, v, circumference, cell_w):
    """Offsets (du, dv, W) in mm from each point to its nearest hexagonal
    lattice center (rows staggered half a cell, spaced 0.866*W)."""
    uc, nu = _cells(u, circumference, cell_w)
    W = circumference / nu
    Rh = W * 0.866
    vc = v / Rh
    best_d2 = None
    best_du = best_dv = None
    base_row = np.floor(vc)
    for row_off in (0.0, 1.0):
        row = base_row + row_off
        stagger = (row % 2) * 0.5
        col = np.round(uc - stagger)
        du = (uc - stagger - col) * W
        dv = (vc - row) * Rh
        d2 = du * du + dv * dv
        if best_d2 is None:
            best_d2, best_du, best_dv = d2, du, dv
        else:
            closer = d2 < best_d2
            best_du = np.where(closer, du, best_du)
            best_dv = np.where(closer, dv, best_dv)
            best_d2 = np.minimum(d2, best_d2)
    return best_du, best_dv, W


def hearts(u, v, circumference, depth, scale):
    """Embossed hearts in staggered rows over a faint pinstripe field
    (like the 'cuore' planter)."""
    du, dv = _staggered_grid(u, v, circumference, 34.0 / scale, 30.0 / scale)
    x = du * 1.5
    y = -dv * 1.4
    # Crisp cartoon heart: a 45-degree diamond with two circular lobes on
    # its upper edges (the cubic implicit heart's cleft is too subtle to
    # read once embossed).
    diamond = np.abs(x) + np.abs(y + 0.15) - 0.65
    lobe_r = np.hypot(x - 0.325, y - 0.175) - 0.46
    lobe_l = np.hypot(x + 0.325, y - 0.175) - 0.46
    inside = np.minimum(diamond, np.minimum(lobe_r, lobe_l))
    heart = _smoothstep(-inside / 0.09)
    stripe_c, _ = _cells(u, circumference, 3.4 / scale)
    stripes = 0.30 * (0.5 + 0.5 * np.sin(TWO_PI * stripe_c)) ** 2
    return depth * np.maximum(heart, stripes)


def honeycomb(u, v, circumference, depth, scale):
    """Raised honeycomb cell walls (like the honey pot)."""
    du, dv, W = _lattice_local(u, v, circumference, 17.0 / scale)
    inradius = W / 2.0
    hexd = np.maximum(np.abs(du),
                       np.maximum(np.abs(du * 0.5 + dv * 0.866),
                                   np.abs(du * 0.5 - dv * 0.866))) / inradius
    return depth * _smoothstep((hexd - 0.74) / 0.16)


def triangle_ribs(u, v, circumference, depth, scale):
    """Sharp full-height sawtooth ribs - a star-prism cross-section look."""
    uc, _ = _cells(u, circumference, 12.0 / scale)
    frac = uc % 1.0
    return depth * (1.0 - 2.0 * np.abs(frac - 0.5))


def weave(u, v, circumference, depth, scale):
    """Two crossing families of diagonal ribbons, lattice-woven (like the
    'salir' planter)."""
    uc, _ = _cells(u, circumference, 26.0 / scale)
    vc = v / (26.0 / scale)
    ribbon1 = np.sin(np.pi * ((uc + vc) % 1.0)) ** 1.3
    ribbon2 = np.sin(np.pi * ((uc - vc) % 1.0)) ** 1.3
    return depth * np.maximum(ribbon1, ribbon2)


def y_tiles(u, v, circumference, depth, scale):
    """Interlocking Y tessellation (like the 'Y Shaped Pot'): three rounded
    bars radiating from each hex lattice center."""
    du, dv, W = _lattice_local(u, v, circumference, 20.0 / scale)
    arm_len = 0.52 * W
    bar_w = 0.17 * W
    min_dist = None
    for (ex, ey) in ((0.0, 1.0), (-0.866, -0.5), (0.866, -0.5)):
        t = np.clip(du * ex + dv * ey, 0.0, arm_len)
        dist = np.hypot(du - ex * t, dv - ey * t)
        min_dist = dist if min_dist is None else np.minimum(min_dist, dist)
    return depth * _smoothstep((bar_w - min_dist) / (bar_w * 0.35))


def soft_cutout(u, v, circumference, depth, scale):
    """Big smooth staggered indents - deep sculptural concavities. Pair with
    Interior = Follow Texture so the whole wall flows instead of thinning."""
    du, dv = _staggered_grid(u, v, circumference, 58.0 / scale, 46.0 / scale)
    d2 = du * du + dv * dv
    return -depth * np.clip(1.0 - d2, 0.0, None) ** 1.5


TEXTURES = {
    "None": none,
    "Knurl": knurl,
    "Scales": scales,
    "Pinecone": pinecone,
    "Pleats": pleats,
    "Pills": pills,
    "Bark": bark,
    "Bubbles": bubbles,
    "Drips": drips,
    "Pinstripe": pinstripe,
    "Lobes": lobes,
    "Shingles": shingles,
    "Arcs": arcs,
    "Hearts": hearts,
    "Honeycomb": honeycomb,
    "Triangle Ribs": triangle_ribs,
    "Weave": weave,
    "Y-Tiles": y_tiles,
    "Soft Cutout": soft_cutout,
}
