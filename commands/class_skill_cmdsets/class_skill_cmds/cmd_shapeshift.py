from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

class CmdShapeshift(CmdSkillBase):
    """
    Transform into an animal form.

    Design notes:
    - Class skill (SHAPE_SHIFTING) — druid.
    - Syntax: shapeshift <form> / ss bear
    - Available forms and their power scale with mastery:
      Basic = small forms (cat, rat, snake)
      Skilled = medium forms (wolf, hawk)
      Expert = large forms (bear, panther)
      Master = powerful forms (dire wolf, giant eagle)
      GM = legendary forms (dragon?)
    """
    key = "shapeshift"
    aliases = ["ss"]
    skill = skills.SHAPE_SHIFTING.value
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
