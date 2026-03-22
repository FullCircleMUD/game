from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdDivert(CmdSkillBase):
    """
    Redirect a mob's aggro from one target to another.

    Design notes:
    - Class skill (MANIPULATION) — bard.
    - Unlike taunt (pull aggro onto yourself), divert redirects aggro between
      any two targets. E.g. divert aggro off your mage onto your tank.
    - Contested CHA + mastery vs target WIS.
    - Success chance scales with mastery.
    """
    key = "divert"
    skill = skills.MANIPULATION.value
    help_category = "Performance"

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
