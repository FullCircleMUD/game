
from evennia import CmdSet
from commands.room_specific_cmds.bank.cmd_withdraw  import CmdWithdraw
from commands.room_specific_cmds.bank.cmd_deposit import CmdDeposit
from commands.room_specific_cmds.bank.cmd_balance import CmdBalance

 
# =====================================================================
# Command set so the commands cen be added to the character cmdset. 
# =====================================================================

class CmdSetBank(CmdSet):

    key = "CmdSetAllCharacters"

    def at_cmdset_creation(self):
        self.add(CmdWithdraw())
        self.add(CmdDeposit())
        self.add(CmdBalance())



