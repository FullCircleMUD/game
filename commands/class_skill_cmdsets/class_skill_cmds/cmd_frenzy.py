from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdFrenzy(CmdSkillBase):
    """
    Enter a berserk frenzy.

    Design notes:
    - Class skill (FRENZY) — berserker.
    - Increases damage output but reduces defence.
    - Damage bonus and defence penalty scale with mastery.
    """
    key = "frenzy"
    skill = skills.FRENZY.value
    help_category = "Combat"

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
