from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdChart(CmdSkillBase):
    """
    Create a map of explored areas.

    Design notes:
    - General skill (CARTOGRAPHY) — available to all characters.
    - Creates an NFT map item of areas the cartographer has explored.
    - Wipes the cartographer's area memory on creation (they "gave away" their knowledge).
    - Map quality and detail scales with mastery.
    """
    key = "chart"
    aliases = ["draw"]
    skill = skills.CARTOGRAPHY.value
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
