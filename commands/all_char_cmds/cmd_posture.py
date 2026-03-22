"""
Posture commands — sit, rest, sleep, stand, wake.

Position affects room display, regen rate, and movement ability.
Standing is required to move between rooms.
"""

from evennia import Command


class _PostureCommand(Command):
    """Base class for posture commands with shared logic."""

    locks = "cmd:all()"
    help_category = "General"
    target_position = "standing"  # subclasses override

    def _is_in_combat(self):
        """Check if the caller is currently fighting."""
        return self.caller.position == "fighting"

    def func(self):
        caller = self.caller
        target = self.target_position

        if self._is_in_combat():
            caller.msg("You can't do that while fighting!")
            return

        if caller.position == target:
            caller.msg(f"You are already {target}.")
            return

        caller.position = target
        caller.msg(self.self_msg)
        if caller.location:
            caller.location.msg_contents(
                self.room_msg.format(name=caller.key),
                exclude=[caller],
                from_obj=caller,
            )


class CmdSit(_PostureCommand):
    """
    Sit down.

    Usage:
        sit

    Sitting does not increase regen rate but you must stand to move.
    """
    key = "sit"
    target_position = "sitting"
    self_msg = "You sit down."
    room_msg = "{name} sits down."


class CmdRest(_PostureCommand):
    """
    Rest and recover faster.

    Usage:
        rest

    Resting doubles your HP, mana, and movement regeneration rate.
    You must stand before you can move.
    """
    key = "rest"
    target_position = "resting"
    self_msg = "You sit down and rest."
    room_msg = "{name} sits down and rests."


class CmdSleep(_PostureCommand):
    """
    Go to sleep for maximum recovery.

    Usage:
        sleep

    Sleeping triples your HP, mana, and movement regeneration rate,
    but you can't see the room or act until you wake up.
    You must wake before you can move.
    """
    key = "sleep"
    target_position = "sleeping"
    self_msg = "You lie down and go to sleep."
    room_msg = "{name} lies down and goes to sleep."


class CmdStand(_PostureCommand):
    """
    Stand up.

    Usage:
        stand

    Stand up from sitting, resting, or sleeping. Required before
    you can move between rooms.
    """
    key = "stand"
    target_position = "standing"
    self_msg = "You stand up."
    room_msg = "{name} stands up."


class CmdWake(Command):
    """
    Wake up from sleeping.

    Usage:
        wake

    Wakes you up and puts you in a standing position.
    """
    key = "wake"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        if caller.position != "sleeping":
            caller.msg("You aren't asleep.")
            return
        caller.position = "standing"
        caller.msg("You wake up and stand.")
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} wakes up and stands.",
                exclude=[caller],
                from_obj=caller,
            )
