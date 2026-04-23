

from evennia import CmdSet
from commands.unloggedin_cmds.cmd_override_unconnected_connect import CmdUnconnectedConnect
from commands.unloggedin_cmds.cmd_override_unloggedin_create import CmdUnconnectedCreate
from commands.unloggedin_cmds.cmd_override_unloggedin_help import CmdUnconnectedHelp

class CmdSetUnloggedinCustom(CmdSet):

    key = "CmdSetUnloggedinCustom"

    def at_cmdset_creation(self):

        # DEFAULT COMMANDS AVAILABLE FOR OVERRIDE
        
        #CmdUnconnectedConnect
        self.add(CmdUnconnectedConnect())
        #CmdUnconnectedCreate
        self.add(CmdUnconnectedCreate())
        #CmdUnconnectedQuit
        #CmdUnconnectedLook
        self.add(CmdUnconnectedHelp())
        #CmdUnconnectedEncoding
        #CmdUnconnectedScreenreader
        #CmdUnconnectedInfo


        # CUSTOM COMMANDS
