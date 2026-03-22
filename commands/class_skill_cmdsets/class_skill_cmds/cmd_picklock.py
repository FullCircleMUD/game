"""
Picklock command — attempt to pick a lock using SUBTERFUGE skill.

Part of the SUBTERFUGE skill (thief/ninja/bard). Calls through to
LockableMixin.picklock() on the target object.

Usage:
    picklock <target>
    pl <target>
"""

from enums.skills_enum import skills
from utils.find_exit_target import find_exit_target
from .cmd_skill_base import CmdSkillBase


class CmdPicklock(CmdSkillBase):
    key = "picklock"
    aliases = ["pl"]
    skill = skills.SUBTERFUGE.value
    help_category = "Stealth"

    def func(self):
        """Override base dispatch — picklock works the same at all mastery levels."""
        caller = self.caller

        if not self.args:
            caller.msg("Pick the lock on what?")
            return

        target_name = self.args.strip()
        target = find_exit_target(caller, target_name)
        if not target:
            return

        if not hasattr(target, "picklock"):
            caller.msg("That doesn't have a lock to pick.")
            return

        if not target.is_locked:
            caller.msg(f"{target.key} is not locked.")
            return

        success, msg = target.picklock(caller)
        caller.msg(msg)

        if success and caller.location:
            caller.location.msg_contents(
                f"$You() $conj(pick) the lock on {target.key}.",
                from_obj=caller, exclude=[caller],
            )

    # Mastery level stubs — not used (func() overridden above)
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
