from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdMock(CmdSkillBase):
    """
    Mock an enemy to stun them.

    Design notes:
    - Class skill (DEBILITATION) — bard.
    - Contested roll: d20 + mastery bonus + CHA vs target d20 + WIS.
    - Stuns the target on success. Scaling:
      Basic:  stun 1 turn
      Skilled: stun 1 turn (better chance of success)
      Expert:  stun 2 turns
      Master:  stun 2 turns (better chance of success)
      GM:      stun 3 turns
    """
    key = "mock"
    skill = skills.DEBILITATION.value
    help_category = "Combat"

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
