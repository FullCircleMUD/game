"""
Resource processing room — convert raw materials into refined ones for a gold fee.

No skill required — anyone can use these rooms. Each room is configured with
a list of processing recipes. Single-recipe rooms (windmill, bakery) work with
bare 'process' / 'mill' / 'bake'. Multi-recipe rooms (smelter) require a
resource name: 'smelt iron ore', 'smelt bronze'.

Recipe format:
    {"inputs": {res_id: amount, ...}, "output": res_id, "amount": 1, "cost": 1}

The "cost" key is optional per recipe — defaults to room's process_cost.
"""

from typeclasses.terrain.rooms.room_base import RoomBase
from evennia import AttributeProperty
from commands.room_specific_cmds.processing.cmdset_processing import CmdSetProcessing


class RoomProcessing(RoomBase):

    # What kind of processing this room does (for display/flavour)
    processing_type = AttributeProperty("windmill")

    # Default gold cost per conversion (recipes can override with "cost" key)
    process_cost = AttributeProperty(1)

    # List of processing recipes available in this room
    recipes = AttributeProperty([])

    # XP awarded per process action (0 = no XP)
    process_xp = AttributeProperty(1)

    # Processing rooms are safe zones
    allow_combat = AttributeProperty(False, autocreate=False)
    allow_pvp = AttributeProperty(False, autocreate=False)
    allow_death = AttributeProperty(False, autocreate=False)

    # No vertical movement
    max_height = AttributeProperty(0)
    max_depth = AttributeProperty(0)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetProcessing, persistent=True)

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Welcome message when a player enters."""
        super().at_object_receive(moved_obj, source_location, **kwargs)

        if moved_obj.has_account:
            moved_obj.msg(f"\n|c--- Welcome to the {self.key} ---|n")
