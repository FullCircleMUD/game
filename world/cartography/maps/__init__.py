"""
Map definition files for the cartography system.

Each file registers a predefined ASCII map via register_map().
Import all map files here so their register_map() calls fire at import time.
"""
from world.cartography.maps import millholm_town  # noqa: F401
from world.cartography.maps import millholm_region  # noqa: F401
from world.cartography.maps import millholm_sewers  # noqa: F401
from world.cartography.maps import millholm_mine  # noqa: F401
