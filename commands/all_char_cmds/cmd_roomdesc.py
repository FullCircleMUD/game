"""
Command for players to set their room description — the short sentence
shown in the room's character list when other players see them.

    roomdesc                     — show current room description
    roomdesc <text>              — set a new room description
    roomdesc clear               — reset to default

Use ``{name}`` in the text to insert your character name automatically.
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdRoomDesc(FCMCommandMixin, Command):
    """
    Set the short description shown when others see you in a room.

    Usage:
        roomdesc                 - show your current room description
        roomdesc <description>   - set a new room description
        roomdesc clear           - reset to the default

    Your room description is the sentence other players see in the room's
    character list. Use {name} to insert your character name.

    Examples:
        roomdesc A tall warrior leans against the wall here.
        roomdesc {name} the wandering bard rests here, tuning a lute.
        roomdesc clear
    """

    key = "roomdesc"
    locks = "cmd:all()"
    help_category = "Character"
    allow_while_sleeping = True

    MAX_LENGTH = 200

    def func(self):
        caller = self.caller

        if not self.args:
            # Show current room description
            desc = caller.get_room_description()
            if caller.room_description:
                caller.msg(f"|wYour room description:|n {desc}")
            else:
                caller.msg(f"|wYour room description (default):|n {desc}")
            return

        text = self.args.strip()

        if text.lower() == "clear":
            caller.room_description = None
            caller.msg(
                f"|wRoom description reset to default:|n "
                f"{caller.get_room_description()}"
            )
            return

        if len(text) > self.MAX_LENGTH:
            caller.msg(
                f"|rRoom description too long ({len(text)} chars). "
                f"Maximum is {self.MAX_LENGTH}.|n"
            )
            return

        caller.room_description = text
        caller.msg(
            f"|wRoom description set to:|n {caller.get_room_description()}"
        )
