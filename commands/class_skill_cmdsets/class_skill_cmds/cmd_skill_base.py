# FullCircleMUD typeclasses/actors/skill_commands/test_skills.py


from evennia import Command
from enums.mastery_level import MasteryLevel

from commands.command import FCMCommandMixin


class CmdSkillBase(FCMCommandMixin, Command):
    # The name of / key for the command
    key = "KEY - BASE VALUE NOT OVERRIDDEN"
    aliases = []
    help_category = "Skill Commands"

    # The skill this command relies on / uses for its execution
    skill = "SKILL_NAME - BASE VALUE NOT OVERRIDDEN" 
    

    def func(self):
        # Callers without skill mastery data (e.g. animal mobs) get mob_func().
        # Humanoid NPCs with mastery data use the same dispatch as players.
        if not (getattr(self.caller.db, "general_skill_mastery_levels", None)
                or getattr(self.caller.db, "class_skill_mastery_levels", None)
                or getattr(self.caller.db, "weapon_skill_mastery_levels", None)):
            return self.mob_func()

        mastery_level = self.caller.get_skill_mastery(self.skill)

        # Call the appropriate function based on mastery level
        dispatch = {
            MasteryLevel.UNSKILLED.value: self.unskilled_func,
            MasteryLevel.BASIC.value: self.basic_func,
            MasteryLevel.SKILLED.value: self.skilled_func,
            MasteryLevel.EXPERT.value: self.expert_func,
            MasteryLevel.MASTER.value: self.master_func,
            MasteryLevel.GRANDMASTER.value: self.grandmaster_func,
        }

        dispatch.get(mastery_level, lambda: self.caller.msg(f"Unknown mastery level for skill '{self.key}' : '{mastery_level}'"))()

    # The following functions will be overridden in child classes to provide 
    # specific behavior for each skill and mastery level. 

    def unskilled_func(self):
        raise NotImplementedError(f"Unskilled function not implemented yet for skill '{self.key}'.")

    def basic_func(self):
        raise NotImplementedError(f"Basic function not implemented yet for skill '{self.key}'.")

    def skilled_func(self):
        raise NotImplementedError(f"Skilled function not implemented yet for skill '{self.key}'.")

    def expert_func(self):
        raise NotImplementedError(f"Expert function not implemented yet for skill '{self.key}'.")

    def master_func(self):
        raise NotImplementedError(f"Master function not implemented yet for skill '{self.key}'.")

    def grandmaster_func(self):
        raise NotImplementedError(f"Grandmaster function not implemented yet for skill '{self.key}'.")

    def mob_func(self):
        """
        Called for callers without skill mastery data (animal mobs, etc.).
        Override in subclasses for mob-specific behavior.
        """
        self.caller.msg(f"You don't know how to {self.key}.")
