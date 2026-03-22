# FullCircleMUD typeclasses/actors/actor_mixins/character_class_mixins/test_classes.py

from enums.mastery_level import MasteryLevel
from evennia import CmdSet

class CmdSetBaseCharClass(CmdSet):
    """
    Base class for all character classes.
    Concrete classes define `class_skills` as a list of Command classes.
    """
    class_name = "COMMAND SET CLASS NAME NOT YET SET"
    cmds = []

    def at_cmdset_creation(self):
        """
        This is called when the CmdSet is created. We can add commands here if needed.
        For now, we'll just add the commands defined in the class.
        """
        for cmd in self.cmds:
            self.add(cmd())

    @classmethod
    def at_add_to_character(cls, character):
        # according to chat GPT
        # character.cmdset.add() can take either a CmdSet class or an instance.
        # When you pass a class, Evennia internally instantiates it for you and calls its
        character.cmdset.add(cls, persistent=True)
        character.msg(f"{cls.class_name} added! Skills activated.")

        if not character.db.class_skill_mastery_levels:
            character.db.class_skill_mastery_levels = {}

        for cmd in cls.cmds:
            skill_key = cmd.skill.lower()

            if skill_key not in character.db.class_skill_mastery_levels:
                #character.msg(f"Hitting loop for cmd: {cmd.__name__} skill: {cmd.skill}")
                character.db.class_skill_mastery_levels[skill_key] = {"mastery": MasteryLevel.UNSKILLED.value, "classes": [cls.class_name]}
            else:
                skill = character.db.class_skill_mastery_levels[skill_key]
                classes = skill["classes"]
                if cls.class_name not in classes:
                    classes.append(cls.class_name)
                
                skill["classes"] = classes
                character.db.class_skill_mastery_levels[skill_key] = skill

