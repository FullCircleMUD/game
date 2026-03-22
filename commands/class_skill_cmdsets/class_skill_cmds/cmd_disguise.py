from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdDisguise(CmdSkillBase):
    """
    Disguise yourself to appear as someone else.

    Design notes:
    - Class skill (MISDIRECTION) — bard.
    - Change appearance so mobs/NPCs don't recognise you.
    - Can appear as a different race, class, or faction member.
    - Duration and convincingness scale with mastery.
    """
    key = "disguise"
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
