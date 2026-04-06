"""
WorldAnchoredNFTItem — Base class for player-owned NFTs that are NOT carried
in inventory.

These objects live in character.contents for ownership tracking (full NFT
lifecycle applies — give, delete, bank, import/export all work normally)
but are invisible to `inventory` and `equipment` commands. They have zero
weight and a real in-world position tracked via `db.world_location`.

World-anchored patterns (location tracking, get/drop blocks, give allows)
are provided by OwnedWorldObjectMixin. NFT lifecycle is provided by
NFTMirrorMixin via BaseNFTItem.

Subtypes:
    ShipNFTItem — berthed at a dock room. Sailed to a new dock on arrival.
    MountNFTItem (future) — stabled at a stable room.
    PetNFTItem (future) — kennelled at a stable room.
    PropertyNFTItem (future) — tied to a room permanently.

Standard get/drop/give/junk commands refuse to interact with these items.
Use the `owned` command to list all owned objects and their world locations.
"""

from typeclasses.items.base_nft_item import BaseNFTItem
from typeclasses.mixins.owned_world_object import OwnedWorldObjectMixin


class WorldAnchoredNFTItem(OwnedWorldObjectMixin, BaseNFTItem):
    """
    An NFT item that lives in character.contents but is invisible to standard
    inventory/equipment commands.

    World-anchored patterns provided by OwnedWorldObjectMixin.
    NFT lifecycle provided by NFTMirrorMixin via BaseNFTItem.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.at_owned_world_object_init()
