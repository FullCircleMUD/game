"""
WearableContainerNFTItem — a container that can be worn (e.g. panniers on a mule).

Inherits:
    ContainerMixin          — container capacity, weight propagation, display
    FungibleInventoryMixin  — gold/resource storage and transfers
    WearableNFTItem         — wearslot, wear_effects, durability
"""

from typeclasses.mixins.container import ContainerMixin
from typeclasses.mixins.fungible_inventory import FungibleInventoryMixin
from typeclasses.items.wearables.wearable_nft_item import WearableNFTItem


class WearableContainerNFTItem(ContainerMixin, FungibleInventoryMixin, WearableNFTItem):
    """
    A wearable container (panniers on a mule) that holds NFTs and fungibles.

    Prototype attributes:
        wearslot                  — WearSlot enum value
        wear_effects              — list of effect dicts (usually [])
        max_container_capacity_kg — float, maximum weight of contents
        transfer_weight           — bool, False for panniers (weight on mule,
                                    not on character leading the mule)
        weight                    — float, the container's own weight
        max_durability            — int, durability
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("container", category="item_type")
        self.at_container_init()
        self.at_fungible_init()
