from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdExplore(CmdSkillBase):
    """
    Set sail on a voyage of exploration.

    Design notes:
    - General skill (SEAMANSHIP) — available to all characters.
    - Random voyage to discover new ports within the ship's range.
    - Chance of finding nothing and returning to home port.
    - Same pre-sail validation as the sail command (bread, ship, crew, etc.).
    - Discovery chance and range scale with mastery.
    """
    key = "explore"
    skill = skills.SEAMANSHIP.value
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
