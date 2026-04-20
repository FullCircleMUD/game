"""
Stash command — STEALTH class skill (thief, ninja, bard).

Currently stubbed pending redesign. Stash is being reworked from an
active command into a passive group buff: a thief's STEALTH mastery
will passively boost groupmates' hide checks, so the thief's
expertise at finding hiding spots benefits the whole party
automatically.

Usage:
    stash
"""

from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase


class CmdStash(CmdSkillBase):
    """
    Stealth expertise — passive group buff (not yet implemented).

    When implemented, your STEALTH mastery will passively boost
    the hide checks of all group members. The higher your mastery,
    the better your allies can hide when you're with them.

    This replaces the old active stash mechanic. You no longer
    need to manually hide objects or allies — your expertise
    helps your group automatically.

    Usage:
        stash
    """

    key = "stash"
    skill = skills.STEALTH.value
    help_category = "Stealth"

    def func(self):
        self.caller.msg(
            "Stash is being reworked into a passive ability. "
            "When implemented, your STEALTH mastery will passively "
            "boost your group members' hide checks. For now, allies "
            "can use |whide|n themselves."
        )

    # Mastery stubs — not used (func overridden)
    def unskilled_func(self):
        pass

    def basic_func(self):
        pass

    def skilled_func(self):
        pass

    def expert_func(self):
        pass

    def master_func(self):
        pass

    def grandmaster_func(self):
        pass
