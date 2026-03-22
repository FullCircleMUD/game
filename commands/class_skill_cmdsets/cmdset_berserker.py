from commands.class_skill_cmdsets.cmdset_base_char_class import CmdSetBaseCharClass
from commands.class_skill_cmdsets.class_skill_cmds.cmd_frenzy import CmdFrenzy
from commands.class_skill_cmdsets.class_skill_cmds.cmd_taunt import CmdTaunt

class CmdSetBerserker(CmdSetBaseCharClass):
    """skills / commands for berserker class"""

    class_name = "Berserker"
    cmds = [
        CmdFrenzy,
        CmdTaunt,
    ]
