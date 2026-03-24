"""
ShipNFTItem — NFT-backed ships owned by players.

Ships live in character.contents (0 weight, invisible to `inventory`).
Their in-world position is tracked via `db.world_location` (a dock room)
and persisted to the XRPL token URI so the location survives withdraw/
re-import and is visible to buyers on external marketplaces.

Ownership lifecycle:
    - Built by Shipwright at a shipyard → world_location = adjacent dock
    - Sold/given anywhere → new owner inherits existing world_location
    - New owner must travel to that dock to sail the ship
    - Sailed to a new dock → world_location updated, URI updated
    - Shipwrecked → object.delete() → NFT lifecycle returns token to reserve

Ship tier maps 1:1 to ShipType enum / mastery levels:
    1 = Cog (BASIC)
    2 = Caravel (SKILLED)
    3 = Brigantine (EXPERT)
    4 = Carrack (MASTER)
    5 = Galleon (GRANDMASTER)
"""

from typeclasses.items.untakeables.world_anchored_nft_item import WorldAnchoredNFTItem


class ShipNFTItem(WorldAnchoredNFTItem):
    """
    A player-owned ship NFT.

    Attributes:
        db.world_location — dock room where the ship is currently berthed.
            Set at build time (shipyard's adjacent dock). Updated on each
            successful voyage. Persisted to XRPL token URI.
        db.ship_tier — int 1–5 matching ShipType enum value. Set at spawn.

    The ship is usable only when the owning character is at the dock
    matching db.world_location. SeaborneGate checks this at sail time.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.ship_tier = 0  # set by spawn_into() from NFTItemType metadata

    @property
    def ship_tier(self):
        """Return the ship's tier (1–5). 0 means not yet assigned."""
        return self.db.ship_tier or 0

    def at_post_move(self, source_location, **kwargs):
        """
        On first creation (source_location is None, destination is a character),
        set world_location to the adjacent dock room so the ship is immediately
        usable without a manual setup step.

        Scans the crafting room's exits for a RoomGateway (dock). Falls back to
        the crafting room itself if no dock exit is found.
        """
        super().at_post_move(source_location, **kwargs)

        if source_location is None and self.location is not None:
            from typeclasses.terrain.rooms.room_gateway import RoomGateway
            crafting_room = self.location.location  # character → room
            if crafting_room is None:
                return
            # Scan exits for an adjacent dock (RoomGateway)
            dock = None
            for exit_obj in crafting_room.exits:
                dest = exit_obj.destination
                if dest and isinstance(dest, RoomGateway):
                    dock = dest
                    break
            self.set_world_location(dock or crafting_room)

    def arrive_at_dock(self, dock_room):
        """
        Called when a successful voyage completes. Updates world_location to
        the new dock and persists to XRPL token URI.

        Args:
            dock_room: the RoomGateway dock room the ship has arrived at.
        """
        self.set_world_location(dock_room)

    def get_owned_display(self):
        """
        Return a single-line summary for the `owned` command listing.
        e.g. "  The Grey Widow (Caravel) — berthed at Saltspray Bay Docks"
        """
        from enums.ship_type import ShipType
        try:
            tier_name = ShipType(self.ship_tier).item_type_name
        except (ValueError, KeyError):
            tier_name = "Ship"
        loc = self.get_world_location_display()
        return f"  {self.key} ({tier_name}) — berthed at {loc}"
