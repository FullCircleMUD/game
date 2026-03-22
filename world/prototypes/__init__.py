"""
FCM Item Prototypes — one file per item, organised by category.

Evennia discovers all prototypes via PROTOTYPE_MODULES = ["world.prototypes"].
Wildcard imports expose every prototype dict at the package level.
"""

from world.prototypes.weapons import *       # noqa: F401,F403
from world.prototypes.wearables import *    # noqa: F401,F403
from world.prototypes.holdables import *    # noqa: F401,F403
from world.prototypes.containers import *   # noqa: F401,F403
from world.prototypes.consumables import *  # noqa: F401,F403
from world.prototypes.components import *   # noqa: F401,F403
from world.prototypes.gems import *        # noqa: F401,F403
