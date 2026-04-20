"""
CmdClimb — climb up or down a climbable fixture in the room.

Usage:
    climb up [<target>]
    climb down [<target>]

Requires a ClimbableMixin object in the room. If only one climbable
fixture is present, the target is optional. Moves the character's
room_vertical_position up or down one level within the fixture's
supported heights.

Optional DEX check if the fixture has climb_dc > 0.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from utils.dice_roller import dice
from utils.targeting.predicates import p_can_see


class CmdClimb(FCMCommandMixin, Command):
    """
    Climb up or down a climbable object in the room.

    Usage:
        climb up [<target>]
        climb down [<target>]

    Requires something climbable in the room — a drainpipe, ladder,
    rope, tree, or similar fixture. If there's only one climbable
    object in the room, you don't need to specify a target.
    """

    key = "climb"
    locks = "cmd:all()"
    help_category = "Character"

    def parse(self):
        parts = self.args.strip().lower().split(None, 1)
        self.direction = parts[0] if parts else ""
        self.target_name = parts[1] if len(parts) > 1 else ""

    def func(self):
        caller = self.caller

        # ── Validate direction ──
        if self.direction in ("up", "u"):
            delta = 1
        elif self.direction in ("down", "d"):
            delta = -1
        else:
            caller.msg("Usage: climb up [target] | climb down [target]")
            return

        # ── Guards ──
        if getattr(caller, "position", "standing") not in (
            "standing", "fighting",
        ):
            caller.msg("You need to be standing to climb.")
            return

        if getattr(caller, "is_encumbered", False):
            caller.msg("You are carrying too much to climb.")
            return

        if caller.scripts.get("combat_handler"):
            caller.msg("You can't climb while in combat!")
            return

        room = caller.location
        if not room:
            return

        # Darkness — can't climb what you can't see
        if hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        # ── Find climbable fixtures ──
        climbables = [
            obj for obj in room.contents
            if getattr(obj, "climbable_heights", None)
            and p_can_see(obj, caller)
        ]
        if not climbables:
            caller.msg("There's nothing climbable here.")
            return

        # ── Resolve target ──
        if self.target_name:
            target = caller.search(
                self.target_name, location=room, quiet=True,
            )
            if not target:
                caller.msg(
                    f"You don't see '{self.target_name}' here."
                )
                return
            # caller.search returns a list in quiet mode
            if isinstance(target, list):
                target = target[0]
            if not p_can_see(target, caller):
                caller.msg(
                    f"You don't see '{self.target_name}' here."
                )
                return
            if not getattr(target, "climbable_heights", None):
                caller.msg(f"You can't climb {target.key}.")
                return
        elif len(climbables) == 1:
            target = climbables[0]
        else:
            names = ", ".join(obj.key for obj in climbables)
            caller.msg(
                f"Climb what? You see: {names}"
            )
            return

        # ── Check height bounds ──
        current = caller.room_vertical_position
        desired = current + delta
        heights = target.climbable_heights

        if desired not in heights:
            if delta > 0:
                caller.msg("You can't climb any higher on that.")
            else:
                caller.msg("You can't climb any lower.")
            return

        # Also respect the room's max_height
        max_height = getattr(room, "max_height", 1)
        if desired > max_height:
            caller.msg("You can't climb any higher here.")
            return

        # ── Optional skill check ──
        climb_dc = target.climb_dc or 0
        if climb_dc > 0:
            has_adv = getattr(caller.db, "non_combat_advantage", False)
            has_dis = getattr(
                caller.db, "non_combat_disadvantage", False,
            )
            roll = dice.roll_with_advantage_or_disadvantage(
                advantage=has_adv, disadvantage=has_dis,
            )
            caller.db.non_combat_advantage = False
            caller.db.non_combat_disadvantage = False

            dex_mod = caller.get_attribute_bonus(caller.dexterity)
            total = roll + dex_mod

            if total < climb_dc:
                fail_msg = (
                    target.climb_fail_msg
                    or "You fail to get a grip and slip back."
                )
                caller.msg(f"|r{fail_msg}|n")
                room.msg_contents(
                    f"{caller.key} tries to climb {target.key} "
                    f"but slips back.",
                    exclude=[caller],
                    from_obj=caller,
                )
                return

        # ── Success — move height ──
        caller.room_vertical_position = desired

        if delta > 0:
            msg = (
                target.climb_up_msg or "You climb upwards."
            )
            third = (
                f"{caller.key} climbs up {target.key}."
            )
        else:
            msg = (
                target.climb_down_msg or "You climb downwards."
            )
            third = (
                f"{caller.key} climbs down {target.key}."
            )

        caller.msg(msg)
        room.msg_contents(third, exclude=[caller], from_obj=caller)
        caller.msg(caller.at_look(caller.location))
