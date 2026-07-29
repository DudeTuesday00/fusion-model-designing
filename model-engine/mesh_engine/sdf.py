"""Signed-distance-field modeling with marching-cubes meshing.

This is how organic shapes with smoothly blended parts are made (branching
coral, melted finger joints, boulder piles - and eventually creature bodies
with limbs that grow out of them). Each part is a mathematical distance
function; smooth-min unions melt parts together; marching cubes extracts one
seamless watertight mesh from the combined field.

Requires scikit-image on the system Python: pip install scikit-image
"""

import numpy as np

try:
    from .decor import noise3
except ImportError:  # running as a plain script via generate.py
    from decor import noise3

_FAR = 1.0e3  # placeholder distance for points outside a primitive's box


def _with_bounds(fn, lo, hi):
    fn.bounds = (np.asarray(lo, dtype=np.float64), np.asarray(hi, dtype=np.float64))
    return fn


# --- primitives (each returns fn(points (n,3)) -> distances (n,)) ----------

def capsule(a, b, radius):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    ba = b - a
    denom = float(ba @ ba) or 1e-12

    def fn(p):
        pa = p - a
        h = np.clip((pa @ ba) / denom, 0.0, 1.0)
        return np.linalg.norm(pa - np.outer(h, ba), axis=1) - radius
    return _with_bounds(fn, np.minimum(a, b) - radius, np.maximum(a, b) + radius)


