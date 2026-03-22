from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdTurn(CmdSkillBase):
    """
    Turn undead — stun or destroy undead creatures.

    Design notes:
    - Class skill (TURN_UNDEAD) — cleric, paladin.
    - Stuns undead mobs scaling with their hit dice.
    - At higher mastery levels, destroys rather than stuns.
    - Affects more and tougher undead at higher mastery.
    """
    key = "turn"
    skill = skills.TURN_UNDEAD.value
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
