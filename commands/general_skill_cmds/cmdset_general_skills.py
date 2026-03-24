from commands.class_skill_cmdsets.cmdset_base_char_class import CmdSetBaseCharClass
from commands.class_skill_cmdsets.class_skill_cmds.cmd_dodge import CmdDodge
from commands.class_skill_cmdsets.class_skill_cmds.cmd_assist import CmdAssist
from commands.class_skill_cmdsets.class_skill_cmds.cmd_sail import CmdSail
from commands.class_skill_cmdsets.class_skill_cmds.cmd_tame import CmdTame
from commands.room_specific_cmds.crafting.cmd_repair import CmdRepair
from commands.general_skill_cmds.cmd_survey import CmdSurvey
from commands.general_skill_cmds.cmd_map import CmdMap
from enums.mastery_level import MasteryLevel


class CmdSetGeneralSkills(CmdSetBaseCharClass):
    """Skills / commands available to all characters regardless of class"""

    # ----- define the general/all-character commands directly in the mixin -----
    class_name = "General Skills"
    cmds = [
        CmdDodge,
        CmdAssist,
        CmdSail,
        CmdTame,
        CmdRepair,
        CmdSurvey,
        CmdMap,
    ]


    @classmethod
    def at_add_to_character(cls, character):
        # according to chat GPT
        # character.cmdset.add() can take either a CmdSet class or an instance.
        # When you pass a class, Evennia internally instantiates it for you and calls its
        character.cmdset.add(cls, persistent=True)
        character.msg(f"{cls.class_name} added! Skills activated.")

        if not character.db.general_skill_mastery_levels:
            character.db.general_skill_mastery_levels = {}

        for cmd in cls.cmds:
            if not hasattr(cmd, 'skill'):
                continue
            #character.msg(f"Hitting loop for cmd: {cmd.__name__} skill: {cmd.skill}")
            character.db.general_skill_mastery_levels[cmd.skill.lower()] = MasteryLevel.UNSKILLED.value