"""Drip tray sized for a Textured Planter (the mesh backend pots).

Textured pots bulge (Barrel/Bowl silhouettes) and carry texture bumps, so a
straight-flared tray can collide with them - the default Barrel pot swells
past a default tray's rim. This tray takes the SAME silhouette numbers you
entered for the Textured Planter, reconstructs the pot's true outer envelope
(profile + bulge + texture depth), and flares its wall automatically so the
pot always drops in with the requested clearance.

L-shaped support ribs work like the regular drip tray: feet lift the pot for
water collection; short vertical legs center it - sized against the textured
envelope, not the bare profile, so bumps don't wedge.
"""

import math

from .. import geometry_utils
from ..base import Generator, ParamSpec
from ..registry import register
from .planter_drip_tray import (_CENTERING_ENGAGE_MM, FOOT_PARAMS, RIM_PARAMS,
                                 add_feet, add_l_ribs, revolve_round_tray,
                                 scallop_rim)

# Matches mesh_engine/surface.py: texture fades in over this span (mm)
# above the pot's bottom, so the pot base itself is smooth.
_TEXTURE_FADE_MM = 3.0


def _smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


@register
class TexturedDripTray(Generator):
    id = "planter_drip_tray_textured"
    display_name = "Drip Tray for Textured Planter"
    category = "Planter"
    parameters = [
        # These first five should copy exactly what you entered for the pot.
        ParamSpec(name="profile", label="Pot Silhouette", type="choice", default="Barrel",
                  choices=["Straight", "Barrel", "Bowl", "Hourglass"]),
        ParamSpec(name="pot_bottom_diameter", label="Pot Bottom Diameter", type="float",
                  default=100.0, min=40.0, max=400.0, unit="mm"),
        ParamSpec(name="pot_top_diameter", label="Pot Top Diameter", type="float",
                  default=130.0, min=40.0, max=400.0, unit="mm"),
        ParamSpec(name="pot_height", label="Pot Height", type="float",
                  default=105.0, min=30.0, max=400.0, unit="mm"),
        ParamSpec(name="bulge", label="Pot Silhouette Bulge", type="float",
                  default=8.0, min=0.0, max=40.0, unit="mm"),
        ParamSpec(name="texture_depth", label="Pot Texture Depth", type="float",
                  default=1.8, min=0.0, max=10.0, unit="mm"),
        ParamSpec(name="cross_section", label="Pot Cross-Section", type="choice",
                  default="Round", choices=["Round", "Square", "Triangle"]),
        ParamSpec(name="clearance", label="Clearance Around Pot", type="float",
                  default=3.0, min=0.5, max=20.0, unit="mm"),
        ParamSpec(name="tray_height", label="Tray Height", type="float",
                  default=15.0, min=5.0, max=60.0, unit="mm"),
        ParamSpec(name="wall_thickness", label="Wall Thickness", type="float",
                  default=2.4, min=1.2, max=10.0, unit="mm"),
        ParamSpec(name="base_thickness", label="Base Thickness", type="float",
                  default=3.0, min=1.2, max=15.0, unit="mm"),
        ParamSpec(name="rib_count", label="Support Ribs", type="int",
                  default=4, min=0, max=8),
        ParamSpec(name="rib_width", label="Rib Width", type="float",
                  default=8.0, min=4.0, max=20.0, unit="mm"),
        ParamSpec(name="standoff_height", label="Standoff Height", type="float",
                  default=4.0, min=1.0, max=15.0, unit="mm"),
        ParamSpec(name="foot_length", label="Foot Length Under Pot", type="float",
                  default=12.0, min=5.0, max=40.0, unit="mm"),
        ParamSpec(name="centering_gap", label="Centering Gap", type="float",
                  default=1.0, min=0.2, max=5.0, unit="mm"),
    ] + RIM_PARAMS + FOOT_PARAMS

    def build(self, component, params: dict) -> None:
        mm = geometry_utils.mm
        bottom_r = mm(params["pot_bottom_diameter"]) / 2.0
        top_r = mm(params["pot_top_diameter"]) / 2.0
        pot_h = mm(params["pot_height"])
        bulge = mm(params["bulge"])
        tex_depth = mm(params["texture_depth"])
        clearance = mm(params["clearance"])
        height = mm(params["tray_height"])
        wall = mm(params["wall_thickness"])
        base = mm(params["base_thickness"])
        kind = params["profile"]

        if base >= height:
            raise ValueError("Base thickness must be less than the tray height.")

        def pot_radius(z_pot):
            z_pot = max(0.0, min(pot_h, z_pot))
            r = bottom_r + (top_r - bottom_r) * (z_pot / pot_h)
            t = z_pot / pot_h
            if kind == "Barrel":
                r += bulge * math.sin(math.pi * t)
            elif kind == "Bowl":
                r += bulge * math.sin(math.pi * t ** 0.65)
            elif kind == "Hourglass":
                r -= bulge * math.sin(math.pi * t)
            return r

        # Non-round pots bulge past the profile radius at their corners
        # (factors measured from the mesh engine's cross-section curves).
        corner_factor = {"Round": 1.0, "Square": 1.251, "Triangle": 1.550}[
            params["cross_section"]]

        def envelope(z_pot):
            """Pot's outermost radius at a height: profile at the widest
            corner + faded texture."""
            fade = _smoothstep(z_pot / mm(_TEXTURE_FADE_MM))
            return pot_radius(z_pot) * corner_factor + tex_depth * fade

        standoff_h = mm(params["standoff_height"])
        pot_lift = base + standoff_h  # pot bottom sits this high in tray coords

        # Interior: pot bottom + clearance at the floor, and enough room at
        # the rim for the lifted, bulged, textured pot to pass through.
        floor_r = envelope(0.0) + clearance
        rim_r = max(floor_r, envelope(height - pot_lift) + clearance)

        tray_body = revolve_round_tray(component, floor_r, rim_r, height, wall, base)

        if params["rim_finish"] == "Scalloped":
            scallop_rim(component, tray_body, rim_r + wall / 2.0, height)

        foot_angles = [2.0 * math.pi * i / params["foot_count"]
                       for i in range(params["foot_count"])]
        add_feet(component, tray_body, params, floor_r, wall, base, foot_angles)

        rib_count = params["rib_count"]
        if rib_count == 0:
            return
        if rib_count < 3:
            raise ValueError("Use at least 3 support ribs so the pot sits stable (or 0 for none).")

        rib_w = mm(params["rib_width"])
        foot_len = mm(params["foot_length"])
        gap = mm(params["centering_gap"])
        foot_top = pot_lift
        leg_top = foot_top + mm(_CENTERING_ENGAGE_MM)

        if leg_top > height:
            raise ValueError("Standoff height is too tall - the centering leg would "
                             "stick out above the tray rim. Reduce it or raise the tray height.")
        if foot_len >= bottom_r:
            raise ValueError("Foot length must be shorter than the pot's bottom radius.")

        # The centering legs press on the TEXTURED surface, so they clear the
        # envelope at their top, where the pot is widest within their reach.
        leg_inner_r = envelope(leg_top - pot_lift) + gap

        foot_in_r = bottom_r - foot_len
        if 2.0 * foot_in_r * math.sin(math.pi / rib_count) < rib_w + mm(1.0):
            raise ValueError("Too many ribs to fit - reduce the rib count or width.")

        # Bury rib ends in the sloped wall without poking out of the tray.
        wall_slope = (rim_r - floor_r) / max(height - base, 1e-6)
        r_out = floor_r + min((leg_top - base) * wall_slope + wall * 0.5, wall)
        if r_out <= leg_inner_r:
            r_out = leg_inner_r + wall * 0.5

        add_l_ribs(component, tray_body, rib_count, rib_w, foot_in_r,
                    leg_inner_r, r_out, foot_top, leg_top)
