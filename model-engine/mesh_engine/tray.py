"""Mesh drip trays and display bowls that match the textured planters.

Two styles built by one surface machine:
- Saucer: a shallow flared dish with an optional raised seat ring on the
  floor (the pot sits proud of collected water).
- Tilted Bowl: the sculptural slant-rim display bowl - rim high at the back
  sweeping low at the front - that a pot nests inside.

Both take the same texture library as the pots (plus twist), so a tray can
carry exactly its planter's pattern.
"""

import numpy as np

try:
    from .surface import FADE_MM, MIN_WALL_MM, cross_section_multiplier
    from .textures import TEXTURES, _smoothstep
except ImportError:  # running as a plain script via generate.py
    from surface import FADE_MM, MIN_WALL_MM, cross_section_multiplier
    from textures import TEXTURES, _smoothstep


def build_tray(params):
    style = params.get("style", "Saucer")
    pot_r = params["pot_bottom_diameter"] / 2.0
    clearance = params.get("clearance", 3.0)
    height = params["height"]
    tilt = params.get("tilt_percent", 0.0) / 100.0
    wall = params["wall_thickness"]
    base = params["base_thickness"]
    seat_ring = bool(params.get("seat_ring", True))
    n_th = params["segments_around"]
    n_z = max(48, params["segments_vertical"] // 4)

    texture_fn = TEXTURES[params.get("texture", "None")]
    depth = params.get("texture_depth", 1.5)
    scale = params.get("texture_scale", 1.0)
    twist_deg = params.get("texture_twist", 0.0)

    floor_r = pot_r + clearance          # interior floor radius
    outer_floor_r = floor_r + wall
    if style == "Tilted Bowl":
        rim_gain = height * 0.60         # bowls belly outward as they rise
        curve = lambda t: np.sin(t * np.pi / 2.0) ** 0.75
    else:
        rim_gain = height * 0.42         # gentle saucer flare (~23 degrees)
        curve = lambda t: t

    def outer_profile(z):
        t = np.clip(z / height, 0.0, 1.0)
        return outer_floor_r + rim_gain * curve(t)

    theta = np.linspace(0.0, 2.0 * np.pi, n_th, endpoint=False)
    # Same cross-section math as the pots, so a triangle tray hugs a
    # triangle pot with uniform clearance (both scale from the same curve).
    mult = cross_section_multiplier(theta, params.get("cross_section", "Round"))
    # Rim height per column: full at the back (theta=pi), dropped at front.
    z_rim = height * (1.0 - tilt * (0.5 + 0.5 * np.cos(theta)))
    z_rim = np.maximum(z_rim, base + 3.0)

    mean_r = float(outer_profile(height * 0.6))
    circumference = 2.0 * np.pi * mean_r

    def displaced(z_grid):
        TH_g = np.broadcast_to(theta, z_grid.shape)
        u_g = TH_g / (2.0 * np.pi) * circumference
        if twist_deg:
            u_g = u_g + circumference * (twist_deg / 360.0) * (z_grid / height)
        disp = texture_fn(u_g, z_grid, circumference, depth, scale)
        fade = (_smoothstep(z_grid / FADE_MM)
                * _smoothstep((z_rim[None, :] - z_grid) / FADE_MM))
        disp = disp * fade
        return np.maximum(disp, -(wall - MIN_WALL_MM))

    t_rows = np.linspace(0.0, 1.0, n_z)
    z_outer = t_rows[:, None] * z_rim[None, :]
    r_outer = outer_profile(z_outer) * mult[None, :] + displaced(z_outer)

    tris = []

    def ring(r_row, z_row):
        r_row = np.broadcast_to(r_row, theta.shape)
        z_row = np.broadcast_to(z_row, theta.shape)
        return np.column_stack([r_row * np.cos(theta),
                                 r_row * np.sin(theta), z_row])

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

    # Outer wall, bottom to rim.
    previous = ring(r_outer[0], z_outer[0])
    outer_bottom = previous
    for i in range(1, n_z):
        current = ring(r_outer[i], z_outer[i])
        strip(previous, current)
        previous = current
    outer_top = previous

    # Rim band across the wall thickness (follows the tilt).
    inner_rim_r = outer_profile(z_rim) * mult - wall
    inner_top = ring(inner_rim_r, z_rim)
    strip(outer_top, inner_top)

    # Smooth inner wall down to the floor.
    t_inner = np.linspace(1.0, 0.0, max(24, n_z // 2))
    previous = inner_top
    for t_val in t_inner[1:]:
        z_row = base + t_val * (z_rim - base)
        current = ring(outer_profile(z_row) * mult - wall, z_row)
        strip(previous, current)
        previous = current
    inner_bottom = previous  # at z=base, radius ~ floor_r (shaped)

    # Floor, optionally with a raised seat ring the pot rests on.
    if seat_ring:
        seat_out = min(pot_r * 0.78 + 3.0, floor_r - 2.0)
        seat_in = max(seat_out - 6.0, 3.0)
        seat_h = 2.5
        floor_rings = [
            (max(floor_r - 0.01, seat_out + 1.0), base),
            (seat_out, base),
            (seat_out, base + seat_h),
            (seat_in, base + seat_h),
            (seat_in, base),
        ]
        previous = inner_bottom
        for (r_val, z_val) in floor_rings:
            current = ring(r_val * mult, z_val)  # seat follows the pot's shape
            # Traversal here runs outer->inner - the opposite of build_pot's
            # floor annulus - so no flip is needed for upward-facing floor.
            strip(previous, current, flip=False)
            previous = current
        fan(previous, np.array([0.0, 0.0, base]), flip=True)
    else:
        fan(inner_bottom, np.array([0.0, 0.0, base]), flip=True)

    # Bottom cap.
    fan(outer_bottom, np.array([0.0, 0.0, 0.0]))

    return np.concatenate(tris, axis=0)
