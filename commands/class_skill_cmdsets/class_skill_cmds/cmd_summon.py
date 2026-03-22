from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdSummon(CmdSkillBase):
    """
    Summon your bonded animal companion from the other dimension.

    Design notes:
    - Class skill (ANIMAL_COMPANION) — druid, ranger.
    - The companion is bonded by default (class feature). No bond command needed.
    - In-game lore: the companion persists in another dimension. When killed,
      it returns there and can be re-summoned.
    - Companion power/type scales with mastery:
      Basic = small animal (rat, cat)
      Skilled = medium animal (wolf, hawk)
      Expert = large animal (bear, panther)
      Master = powerful animal (dire wolf, giant eagle)
      GM = something exceptional like a small dragon
    """
    key = "summon"
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
