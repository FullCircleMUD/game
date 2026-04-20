from commands.class_skill_cmdsets.cmdset_base_char_class import CmdSetBaseCharClass
from commands.class_skill_cmdsets.class_skill_cmds.cmd_perform import CmdPerform
from commands.class_skill_cmdsets.class_skill_cmds.cmd_inspire import CmdInspire
from commands.class_skill_cmdsets.class_skill_cmds.cmd_mock import CmdMock
from commands.class_skill_cmdsets.class_skill_cmds.cmd_charm import CmdCharm
from commands.class_skill_cmdsets.class_skill_cmds.cmd_divert import CmdDivert
from commands.class_skill_cmdsets.class_skill_cmds.cmd_disguise import CmdDisguise
from commands.class_skill_cmdsets.class_skill_cmds.cmd_conceal import CmdConceal
from commands.class_skill_cmdsets.class_skill_cmds.cmd_identify import CmdIdentify
from commands.class_skill_cmdsets.class_skill_cmds.cmd_recognise import CmdRecognise
from commands.class_skill_cmdsets.class_skill_cmds.cmd_case import CmdCase
from commands.class_skill_cmdsets.class_skill_cmds.cmd_stash import CmdStash
from commands.class_skill_cmdsets.class_skill_cmds.cmd_picklock import CmdPicklock
from commands.class_skill_cmdsets.class_skill_cmds.cmd_pickpocket import CmdPickpocket
from commands.class_skill_cmdsets.class_skill_cmds.cmd_disarm_trap import CmdDisarmTrap

class CmdSetBard(CmdSetBaseCharClass):
    """skills / commands for bard class"""

    class_name = "Bard"
    cmds = [
        CmdPerform,
        CmdInspire,
        CmdMock,
        CmdCharm,
        CmdDivert,
        CmdDisguise,
        CmdConceal,
        CmdIdentify,
        CmdRecognise,
        CmdCase,
        CmdStash,
        CmdPicklock,
        CmdPickpocket,
        CmdDisarmTrap,
    ]
