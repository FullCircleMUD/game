from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdConceal(CmdSkillBase):
    """
    Conceal yourself or an object through bardic glamour.

    Design notes:
    - Class skill (MISDIRECTION) — bard.
    - Lower mastery = hidden state (can be found by search/alertness).
    - Higher mastery = full invisible (harder to detect).
    - Duration and effectiveness scale with mastery.
    - Distinct from hide (physical stealth in shadows) — this is magical/bardic
      glamour. You're still standing there but nobody notices.
    """
    key = "conceal"
    skill = skills.MISDIRECTION.value
    help_category = "Stealth"

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
