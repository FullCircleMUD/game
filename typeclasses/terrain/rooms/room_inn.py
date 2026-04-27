from typeclasses.terrain.rooms.room_base import RoomBase
from evennia import AttributeProperty
from commands.room_specific_cmds.inn.cmdset_inn import CmdSetInn


class RoomInn(RoomBase):

    allow_combat = AttributeProperty(False, autocreate=False)
    allow_pvp = AttributeProperty(False, autocreate=False)
    allow_death = AttributeProperty(False, autocreate=False)

    max_height = AttributeProperty(0)
    max_depth = AttributeProperty(0)

    welcome_message = AttributeProperty("\n|c--- Welcome to the Inn ---|n")

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetInn, persistent=True)

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Called when something enters the room."""
        super().at_object_receive(moved_obj, source_location, **kwargs)

        if moved_obj.has_account:
            moved_obj.msg(self.welcome_message)
