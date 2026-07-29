"""Importing this package registers every generator module below.

To add a new generator: create a module in this folder, define a Generator
subclass in it decorated with @registry.register, then import that module
here. Nothing else needs to change - the UI discovers generators through
registry.list_all().

The example_cylinder module is intentionally not imported so the placeholder
stays out of the Object Type dropdown in normal use. Keep the file as a
minimal reference for writing new generators.
"""

from . import planter_basic  # noqa: F401
from . import planter_drip_tray  # noqa: F401
from . import planter_drip_tray_textured  # noqa: F401
from . import planter_stand  # noqa: F401
from . import planter_stand_cross  # noqa: F401
from . import planter_tray_mesh  # noqa: F401
from . import planter_insert  # noqa: F401
from . import planter_textured  # noqa: F401
from . import planter_with_tray  # noqa: F401
from . import aquarium_treasure_chest  # noqa: F401
from . import aquarium_castle_tower  # noqa: F401
from . import aquarium_mesh_decor  # noqa: F401
from . import creature_axolotl  # noqa: F401
from . import keychain_tag  # noqa: F401
from . import scoop_turned  # noqa: F401
from . import scoop_loop_handle  # noqa: F401
