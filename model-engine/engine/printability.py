"""Shared printability checks for generators.

Raise ValueError with a clear, actionable message when parameters would
produce a weak or unprintable FDM part. Generators can call these before
building geometry.
"""

from .units import mm

# Practical FDM floors for typical 0.4 mm nozzles.
MIN_WALL_MM = 1.2
MIN_FEATURE_MM = 1.0
MIN_HOLE_MM = 2.0


def require_wall_thinner_than_radius(wall_mm: float, radius_mm: float,
                                     label: str = "wall") -> None:
    if wall_mm >= radius_mm:
        raise ValueError(
            f"{label.capitalize()} thickness ({wall_mm:.1f} mm) must be less than "
            f"half the smallest width/diameter ({radius_mm * 2:.1f} mm)."
        )


def require_min_wall(wall_mm: float, minimum_mm: float = MIN_WALL_MM) -> None:
    if wall_mm < minimum_mm:
        raise ValueError(
            f"Wall thickness ({wall_mm:.1f} mm) is below the recommended "
            f"FDM minimum of {minimum_mm:.1f} mm."
        )


def require_base_below_height(base_mm: float, height_mm: float,
                               base_label: str = "Base thickness",
                               height_label: str = "height") -> None:
    if base_mm >= height_mm:
        raise ValueError(
            f"{base_label} ({base_mm:.1f} mm) must be less than the "
            f"{height_label} ({height_mm:.1f} mm)."
        )


def require_feature_fits_ring(count: int, ring_radius_mm: float,
                               feature_radius_mm: float, gap_mm: float = 1.0,
                               feature_name: str = "features") -> None:
    """Ensures evenly spaced features on a ring don't overlap."""
    if count < 2:
        return
    import math
    spacing = 2.0 * ring_radius_mm * math.sin(math.pi / count)
    if spacing < feature_radius_mm * 2.0 + gap_mm:
        raise ValueError(
            f"Too many {feature_name} to fit - reduce the count or size."
        )


def require_positive(value: float, label: str) -> None:
    if value <= 0:
        raise ValueError(f"{label} must be greater than zero.")


def leftover_wall_after_relief(wall_mm: float, depth_mm: float,
                                min_leftover_mm: float = 1.2) -> None:
    if depth_mm >= wall_mm - min_leftover_mm:
        raise ValueError(
            f"Relief/texture depth ({depth_mm:.1f} mm) would leave the wall "
            f"thinner than {min_leftover_mm:.1f} mm - reduce the depth or "
            f"thicken the wall."
        )
