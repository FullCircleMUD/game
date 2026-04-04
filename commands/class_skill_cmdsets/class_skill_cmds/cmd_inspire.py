from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdInspire(CmdSkillBase):
    """
    Inspire your group with a rousing performance.

    Design notes:
    - Class skill (INSPIRATION) — bard.
    - Whole group combat buff. Scaling:
      Basic:  +10 max temp HP
      Skilled: +10 max temp HP, +1 AC
      Expert:  +10 max temp HP, +1 AC, +1 hit
      Master:  +10 max temp HP, +1 AC, +1 hit, +1 dam
      GM:      +20 max temp HP, +2 AC, +2 hit, +2 dam
    """
    key = "inspire"
    skill = skills.INSPIRATION.value
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
