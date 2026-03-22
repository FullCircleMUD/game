"""
ContainerNFTItem — a takeable NFT container that holds items and fungibles.

Examples: leather backpack, sack, pouch, quiver.

Inherits:
    ContainerMixin   — container capacity, weight propagation, display
    FungibleInventoryMixin — gold/resource storage and transfers
    BaseNFTItem      — NFT identity, mirror hooks, takeability
"""

from typeclasses.mixins.container import ContainerMixin
from typeclasses.mixins.fungible_inventory import FungibleInventoryMixin
from typeclasses.mixins.durability import DurabilityMixin
from typeclasses.items.base_nft_item import BaseNFTItem


class ContainerNFTItem(ContainerMixin, FungibleInventoryMixin, DurabilityMixin, BaseNFTItem):
    """
    A takeable container (backpack, sack, etc.) that holds NFTs and fungibles.

    Prototype attributes:
        max_container_capacity_kg — float, maximum weight of contents
        transfer_weight           — bool, True = contents weight counts
                                    against carrier
        weight                    — float, the container's own weight
        max_durability            — int, durability (0 = unbreakable)
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("container", category="item_type")
        self.at_container_init()
        self.at_fungible_init()
        self.at_durability_init()
