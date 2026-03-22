"""
RoomGateway — a room that connects zones via the `travel` and `explore` commands.

Stores a list of destinations, each with:
- travel conditions (food, gold, level, etc.)
- discovery requirements (hidden until discovered via exploration or chart item)
- narrative text for the journey

Players use `travel` to go to known destinations and `explore` to attempt
discovering hidden ones (each bread = one exploration roll).
"""

from evennia import AttributeProperty

from typeclasses.terrain.rooms.room_base import RoomBase
from commands.room_specific_cmds.gateway.cmdset_gateway import CmdSetGateway


class RoomGateway(RoomBase):
    """
    Gateway room connecting zones.

    destinations is a list of dicts, each with:
        key             - unique id for this link (str)
        label           - display name (str)
        destination     - target RoomGateway dbref (obj)
        travel_description - narrative on travel (str)
        conditions      - dict of travel conditions (optional):
            food_cost       - int, bread consumed
            gold_cost       - int, gold consumed
            level_required  - int, minimum total_level
            mounted         - bool (stub)
            fly             - bool (stub)
            water_breathing - bool (stub)
            boat_level      - int (stub)
        hidden          - bool, must discover first (default False)
        discover_item_tag - str, item tag that reveals this dest (optional)
        explore_chance  - int, % chance per roll (default 20)
    """

    destinations = AttributeProperty([], autocreate=False)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetGateway, persistent=True)
