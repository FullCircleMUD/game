from commands.class_skill_cmdsets.cmdset_base_char_class import CmdSetBaseCharClass
from commands.class_skill_cmdsets.class_skill_cmds.cmd_turn import CmdTurn


class CmdSetCleric(CmdSetBaseCharClass):
    """skills / commands for cleric class"""

    class_name = "Cleric"
    cmds = [
        CmdTurn,
    ]
