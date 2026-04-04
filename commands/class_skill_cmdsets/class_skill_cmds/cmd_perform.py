from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdPerform(CmdSkillBase):
    """
    Perform music, poetry, or storytelling.

    Design notes:
    - Class skill (PERFORMANCE) — bard.
    - Two effects:
      1) Distracts audience — gives pickpocket bonus of 1d4 per skill tier
         to nearby thieves.
      2) Raises regard/reputation with the audience.
    - Scaling: larger audience affected / bigger bonuses at higher mastery.
    """
    key = "perform"
    skill = skills.PERFORMANCE.value
    help_category = "Performance"
    allow_while_sleeping = True

    def unskilled_func(self):
        self.caller.msg(f"'{self.key}' Command using Skill '{self.skill}' - Unskilled")

    def basic_func(self):
        self.caller.msg(f"'{self.key}' Command using Skill '{self.skill}' - Basic")

    def skilled_func(self):
        self.caller.msg(f"'{self.key}' Command using Skill '{self.skill}' - Skilled")

    def expert_func(self):
        self.caller.msg(f"'{self.key}' Command using Skill '{self.skill}' - Expert")

    def master_func(self):
        self.caller.msg(f"'{self.key}' Command using Skill '{self.skill}' - Master")

    def grandmaster_func(self):
        self.caller.msg(f"'{self.key}' Command using Skill '{self.skill}' - Grandmaster")
