"""
UntakeableNFTItem — NFT items that CANNOT be picked up, dropped, or given
via standard inventory commands.

These are player-owned NFTs that exist in the game world but are not
carried in inventory. They have their own specialised commands for
acquisition and storage. Examples:

    Mounts:
        - Horse, Griffon, Dragon, etc.
        - Acquired/stored at stables (stable/collect commands)
        - Follow the character when active, stay at stable when stored

    Pets:
        - Hawk, Dog, etc.
        - Acquired/stored at specific locations (aviary, kennel)
        - Provide passive bonuses or combat assistance

    Property:
        - Private rooms, guild halls, ships
        - Acquired via purchase/deed mechanisms
        - Cannot be moved at all — tied to a location

    Decorative/Trophy:
        - Wall-mounted items, statues, etc.
        - Placed in owned rooms, cannot be carried

Standard get, drop, give, and junk commands will refuse to interact with
these items. Each subtype defines its own commands for moving the NFT
between game locations and the player's bank.

The bank may hold UntakeableNFTItems, but withdrawal is restricted by
subtype — a mount can only be withdrawn at a stable, a pet at a kennel, etc.
"""

from typeclasses.items.base_nft_item import BaseNFTItem


class UntakeableNFTItem(BaseNFTItem):
    """
    An NFT item that cannot be picked up, dropped, or given via standard
    inventory commands. Owned by a player but interacted with through
    specialised commands specific to the item subtype.

    Subclass for specific untakeable types:
        - MountNFTItem (future) — stable/collect at stables
        - PetNFTItem (future) — kennel/collect at kennels
        - PropertyNFTItem (future) — deeds, room ownership
        - ShipNFTItem (future) — dock/launch at shipyards
    """

    def at_object_creation(self):
        super().at_object_creation()
        # Override the base class get:true() lock — these items cannot be
        # picked up via the standard get command.
        self.locks.add("get:false()")

    def at_pre_get(self, getter, **kwargs):
        """Block standard pickup with a user-friendly message."""
        getter.msg(f"You can't pick up {self.get_display_name(getter)}.")
        return False

    def at_pre_drop(self, dropper, **kwargs):
        """Block standard drop with a user-friendly message."""
        dropper.msg(f"You can't drop {self.get_display_name(dropper)}.")
        return False

    def at_pre_give(self, giver, target, **kwargs):
        """Block standard give with a user-friendly message."""
        giver.msg(f"You can't give {self.get_display_name(giver)} to someone.")
        return False
