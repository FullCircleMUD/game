from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdAssassinate(CmdSkillBase):
    """
    Attempt to instantly kill a target from stealth.

    Design notes:
    - Class skill (ASSASSINATE) — ninja.
    - Instant kill attempt. Requires being hidden.
    - Success chance scales with mastery vs target level/HD.
    """
    key = "assassinate"
    skill = skills.ASSASSINATE.value
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
