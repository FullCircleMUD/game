"""
Owned command — lists all player-owned large objects (ships, mounts, pets,
property) and their current in-world location.

Usage:
    owned

These objects live in your character record for ownership tracking but do not
appear in your inventory. They have their own specialised commands for
interaction (sail, mount, etc.).
"""

from evennia import Command

from commands.command import FCMCommandMixin
from typeclasses.items.untakeables.world_anchored_nft_item import WorldAnchoredNFTItem


class CmdOwned(FCMCommandMixin, Command):
    """
    List your owned objects (ships, mounts, pets, property).

    Usage:
        owned

    Shows large objects you own — ships, mounts, pets, property — and where
    they currently are in the world. These do not appear in your inventory.
    """

    key = "owned"
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller
        owned = [obj for obj in caller.contents if isinstance(obj, WorldAnchoredNFTItem)]

        if not owned:
            caller.msg("You don't own any ships, mounts, or property.")
            return

        lines = ["\n|wOwned Objects:|n\n"]
        for obj in owned:
            if hasattr(obj, "get_owned_display"):
                lines.append(obj.get_owned_display())
            else:
                loc = obj.get_world_location_display() if hasattr(obj, "get_world_location_display") else "unknown"
                lines.append(f"  {obj.key} — {loc}")

        caller.msg("\n".join(lines))
