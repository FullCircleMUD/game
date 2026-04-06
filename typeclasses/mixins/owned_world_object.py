"""
OwnedWorldObjectMixin — shared patterns for player-owned objects that
exist in the game world but are NOT carried in regular inventory.

Provides:
    - db.world_location tracking (where the object is in the world)
    - get:false() lock (can't be picked up)
    - Zero weight (doesn't count toward encumbrance)
    - Block get/drop, allow give (ownership transfer)
    - Human-readable location display

Composed into:
    WorldAnchoredNFTItem(OwnedWorldObjectMixin, BaseNFTItem) — ships, property
    BasePet(NFTMirrorMixin, OwnedWorldObjectMixin, ..., BaseNPC) — pets, mounts
"""


class OwnedWorldObjectMixin:
    """Mixin for player-owned objects anchored in the game world."""

    def at_owned_world_object_init(self):
        """
        Initialize owned world object state. Call from at_object_creation().
        Safe to call multiple times.
        """
        self.locks.add("get:false()")
        self.db.weight = 0
        if self.db.world_location is None:
            self.db.world_location = None

    def set_world_location(self, room):
        """
        Update the in-world position and persist to XRPL token URI metadata.

        Args:
            room: the room object (dock, stable, kennel, etc.)
        """
        self.db.world_location = room
        self._persist_location_to_uri()

    def _persist_location_to_uri(self):
        """
        Write db.world_location to the XRPL token URI so the location
        survives withdraw/re-import and is visible on external marketplaces.

        Stub — wired up when XRPL URI write support is added to NFTService.
        """
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
        Allow give — ownership transfer is the primary way ships, pets,
        and mounts change hands.
        """
        return True
