"""
RoomStable — a room where pets and mounts can be safely stabled.

Stabled pets:
    - Don't consume food (hunger paused)
    - Can't be attacked
    - Persist indefinitely
    - Cost 1 gold to stable

Commands:
    stable <pet>     — stable a pet for 1 gold
    retrieve <pet>   — retrieve a stabled pet
    stabled          — list your stabled pets here

Large animals (horses) are explicitly allowed in stables regardless
of the room's max_height setting.
"""

from typeclasses.terrain.rooms.room_base import RoomBase
from evennia import AttributeProperty
from commands.room_specific_cmds.stable.cmdset_stable import CmdSetStable


class RoomStable(RoomBase):

    allow_combat = AttributeProperty(False, autocreate=False)
    allow_pvp = AttributeProperty(False, autocreate=False)
    allow_death = AttributeProperty(False, autocreate=False)

    # Stables accept large animals despite being indoor
    max_height = AttributeProperty(0)
    max_depth = AttributeProperty(0)

    # Stable fee in gold
    stable_fee = AttributeProperty(1)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetStable, persistent=True)
        # Tag so pets skip size restriction check
        self.tags.add("stable", category="room_type")
