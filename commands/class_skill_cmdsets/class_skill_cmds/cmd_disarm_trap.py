"""
Disarm trap command — disarm a detected trap using SUBTERFUGE skill.

Part of the SUBTERFUGE skill (thief/ninja/bard). Calls through to
TrapMixin.disarm_trap() on the target object.

Usage:
    disarm <target>
    dis <target>
    disarm floor / ground / plate / room  (for pressure plates)
"""

from enums.skills_enum import skills
from utils.find_exit_target import find_exit_target
from .cmd_skill_base import CmdSkillBase


# Keywords that target the room itself (pressure plates)
_ROOM_KEYWORDS = {"floor", "ground", "plate", "room", "pressure"}


class CmdDisarmTrap(CmdSkillBase):
    key = "disarm"
    aliases = ["dis"]
    skill = skills.SUBTERFUGE.value
    help_category = "Stealth"

    def func(self):
        """Override base dispatch — disarm works the same at all mastery levels."""
        caller = self.caller

        if not self.args:
            caller.msg("Disarm what? Usage: disarm <target>")
            return

        target_name = self.args.strip().lower()
        room = caller.location

        if not room:
            caller.msg("You have nowhere to disarm traps.")
            return

        # Check if targeting the room itself (pressure plates)
        target = None
        if target_name in _ROOM_KEYWORDS:
            if hasattr(room, "is_trapped") and room.is_trapped:
                target = room
            else:
                caller.msg("You don't see a trap here.")
                return
        else:
            # Search room contents and exits for trapped target
            target = self._find_trapped_target(caller, target_name)
            if not target:
                return

        if not hasattr(target, "disarm_trap"):
            caller.msg("That doesn't have a trap to disarm.")
            return

        success, msg = target.disarm_trap(caller)
        caller.msg(msg)

        if success and room:
            desc = getattr(target, "trap_description", "a trap")
            target_str = target.key if target != room else "the room"
            room.msg_contents(
                f"$You() carefully $conj(disarm) {desc} on {target_str}.",
                from_obj=caller, exclude=[caller],
            )

    def _find_trapped_target(self, caller, name):
        """Find a trapped object in the room by name."""
        # Try standard find first
        target = find_exit_target(caller, name)
        if target:
            if not hasattr(target, "is_trapped") or not target.is_trapped:
                caller.msg(f"{target.key} doesn't have a trap.")
                return None
            return target
        # find_exit_target already sent error message
        return None

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
