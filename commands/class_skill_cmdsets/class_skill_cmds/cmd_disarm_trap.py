"""
Disarm trap command — disarm a detected trap using SUBTERFUGE skill.

Part of the SUBTERFUGE skill (thief/ninja/bard). Calls through to
TrapMixin.disarm_trap() on the target object.

Usage:
    disarm <target>
    disarm <target> <direction>
    disarm <direction>

If no object or exit matches, checks the room itself (pressure plates).
"""

from enums.skills_enum import skills
from utils.direction_parser import parse_direction
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see, p_same_height
from .cmd_skill_base import CmdSkillBase


class CmdDisarmTrap(CmdSkillBase):
    key = "disarm"
    aliases = []
    skill = skills.SUBTERFUGE.value
    help_category = "Stealth"

    def func(self):
        """Override base dispatch — disarm works the same at all mastery levels."""
        caller = self.caller

        if not self.args:
            caller.msg("Disarm what? Usage: disarm <target>")
            return

        # Darkness
        room = caller.location
        if not room:
            caller.msg("You have nowhere to disarm traps.")
            return
        if hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        target_str = self.args.strip()
        parsed_name, direction = parse_direction(target_str)

        if direction:
            # Direction-qualified: exit only
            target, _ = resolve_target(
                caller, parsed_name, "items_room_exit_by_direction",
                extra_predicates=(p_can_see,), direction=direction,
            )
        else:
            # No direction: room contents first, room itself as fallback.
            # If nothing in the room matches by name, the room itself is
            # returned — the command checks if the room is trapped.
            target, _ = resolve_target(
                caller, target_str, "items_room_all_then_room",
                extra_predicates=(p_can_see,),
            )

        if not target:
            caller.msg(f"You don't see '{target_str}' here.")
            return

        # Room fallback — only valid if the room is trapped
        if target == room:
            if not hasattr(room, "is_trapped") or not room.is_trapped:
                caller.msg(f"You don't see '{target_str}' here.")
                return
        else:
            # Height check — non-room targets must be at same height
            if not p_same_height(caller)(target, caller):
                caller.msg(f"{target.key} is out of reach.")
                return

        if not hasattr(target, "disarm_trap"):
            caller.msg("That doesn't have a trap to disarm.")
            return

        if not getattr(target, "is_trapped", False):
            caller.msg(f"{target.key} doesn't have a trap.")
            return

        success, msg = target.disarm_trap(caller)
        caller.msg(msg)

        if success and room:
            desc = getattr(target, "trap_description", "a trap")
            target_label = target.key if target != room else "the room"
            room.msg_contents(
                f"$You() carefully $conj(disarm) {desc} on {target_label}.",
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
