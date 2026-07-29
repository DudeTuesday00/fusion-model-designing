"""Length-unit helpers. Fusion works in cm internally; dialogs use mm."""


def mm(value: float) -> float:
    """Converts millimeters to centimeters (Fusion's internal length unit)."""
    return value / 10.0


def cm_to_mm(value: float) -> float:
    """Converts centimeters (Fusion's internal length unit) back to millimeters."""
    return value * 10.0
