"""
Picklock command — attempt to pick a lock using SUBTERFUGE skill.

Part of the SUBTERFUGE skill (thief/ninja/bard). Calls through to
LockableMixin.picklock() on the target object.

Usage:
    picklock <target>
    picklock <target> <direction>
    picklock <direction>
"""

from enums.skills_enum import skills
from utils.direction_parser import parse_direction
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import (
    p_can_see, p_is_lockable, p_is_locked, p_same_height,
)
from .cmd_skill_base import CmdSkillBase


class CmdPicklock(CmdSkillBase):
    key = "picklock"
    aliases = []
    skill = skills.SUBTERFUGE.value
    help_category = "Stealth"

    def func(self):
        """Override base dispatch — picklock works the same at all mastery levels."""
        caller = self.caller

        if not self.args:
            caller.msg("Pick the lock on what?")
            return

        # Darkness
        room = caller.location
        if room and hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        target_str = self.args.strip()
        parsed_name, direction = parse_direction(target_str)

        if direction:
            target, _ = resolve_target(
                caller, parsed_name, "items_room_exit_by_direction",
                extra_predicates=(p_can_see,), direction=direction,
            )
        else:
            target, _ = resolve_target(
                caller, target_str, "items_room_all_then_inventory",
                extra_predicates=(p_can_see,),
            )

        if not target:
            caller.msg(f"You don't see '{target_str}' here.")
            return
        if target.location != caller and not p_same_height(caller)(target, caller):
            caller.msg(f"{target.key} is out of reach.")
            return
        if not p_is_lockable(target, caller):
            caller.msg("That doesn't have a lock to pick.")
            return
        if not p_is_locked(target, caller):
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
