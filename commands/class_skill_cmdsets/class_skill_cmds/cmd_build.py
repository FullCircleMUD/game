from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdBuild(CmdSkillBase):
    """
    Build or repair a ship.

    Design notes:
    - General skill (SHIPWRIGHT) — available to all characters.
    - Uses the crafting recipe system. Ships have recipes like any other craftable:
      input requirements, skill requirements, and output NFTs.
    - Ship quality and available blueprints scale with mastery.
    """
    key = "build"
    skill = skills.SHIPWRIGHT.value
    help_category = "Exploration"

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
