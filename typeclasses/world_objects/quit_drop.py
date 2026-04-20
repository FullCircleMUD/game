"""
QuitDrop — container spawned when a player quits outside an inn.

Inherits from Corpse to reuse the owner-only loot lock and timer system.
Behavioural differences from Corpse:

    - Display name: "{owner}'s abandoned pack" instead of "corpse of {owner}"
    - On unlock: announces the pack can be looted by anyone
    - On despawn: dumps all contents (NFT items, gold, resources) to the
      room floor, then deletes itself. (Corpse returns everything to RESERVE.)
"""

from typeclasses.world_objects.corpse import Corpse


class QuitDrop(Corpse):
    """
    A container for items dropped when a player quits outside an inn.

    Same loot-lock lifecycle as a Corpse (owner-only for 5 min, then
    public for 5 min, then despawn), but on despawn all contents are
    scattered on the ground instead of returned to RESERVE.
    """

    # ------------------------------------------------------------------ #
    #  Display
    # ------------------------------------------------------------------ #

    def get_display_name(self, looker=None, **kwargs):
        return f"{self.owner_name}'s abandoned pack"

    def get_display_desc(self, looker, **kwargs):
        return (
            f"A hastily abandoned pack of belongings left behind by "
            f"{self.owner_name}."
        )

    # ------------------------------------------------------------------ #
    #  Timer callbacks
    # ------------------------------------------------------------------ #

    def unlock(self):
        """Allow anyone to loot this pack."""
        if not self.pk:
            return
        if self.is_unlocked:
            return
        self.is_unlocked = True
        if self.location:
            self.location.msg_contents(
                f"{self.owner_name}'s abandoned pack can now be looted by anyone."
            )

    def despawn(self):
        """Dump all contents to the room floor, then delete the pack."""
        if not self.pk:
            return

        room = self.location
        has_contents = False

        from typeclasses.items.base_nft_item import BaseNFTItem

        # Scatter NFT items onto the ground
        for obj in list(self.contents):
            if isinstance(obj, BaseNFTItem):
                obj.move_to(room, quiet=True, move_type="teleport")
                has_contents = True

        # Transfer gold to the room floor
        gold = self.get_gold()
        if gold > 0:
            self.transfer_gold_to(room, gold)
            has_contents = True

        # Transfer resources to the room floor
        for rid, amt in list(self.get_all_resources().items()):
            if amt > 0:
                self.transfer_resource_to(room, rid, amt)
                has_contents = True

        if room:
            if has_contents:
                room.msg_contents(
                    f"{self.owner_name}'s abandoned pack falls apart, "
                    f"scattering its contents on the ground."
                )
            else:
                room.msg_contents(
                    f"{self.owner_name}'s abandoned pack crumbles away."
                )
        self.delete()
