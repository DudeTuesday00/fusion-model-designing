"""Shared types every generator (planter, creature, aquarium decor, ...) builds on.

A generator describes what parameters it needs (ParamSpec list) and knows how
to turn a dict of parameter values into geometry (Generator.build). The UI
layer (engine/ui/command.py) is the only thing that knows about Fusion's
dialog widgets - generators never touch the UI directly, so a generator can
be tested/reasoned about independently of the dialog that feeds it.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParamSpec:
    """Describes one parameter a generator needs, so the UI can build an input for it."""

    name: str  # key used in the params dict passed to Generator.build
    label: str  # text shown next to the input in the dialog
    type: str  # "float" | "int" | "bool" | "choice" | "string"
    default: object
    min: Optional[float] = None
    max: Optional[float] = None
    unit: str = ""  # e.g. "mm" - only meaningful for float/int params
    choices: list = field(default_factory=list)  # only used when type == "choice"
    group: str = ""  # optional dialog subgroup title (e.g. "Feet", "Rim")


class Generator(ABC):
    """Base class for anything that can build a print-ready object.

    Subclasses set `id`, `display_name`, `category`, and `parameters` as
    class attributes, then implement build(). See
    engine/generators/example_cylinder.py for the simplest possible example
    (kept as a reference; not registered in normal builds).

    Set supports_preview = False for mesh/SDF backends that write files via
    subprocess - those must only run on OK, never during dialog preview.
    """

    id: str = ""
    display_name: str = ""
    category: str = ""  # e.g. "Planter", "Creature", "Aquarium Decor"
    parameters: list = []
    supports_preview: bool = True

    @abstractmethod
    def build(self, component, params: dict) -> None:
        """Create geometry inside `component` (an adsk.fusion.Component).

        `params` has one entry per ParamSpec.name, converted to the right
        Python type (float/int/bool/str), in the unit that ParamSpec named
        (e.g. "mm" for lengths) - NOT Fusion's internal cm. Use
        geometry_utils.mm() to convert when calling into the Fusion API.
        """
        raise NotImplementedError
