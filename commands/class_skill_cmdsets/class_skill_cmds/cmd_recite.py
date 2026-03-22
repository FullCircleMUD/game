from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdRecite(CmdSkillBase):
    """
    Cast a spell from a scroll.

    Design notes:
    - Class skill (MAGICAL_SECRETS) — thief, ninja.
    - Distinct from `cast` (which is casting from memory). Recite is for
      characters who don't formally study magic but can use scrolls.
    - Mastery level limits the scroll spell level that can be recited:
      basic = basic spells, skilled = skilled spells, etc.
    - Mages use `cast` for both memory and scrolls; thieves/ninjas use `recite`
      for scrolls only.
    """
    key = "recite"
    skill = skills.MAGICAL_SECRETS.value
    help_category = "Magic"

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
