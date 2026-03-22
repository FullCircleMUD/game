"""
CmdSetMobCombat — combat commands available to CombatMob NPCs.

Added to CombatMob at creation so mobs can use the same command
interface as players. AI state methods call execute_cmd("attack target")
which resolves through this cmdset.
"""

from evennia import CmdSet

from commands.all_char_cmds.cmd_attack import CmdAttack
from commands.all_char_cmds.cmd_flee import CmdFlee
from commands.class_skill_cmdsets.class_skill_cmds.cmd_dodge import CmdDodge


class CmdSetMobCombat(CmdSet):
    """Combat commands for mobs — same commands as players."""

    key = "CmdSetMobCombat"

    def at_cmdset_creation(self):
        self.add(CmdAttack())
        self.add(CmdDodge())
        self.add(CmdFlee())
