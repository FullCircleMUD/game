from commands.class_skill_cmdsets.cmdset_base_char_class import CmdSetBaseCharClass
from commands.class_skill_cmdsets.class_skill_cmds.cmd_case import CmdCase
from commands.class_skill_cmdsets.class_skill_cmds.cmd_picklock import CmdPicklock
from commands.class_skill_cmdsets.class_skill_cmds.cmd_pickpocket import CmdPickpocket
from commands.class_skill_cmdsets.class_skill_cmds.cmd_disarm_trap import CmdDisarmTrap
from commands.class_skill_cmdsets.class_skill_cmds.cmd_stash import CmdStash
from commands.class_skill_cmdsets.class_skill_cmds.cmd_backstab import CmdBackstab
from commands.class_skill_cmdsets.class_skill_cmds.cmd_recite import CmdRecite

class CmdSetThief(CmdSetBaseCharClass):
    """skills / commands for thief class"""

    # ----- define the skills directly in the class -----
    class_name = "Thief"
    cmds = [
        CmdCase,
        CmdPicklock,
        CmdPickpocket,
        CmdDisarmTrap,
        CmdStash,
        CmdBackstab,
        CmdRecite,
    ]