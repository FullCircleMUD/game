from commands.class_skill_cmdsets.cmdset_base_char_class import CmdSetBaseCharClass
from commands.class_skill_cmdsets.class_skill_cmds.cmd_bash import CmdBash
from commands.class_skill_cmdsets.class_skill_cmds.cmd_pummel import CmdPummel
from commands.class_skill_cmdsets.class_skill_cmds.cmd_retreat import CmdRetreat
from commands.class_skill_cmdsets.class_skill_cmds.cmd_protect import CmdProtect
from commands.class_skill_cmdsets.class_skill_cmds.cmd_taunt import CmdTaunt
from commands.class_skill_cmdsets.class_skill_cmds.cmd_offence import CmdOffence
from commands.class_skill_cmdsets.class_skill_cmds.cmd_defence import CmdDefence

class CmdSetWarrior(CmdSetBaseCharClass):
    """skills / commands for warrior class"""

    # ----- define the skills directly in the class -----
    class_name = "Warrior"
    cmds = [
        CmdBash,
        CmdPummel,
        CmdRetreat,
        CmdProtect,
        CmdTaunt,
        CmdOffence,
        CmdDefence,
    ]