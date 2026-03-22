"""CmdSet for tutorial rooms — adds the `tutorial` command."""

from evennia import CmdSet

from commands.room_specific_cmds.tutorial.cmd_tutorial import CmdTutorial


class CmdSetTutorial(CmdSet):
    key = "CmdSetTutorial"

    def at_cmdset_creation(self):
        self.add(CmdTutorial())
