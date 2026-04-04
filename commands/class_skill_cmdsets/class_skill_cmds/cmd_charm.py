from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdCharm(CmdSkillBase):
    """
    Charm a mob or NPC into following you.

    Design notes:
    - Class skill (MANIPULATION) — bard.
    - Charmed mob/NPC acts as a temporary NPC follower for the duration.
    - When charm wears off, the target KNOWS they were charmed and their
      regard/reputation toward the charmer drops.
    - Contested CHA + mastery vs target WIS.
    - Duration and target difficulty scale with mastery.
    """
    key = "charm"
    skill = skills.MANIPULATION.value
    help_category = "Performance"
    allow_while_sleeping = True

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
