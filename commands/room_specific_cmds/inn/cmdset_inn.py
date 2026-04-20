from evennia import CmdSet

from commands.room_specific_cmds.inn.cmd_stew import CmdStew
from commands.room_specific_cmds.inn.cmd_ale import CmdAle
from commands.room_specific_cmds.inn.cmd_menu import CmdMenu
from commands.room_specific_cmds.inn.cmd_rent import CmdRent


class CmdSetInn(CmdSet):

    key = "CmdSetInn"

    def at_cmdset_creation(self):
        self.add(CmdStew())
        self.add(CmdAle())
        self.add(CmdMenu())
        self.add(CmdRent())
