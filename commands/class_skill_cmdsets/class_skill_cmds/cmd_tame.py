from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdTame(CmdSkillBase):
    """
    Tame a wild animal.

    Design notes:
    - General skill (ANIMAL_HANDLING) — available to all characters.
    - One-off act: makes a wild animal tame so anyone can use it.
    - Success chance scales with mastery and animal difficulty.
    - Distinct from ANIMAL_COMPANION (class skill): tame is the "horse breaker"
      skill, while bond/summon is the druid/ranger's permanent fighting companion.
    """
    key = "tame"
    skill = skills.ANIMAL_HANDLING.value
    help_category = "Nature"

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
