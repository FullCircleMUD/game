"""
PetNFTItem — NFT-backed pets that follow their owner.

Pets are untakeable NFT items that exist in the game world alongside
their owner character. They cannot be picked up, dropped, or given
via standard inventory commands.

Lifecycle:
    - Collected from a kennel/aviary/etc. → pet spawns in the room,
      owner's active_pet is set to this object
    - Follows the owner as they move between rooms
    - Stored back at a kennel → pet is banked, active_pet cleared
    - Can be banked/unbanked at appropriate locations

Future:
    - Passive bonuses (e.g. hawk improves perception)
    - Combat assistance
    - Pet-specific commands (feed, train, etc.)
    - Only one active pet at a time (enforced by active_pet attribute)
"""

from typeclasses.items.untakeables.world_anchored_nft_item import WorldAnchoredNFTItem


class PetNFTItem(WorldAnchoredNFTItem):
    """
    An NFT pet that follows its owner in the game world.

    The pet exists as an object in the same room as its owner.
    The owning character's `active_pet` attribute points to this object.
    """

    def at_object_creation(self):
        super().at_object_creation()

    def at_post_move(self, source_location, move_type="move", **kwargs):
        """Called after the pet moves. Handles NFT mirror updates via parent."""
        super().at_post_move(source_location, move_type=move_type, **kwargs)
