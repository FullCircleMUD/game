"""
BaseNFTItem — Evennia object representing an NFT in the game world.

Each instance maps 1:1 to an NFTGameState row via token_id.
All NFT mirror/ownership updates are provided by NFTMirrorMixin.

Subclass hierarchy:
    BaseNFTItem (this class — never instantiate directly)
    ├── TakeableNFTItem    — items characters can get/drop/give/bank
    │   ├── WeaponNFTItem
    │   ├── ArmorNFTItem   (future)
    │   └── ...
    └── WorldAnchoredNFTItem  — items with specialised commands (mounts, pets, property)
        ├── ShipNFTItem
        └── ...

Usage (spawning items):
    from typeclasses.items.base_nft_item import BaseNFTItem

    token_id = BaseNFTItem.assign_to_blank_token("Iron Longsword")
    obj = BaseNFTItem.spawn_into(token_id, room)
"""

from evennia.objects.objects import DefaultObject
from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.mixins.hidden_object import HiddenObjectMixin
from typeclasses.mixins.height_aware_mixin import HeightAwareMixin
from typeclasses.mixins.item_restriction import ItemRestrictionMixin
from typeclasses.mixins.nft_mirror import NFTMirrorMixin


class BaseNFTItem(NFTMirrorMixin, HeightAwareMixin, HiddenObjectMixin, ItemRestrictionMixin, DefaultObject):
    """
    Base class for all NFT-backed items in the game world.

    NFT lifecycle (mirror tracking, ownership transitions, factory methods)
    is provided by NFTMirrorMixin. This class adds item-specific concerns:
    weight, identification, ground display, hidden-state visibility.
    """

    weight = AttributeProperty(0.0)
    identify_mastery_gate = AttributeProperty(1)  # tier required to identify (1=BASIC)
    ground_description = AttributeProperty("")  # e.g. "A rusty sword lies here."

    # ================================================================== #
    #  Evennia Hooks
    # ================================================================== #

    def at_object_creation(self):
        """Called once when the object is first created."""
        super().at_object_creation()
        self.at_hidden_init()
        # NOTE: get lock is NOT set here — subclasses determine takeability.
        # TakeableNFTItem inherits Evennia's default get:true().
        # WorldAnchoredNFTItem overrides with get:false().

    # ================================================================== #
    #  Display
    # ================================================================== #

    def is_visible_to(self, character):
        """Hidden-state visibility check for room display filtering."""
        return self.is_hidden_visible_to(character)

    def get_display_name(self, looker=None, **kwargs):
        """Include token ID for builders, plain name for players."""
        name = super().get_display_name(looker, **kwargs)
        if looker and self.locks.check_lockstring(looker, "perm(Builder)"):
            return f"{name} |w[NFT #{self.token_id}]|n"
        return name
