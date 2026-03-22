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

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetPurgatory, persistent=True)
        self.db.desc = (
            "You float in a grey void between life and death. "
            "Faint whispers echo around you, the voices of those who came before. "
            "A dim light pulses in the distance, slowly growing brighter.\n\n"
            "You will be released soon. Type |wrelease|n for early release (50 gold)."
        )
