"""
Show command — share your discovery of a hidden object with another player.

Adds the target player to the object's `discovered_by` set so they can
see it without needing to search for it themselves.

Usage:
    show <object> to <character>
"""

from evennia import Command

from commands.command import FCMCommandMixin
from typeclasses.mixins.hidden_object import HiddenObjectMixin
from utils.targeting.helpers import resolve_character_in_room, resolve_target
from utils.targeting.predicates import p_can_see


class CmdShow(FCMCommandMixin, Command):
    """
    Point out a hidden object to another player.

    Usage:
        show <object> to <character>

    If you've discovered something hidden in the room, you can
    show it to another character so they can see it too.
    """

    key = "show"
    locks = "cmd:all()"
    help_category = "Items"
    arg_regex = r"\s|$"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller
        room = caller.location

        if not room:
            return

        args = self.args.strip() if self.args else ""
        if not args or " to " not in args:
            caller.msg("Usage: show <object> to <character>")
            return

        obj_str, char_str = args.split(" to ", 1)
        obj_str = obj_str.strip()
        char_str = char_str.strip()
        if not obj_str or not char_str:
            caller.msg("Usage: show <object> to <character>")
            return

        # Darkness — can't see what you're pointing out
        if hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        # Find the object in the room — p_can_see handles info-leak
        # prevention: undiscovered hidden objects are filtered out
        target_obj, _ = resolve_target(
            caller, obj_str, "items_room_nonexit",
            extra_predicates=(p_can_see,),
        )
        if not target_obj:
            caller.msg(f"You don't see '{obj_str}' here.")
            return

        # Must be a hidden-type object
        if not isinstance(target_obj, HiddenObjectMixin):
            caller.msg("That's not something you need to point out.")
            return

        # If the object isn't currently hidden, everyone can already see it
        if not target_obj.is_hidden:
            caller.msg("That's already visible to everyone.")
            return

        # Find the target character in the room
        target_char = resolve_character_in_room(caller, char_str)
        if not target_char:
            caller.msg(
                f"You don't see a character called '{char_str}' here."
            )
            return

        # Can't show to yourself
        if target_char == caller:
            caller.msg("You already know about that.")
            return

        # Check if target has already discovered it
        if target_char.key in set(target_obj.discovered_by):
            caller.msg(
                f"{target_char.key} has already found {target_obj.key}."
            )
            return

        # Add target to discovered_by set
        discovered = set(target_obj.discovered_by)
        discovered.add(target_char.key)
        target_obj.discovered_by = discovered

        # Messages
        caller.msg(
            f"|gYou point out {target_obj.key} to {target_char.key}.|n"
        )
        target_char.msg(
            f"|g{caller.key} points out {target_obj.key} to you.|n"
        )
        if room:
            room.msg_contents(
                f"$You() $conj(point) out something to {target_char.key}.",
                from_obj=caller,
                exclude=[caller, target_char],
            )
