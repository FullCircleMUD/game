"""
MountNFTItem — NFT-backed mounts that characters can ride.

Mounts are untakeable NFT items that exist in the game world alongside
their owner character. They cannot be picked up, dropped, or given
via standard inventory commands.

Lifecycle:
    - Collected from a stable → mount spawns in the room,
      owner's active_mount is set to this object
    - Follows the owner as they move between rooms
    - Stored back at a stable → mount is banked, active_mount cleared
    - Can be banked/unbanked at stables only

Future:
    - Movement speed bonuses
    - Mounted combat modifiers
    - Mount-specific commands (mount, dismount, feed)
    - Only one active mount at a time (enforced by active_mount attribute)
    - Mount stamina / fatigue system
"""

from typeclasses.items.untakeables.untakeable_nft_item import UntakeableNFTItem


class MountNFTItem(UntakeableNFTItem):
    """
    An NFT mount that a character can ride.

    The mount exists as an object in the same room as its owner.
    The owning character's `active_mount` attribute points to this object.
    """

    def at_object_creation(self):
        super().at_object_creation()

    def at_post_move(self, source_location, move_type="move", **kwargs):
        """Called after the mount moves. Handles NFT mirror updates via parent."""
        super().at_post_move(source_location, move_type=move_type, **kwargs)