def round_cone(a, b, r1, r2):
    """Tapered capsule: radius r1 at point a, r2 at point b (iq's exact SDF)."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    ba = b - a
    l2 = float(ba @ ba) or 1e-12
    rr = r1 - r2
    a2 = l2 - rr * rr
    il2 = 1.0 / l2

    def fn(p):
        pa = p - a
        y = pa @ ba
        z = y - l2
        d = pa * l2 - np.outer(y, ba)
        x2 = np.einsum("ij,ij->i", d, d)
        y2 = y * y * l2
        z2 = z * z * l2
        k = np.sign(rr) * rr * rr * x2
        far = np.sqrt(x2 + z2) * il2 - r2       # beyond the b end
        near = np.sqrt(x2 + y2) * il2 - r1      # before the a end
        side = (np.sqrt(np.maximum(x2 * a2 * il2, 0.0)) + y * rr) * il2 - r1
        result = side
        result = np.where(np.sign(z) * a2 * z2 > k, far, result)
        result = np.where(np.sign(y) * a2 * y2 < k, near, result)
        return result
    r_max = max(r1, r2)
    return _with_bounds(fn, np.minimum(a, b) - r_max, np.maximum(a, b) + r_max)


def torus(center, major_r, minor_r):
    """Torus lying flat (axis = Z) - e.g. an anchor ring on the print bed."""
    center = np.asarray(center, dtype=np.float64)

    def fn(p):
        q = p - center
        ring = np.hypot(q[:, 0], q[:, 1]) - major_r
        return np.hypot(ring, q[:, 2]) - minor_r
    reach = major_r + minor_r
    return _with_bounds(fn, center - [reach, reach, minor_r],
                         center + [reach, reach, minor_r])


def rounded_box(center, half_sizes, radius):
    center = np.asarray(center, dtype=np.float64)
    half = np.asarray(half_sizes, dtype=np.float64) - radius

    def fn(p):
        q = np.abs(p - center) - half
        outside = np.linalg.norm(np.maximum(q, 0.0), axis=1)
        inside = np.minimum(np.max(q, axis=1), 0.0)
        return outside + inside - radius
    return _with_bounds(fn, center - half - radius, center + half + radius)


def ellipsoid(center, radii):
    """Approximate ellipsoid SDF (good enough for blobby unions)."""
    center = np.asarray(center, dtype=np.float64)
    radii = np.asarray(radii, dtype=np.float64)

    def fn(p):
        q = p - center
        k0 = np.linalg.norm(q / radii, axis=1)
        k1 = np.linalg.norm(q / (radii * radii), axis=1)
        k1 = np.maximum(k1, 1e-12)
        return k0 * (k0 - 1.0) / k1
    return _with_bounds(fn, center - radii, center + radii)


# --- combination -------------------------------------------------------------

def _smin(d1, d2, k):
    h = np.clip(0.5 + 0.5 * (d2 - d1) / k, 0.0, 1.0)
    return d2 * (1.0 - h) + d1 * h - k * h * (1.0 - h)


class Scene:
    """A pile of primitives blended with smooth-min, plus optional surface
    noise (adds organic skin detail to everything at once).

    Each primitive is only evaluated on grid points inside its own bounding
    box (plus a safety margin) - with a hundred branches, this is the
    difference between minutes and seconds per mesh.
    """

    def __init__(self, blend_mm=3.0, noise_amp=0.0, noise_cell=8.0, seed=1):
        self.prims = []
        self.blend = blend_mm
        self.noise_amp = noise_amp
        self.noise_cell = noise_cell
        self.seed = seed

    def add(self, prim_fn):
        self.prims.append(prim_fn)

    def eval(self, points):
        margin = self.blend * 2.5 + self.noise_amp + 4.0
        d = np.full(len(points), _FAR)
        for prim in self.prims:
            lo, hi = prim.bounds
            mask = np.all((points >= lo - margin) & (points <= hi + margin), axis=1)
            if not mask.any():
                continue
            dp = np.full(len(points), _FAR)
            dp[mask] = prim(points[mask])
            d = _smin(dp, d, self.blend)
        if self.noise_amp > 0:
            # Noise only matters near the surface - skip the empty space.
            band = np.abs(d) < (self.noise_amp + 3.0)
            if band.any():
                d[band] += ((2.0 * noise3(points[band], self.noise_cell, self.seed)
                             - 1.0) * self.noise_amp)
        return d


# --- meshing -------------------------------------------------------------------

def mesh_scene(scene, bounds_min, bounds_max, voxel_mm):
    """Marching-cubes the scene into an (n, 3, 3) triangle array (mm)."""
    from skimage import measure

    bounds_min = np.asarray(bounds_min, dtype=np.float64)
    bounds_max = np.asarray(bounds_max, dtype=np.float64)
    counts = np.maximum(((bounds_max - bounds_min) / voxel_mm).astype(int) + 1, 2)

    xs = bounds_min[0] + np.arange(counts[0]) * voxel_mm
    ys = bounds_min[1] + np.arange(counts[1]) * voxel_mm
    zs = bounds_min[2] + np.arange(counts[2]) * voxel_mm

    volume = np.empty(counts, dtype=np.float32)
    # Evaluate in x-slabs to bound memory (each slab is ny*nz points).
    slab = max(1, int(4_000_000 / (counts[1] * counts[2])))
    Y, Z = np.meshgrid(ys, zs, indexing="ij")
    for start in range(0, counts[0], slab):
        stop = min(start + slab, counts[0])
        pts = []
        for i in range(start, stop):
            X = np.full_like(Y, xs[i])
            pts.append(np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1))
        block = np.concatenate(pts, axis=0)
        values = scene.eval(block).astype(np.float32)
        volume[start:stop] = values.reshape(stop - start, counts[1], counts[2])

    verts, faces, _, _ = measure.marching_cubes(volume, level=0.0,
                                                 spacing=(voxel_mm,) * 3)
    verts = verts + bounds_min

    # Marching cubes emits degenerate slivers where the surface crosses a
    # grid corner exactly - triangles whose corners coincide. Their edges
    # self-cancel, so dropping them keeps the mesh closed and makes it clean.
    quantized = np.round(verts / 1e-6).astype(np.int64)
    _, vert_ids = np.unique(quantized, axis=0, return_inverse=True)
    face_ids = vert_ids[faces]
    good = ((face_ids[:, 0] != face_ids[:, 1])
            & (face_ids[:, 1] != face_ids[:, 2])
            & (face_ids[:, 2] != face_ids[:, 0]))
    tris = verts[faces[good]]

    # Ensure outward winding (marching cubes' orientation varies by convention).
    signed_volume = np.einsum("ij,ij->i", tris[:, 0],
                               np.cross(tris[:, 1], tris[:, 2])).sum() / 6.0
    if signed_volume < 0:
        tris = tris[:, ::-1]
    return np.ascontiguousarray(tris)


def bounds_for_points(points, margin_mm):
    """Axis-aligned bounds around (n,3) skeleton/center points + margin."""
    points = np.asarray(points, dtype=np.float64)
    return points.min(axis=0) - margin_mm, points.max(axis=0) + margin_mm
