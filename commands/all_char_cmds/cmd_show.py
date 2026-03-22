"""
Show command — share your discovery of a hidden object with another player.

Adds the target player to the object's `discovered_by` set so they can
see it without needing to search for it themselves.

Usage:
    show <object> to <character>
    show <object> <character>
"""

from evennia import Command

from typeclasses.mixins.hidden_object import HiddenObjectMixin


class CmdShow(Command):
    """
    Point out a hidden object to another player.

    Usage:
        show <object> to <character>
        show <object> <character>

    If you've discovered something hidden in the room, you can
    show it to another character so they can see it too.
    """

    key = "show"
    locks = "cmd:all()"
    help_category = "Items"
    arg_regex = r"\s|$"

    def func(self):
        caller = self.caller
        room = caller.location

        if not room:
            return

        args = self.args.strip() if self.args else ""
        if not args:
            caller.msg("Usage: show <object> to <character>")
            return

        # Parse: "obj to char" or "obj char"
        if " to " in args:
            obj_str, char_str = args.split(" to ", 1)
        else:
            parts = args.rsplit(None, 1)
            if len(parts) < 2:
                caller.msg("Usage: show <object> to <character>")
                return
            obj_str, char_str = parts

        obj_str = obj_str.strip()
        char_str = char_str.strip()
        if not obj_str or not char_str:
            caller.msg("Usage: show <object> to <character>")
            return

        # Find the object in the room
        target_obj = caller.search(obj_str, location=room, quiet=True)
        if target_obj:
            target_obj = target_obj[0]
        else:
            caller.msg(f"Could not find '{obj_str}'.")
            return

        # Info-leak prevention: if the object is hidden and the caller
        # can't see it, pretend it doesn't exist
        if (
            isinstance(target_obj, HiddenObjectMixin)
            and not target_obj.is_hidden_visible_to(caller)
        ):
            caller.msg(f"Could not find '{obj_str}'.")
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
        target_char = caller.search(char_str, location=room)
        if not target_char:
            return

        # Can't show to yourself
        if target_char == caller:
            caller.msg("You already know about that.")
            return

        # Target must have a character_key (i.e. be a player character or NPC)
        char_key = target_obj._get_character_key(target_char)
        if not char_key:
            caller.msg("You can only show things to other characters.")
            return

        # Check if target has already discovered it
        if char_key in set(target_obj.discovered_by):
            caller.msg(
                f"{target_char.key} has already found {target_obj.key}."
            )
            return

        # Add target to discovered_by set
        discovered = set(target_obj.discovered_by)
        discovered.add(char_key)
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
