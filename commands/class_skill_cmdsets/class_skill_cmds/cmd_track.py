from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdTrack(CmdSkillBase):
    """
    Track a creature by following its trail.

    Design notes:
    - Class skill (SURVIVALIST) — druid, ranger.
    - Follow a creature's trail through the wilderness.
    - Success chance and tracking range scale with mastery.
    """
    key = "track"
    skill = skills.SURVIVALIST.value
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
