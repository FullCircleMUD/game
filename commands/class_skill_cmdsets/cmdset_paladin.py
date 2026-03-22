from commands.class_skill_cmdsets.cmdset_base_char_class import CmdSetBaseCharClass
from commands.class_skill_cmdsets.class_skill_cmds.cmd_protect import CmdProtect
from commands.class_skill_cmdsets.class_skill_cmds.cmd_taunt import CmdTaunt
from commands.class_skill_cmdsets.class_skill_cmds.cmd_turn import CmdTurn

class CmdSetPaladin(CmdSetBaseCharClass):
    """skills / commands for paladin class"""

    class_name = "Paladin"
    cmds = [
        CmdProtect,
        CmdTaunt,
        CmdTurn,
    ]
