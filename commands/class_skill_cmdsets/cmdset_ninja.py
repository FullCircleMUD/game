from commands.class_skill_cmdsets.cmdset_base_char_class import CmdSetBaseCharClass
from commands.class_skill_cmdsets.class_skill_cmds.cmd_stab import CmdStab
from commands.class_skill_cmdsets.class_skill_cmds.cmd_assassinate import CmdAssassinate
from commands.class_skill_cmdsets.class_skill_cmds.cmd_recite import CmdRecite
from commands.class_skill_cmdsets.class_skill_cmds.cmd_case import CmdCase
from commands.class_skill_cmdsets.class_skill_cmds.cmd_stash import CmdStash
from commands.class_skill_cmdsets.class_skill_cmds.cmd_picklock import CmdPicklock
from commands.class_skill_cmdsets.class_skill_cmds.cmd_pickpocket import CmdPickpocket
from commands.class_skill_cmdsets.class_skill_cmds.cmd_disarm_trap import CmdDisarmTrap

class CmdSetNinja(CmdSetBaseCharClass):
    """skills / commands for ninja class"""

    class_name = "Ninja"
    cmds = [
        CmdStab,
        CmdAssassinate,
        CmdRecite,
        CmdCase,
        CmdStash,
        CmdPicklock,
        CmdPickpocket,
        CmdDisarmTrap,
    ]
