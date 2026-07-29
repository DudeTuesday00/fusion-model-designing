"""Binary STL writer. Vectorized - handles millions of triangles in seconds."""

import struct

import numpy as np


def save_stl(path: str, tris: np.ndarray) -> None:
    """Writes tris (n, 3, 3) float array (mm) as binary STL."""
    n = len(tris)
    v1 = tris[:, 1] - tris[:, 0]
    v2 = tris[:, 2] - tris[:, 0]
    normals = np.cross(v1, v2)
    lengths = np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    normals = (normals / lengths).astype("<f4")

    record = np.zeros(n, dtype=np.dtype([
        ("normal", "<f4", 3), ("vertices", "<f4", (3, 3)), ("attr", "<u2"),
    ]))
    record["normal"] = normals
    record["vertices"] = tris.astype("<f4")

    with open(path, "wb") as f:
        f.write(b"Print Engine textured mesh".ljust(80, b" "))
        f.write(struct.pack("<I", n))
        record.tofile(f)
