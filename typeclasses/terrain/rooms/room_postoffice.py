"""Post Office room — provides mail commands to characters."""

from evennia import AttributeProperty

from commands.room_specific_cmds.postoffice.cmdset_postoffice import CmdSetPostOffice
from typeclasses.terrain.rooms.room_base import RoomBase


class RoomPostOffice(RoomBase):

    allow_combat = AttributeProperty(False, autocreate=False)
    allow_pvp = AttributeProperty(False, autocreate=False)
    allow_death = AttributeProperty(False, autocreate=False)
    max_height = AttributeProperty(0)
    max_depth = AttributeProperty(0)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetPostOffice, persistent=True)

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Welcome message when a player enters."""
        super().at_object_receive(moved_obj, source_location, **kwargs)
        if moved_obj.has_account:
            moved_obj.msg("\n|c--- Welcome to the Post Office ---|n")
            # Show unread mail count
            from commands.room_specific_cmds.postoffice.cmd_mail import CmdMail
            unread = CmdMail.get_unread_count(moved_obj)
            if unread:
                moved_obj.msg(f"|yYou have {unread} unread message(s). Type |wmail|y to check.|n")
