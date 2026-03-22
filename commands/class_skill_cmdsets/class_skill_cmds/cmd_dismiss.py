from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdDismiss(CmdSkillBase):
    """
    Dismiss your animal companion back to the other dimension.

    Design notes:
    - Class skill (ANIMAL_COMPANION) — druid, ranger.
    - Sends your companion back to the other dimension.
    - Available any time your companion is present.
    """
    key = "dismiss"
    skill = skills.ANIMAL_COMPANION.value
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
