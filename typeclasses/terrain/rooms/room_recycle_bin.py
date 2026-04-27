"""
NFT Recycle Bin — a hidden, inaccessible room that serves as the
default home for all NFT items.

If an NFT item ends up here (e.g. its room was deleted and Evennia
teleported contents to their home), the item is despawned in the
mirror DB and deleted. Characters that somehow arrive here are
immediately teleported to DEFAULT_HOME.

This room should have no exits and be created once during world setup.
"""

from evennia import DefaultRoom, search_object
from django.conf import settings


class RoomRecycleBin(DefaultRoom):

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Called when any object arrives in this room."""
        super().at_object_receive(moved_obj, source_location, **kwargs)

        from typeclasses.items.base_nft_item import BaseNFTItem
        from typeclasses.actors.character import FCMCharacter

        if isinstance(moved_obj, FCMCharacter):
            # Character should never be here — try their home first,
            # fall back to DEFAULT_HOME if home is this room or doesn't exist
            destination = moved_obj.home
            if destination is None or destination == self:
                results = search_object(settings.DEFAULT_HOME)
                destination = results[0] if results else None
            if destination and destination != self:
                moved_obj.msg("You were moved to safety.")
                moved_obj.move_to(destination, quiet=True, move_type="teleport")
            return

        if isinstance(moved_obj, BaseNFTItem):
            # NFT landed in the bin — delete (at_object_delete handles mirror despawn)
            print(f"  RecycleBin: despawning NFT #{moved_obj.token_id}")
            moved_obj.delete()
            return

        # Catch-all — any non-player, non-NFT object (WorldItems, fixtures,
        # corpses, etc.) that ends up here is orphaned and should be deleted.
        print(f"  RecycleBin: deleting orphaned object '{moved_obj.key}'")
        moved_obj.delete()
