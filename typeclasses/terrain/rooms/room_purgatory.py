"""
Purgatory room — where dead characters wait before release.

Characters are teleported here on death. After 1 minute they are
auto-released to their bound cemetery, or they can pay 50 gold
for early release via the `release` command.

Commands are restricted while dead (handled by FCMCharacter.at_pre_cmd).
"""

from evennia import AttributeProperty

from typeclasses.terrain.rooms.room_base import RoomBase
from commands.room_specific_cmds.purgatory.cmdset_purgatory import CmdSetPurgatory


class RoomPurgatory(RoomBase):

    allow_combat = AttributeProperty(False, autocreate=False)
    allow_pvp = AttributeProperty(False, autocreate=False)
    allow_death = AttributeProperty(False, autocreate=False)
    always_lit = AttributeProperty(True, autocreate=False)
    max_height = AttributeProperty(0)
    subterranean = AttributeProperty(True, autocreate=False)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetPurgatory, persistent=True)
