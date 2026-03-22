"""
Skilled crafting room — characters craft NFT items from learned recipes.

Requires skill mastery. Each room has a crafting_type (SMITHY, WOODSHOP, etc.)
that determines which recipes can be crafted here. Room mastery_level gates
the maximum recipe complexity.

Examples:
    Woodshop:  carve training longsword  (2 Timber + 2 gold + room fee)
    Smithy:    forge iron longsword      (2 Iron Ingots + 5 gold + room fee)
"""

from typeclasses.terrain.rooms.room_base import RoomBase
from evennia import AttributeProperty
from commands.room_specific_cmds.crafting.cmdset_crafting import CmdSetCrafting


class RoomCrafting(RoomBase):

    # RoomCraftingType value — determines which recipes work here
    crafting_type = AttributeProperty("woodshop")

    # Max recipe mastery level this room supports (MasteryLevel.value)
    mastery_level = AttributeProperty(1)

    # Gold room fee per craft (on top of recipe's gold_cost)
    craft_cost = AttributeProperty(2)

    # XP multiplier for crafting in this room (1.0 = standard)
    craft_xp_multiplier = AttributeProperty(1.0)

    # Safe zones
    allow_combat = AttributeProperty(False, autocreate=False)
    allow_pvp = AttributeProperty(False, autocreate=False)
    allow_death = AttributeProperty(False, autocreate=False)

    # No vertical movement
    max_height = AttributeProperty(0)
    max_depth = AttributeProperty(0)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetCrafting, persistent=True)

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Welcome message when a player enters."""
        super().at_object_receive(moved_obj, source_location, **kwargs)

        if moved_obj.has_account:
            moved_obj.msg(f"\n|c--- Welcome to the {self.key} ---|n")
