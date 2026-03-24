"""
WorldAnchoredNFTItem — Base class for player-owned NFTs that are NOT carried
in inventory.

These objects live in character.contents for ownership tracking (full NFT
lifecycle applies — give, delete, bank, import/export all work normally)
but are invisible to `inventory` and `equipment` commands. They have zero
weight and a real in-world position tracked via `db.world_location`.

The `db.world_location` attribute is also written to the XRPL token URI so
the location survives withdraw/re-import and is visible to buyers on external
marketplaces.

Subtypes:

    ShipNFTItem — berthed at a dock room. Sailed to a new dock on arrival.
        Sale can happen anywhere; new owner must travel to the dock to use it.
        Built by Shipwright skill at a shipyard; starts at the adjacent dock.
        Destroyed on shipwreck (object.delete() → NFT lifecycle handles XRPL).

    MountNFTItem (future) — stabled at a stable room. Ride/walk to new stable.

    PetNFTItem (future) — kennelled at a kennel/stable room.

    PropertyNFTItem (future) — tied to a room permanently; world_location never
        changes after placement.

Standard get/drop/give/junk commands refuse to interact with these items.
Use the `owned` command to list all owned objects and their world locations.
"""

from evennia.utils.utils import lazy_property

from typeclasses.items.base_nft_item import BaseNFTItem


class WorldAnchoredNFTItem(BaseNFTItem):
    """
    An NFT item that lives in character.contents but is invisible to standard
    inventory/equipment commands.

    Key attributes:
        db.world_location — the room object where this item currently resides
            in the game world (dock, stable, kennel, property room).
            Persisted to XRPL token URI on change so it survives withdraw/import.

        weight — always 0; does not contribute to encumbrance.

    Subclass for specific owned types:
        - ShipNFTItem — dock/sail at docks, built at shipyards
        - MountNFTItem (future) — stable/collect at stables
        - PetNFTItem (future) — kennel/collect at kennels
        - PropertyNFTItem (future) — deeds, room ownership
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.locks.add("get:false()")
        self.db.weight = 0
        self.db.world_location = None

    def set_world_location(self, room):
        """
        Update the in-world position of this owned object and persist to XRPL
        token URI metadata.

        Args:
            room: the RoomGateway (dock), stable room, or other location room.
        """
        self.db.world_location = room
        self._persist_location_to_uri()

    def _persist_location_to_uri(self):
        """
        Write db.world_location to the XRPL token URI so the location survives
        withdraw/re-import cycles and is visible on external marketplaces.

        Stub — wired up when XRPL URI write support is added to NFTService.
        """
        # TODO: call NFTService.update_token_uri(self.token_id, {"world_location": room_key})
        pass

    def get_world_location_display(self):
        """Return a human-readable description of where this object is."""
        loc = self.db.world_location
        if loc is None:
            return "unknown location"
        return loc.get_display_name(self) if hasattr(loc, "get_display_name") else str(loc)

    def at_pre_get(self, getter, **kwargs):
        """Block standard pickup."""
        getter.msg(f"You can't pick up {self.get_display_name(getter)}.")
        return False

    def at_pre_drop(self, dropper, **kwargs):
        """Block standard drop."""
        dropper.msg(f"You can't drop {self.get_display_name(dropper)}.")
        return False

    def at_pre_give(self, giver, target, **kwargs):
        """
        Allow give — ownership transfer is the primary way ships and mounts
        change hands. The full NFT at_give() hook handles the ownership mirror
        update. The new owner inherits the existing world_location.
        """
        return True
