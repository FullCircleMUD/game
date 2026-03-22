from commands.class_skill_cmdsets.cmdset_base_char_class import CmdSetBaseCharClass
from commands.class_skill_cmdsets.class_skill_cmds.cmd_forage import CmdForage
from commands.class_skill_cmdsets.class_skill_cmds.cmd_track import CmdTrack
from commands.class_skill_cmdsets.class_skill_cmds.cmd_summon import CmdSummon
from commands.class_skill_cmdsets.class_skill_cmds.cmd_dismiss import CmdDismiss
from commands.class_skill_cmdsets.class_skill_cmds.cmd_shapeshift import CmdShapeshift

class CmdSetDruid(CmdSetBaseCharClass):
    """skills / commands for druid class"""

    class_name = "Druid"
    cmds = [
        CmdForage,
        CmdTrack,
        CmdSummon,
        CmdDismiss,
        CmdShapeshift,
    ]
