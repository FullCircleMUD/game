from evennia import Command

from commands.command import FCMCommandMixin
from enums.condition import Condition


class CmdFly(FCMCommandMixin, Command):
    """
    Fly up or down in a room.

    Usage:
        fly up / fly down

    Requires the FLY condition (from a spell, potion, or magic item).
    """

    key = "fly"
    aliases = []
    locks = "cmd:all()"
    help_category = "Character"

    def parse(self):
        """
        Separates the command input into first word and args.
        self.args is the raw string after the command key.
        """
        self.direction = self.args.strip().lower()

    def func(self):
        if not self.caller.has_condition(Condition.FLY):
            self.caller.msg("You can't fly.")
            return

        # Encumbrance check — can't fly when overloaded
        if self.caller.is_encumbered:
            if self.caller.room_vertical_position > 0:
                self.caller.msg("|rYou are carrying too much to stay airborne!|n")
                self.caller._check_fall()
            else:
                self.caller.msg("You are carrying too much to fly.")
            return

        current_level = self.caller.room_vertical_position
        room = self.caller.location
        max_height = getattr(room, "max_height", 0)
        max_depth = getattr(room, "max_depth", 0)

        """
        self.caller.msg(f"\n{self.key} command entered")
        self.caller.msg(f"vertical position {current_level}")
        self.caller.msg(f"direction {self.direction}")
        self.caller.msg(f"room {room}")

        self.caller.msg(f"room max height: {max_height}")
        self.caller.msg(f"room max depth: {max_depth}")
        """
   
        # Thorn whip hold blocks all height changes
        if hasattr(self.caller, "has_effect") and self.caller.has_effect("thorn_whip_held"):
            self.caller.msg("|rThorny vines hold you in place! You can't change height!|n")
            return

        if self.direction == "up" or self.direction == "u":

            if current_level < 0:
                # regardless of whether it is up or down
                self.caller.msg(f"\nYou can't fly in water")
                return

            # neccessarily on the surface or higher
            if current_level == max_height:
                self.caller.msg(f"\nYou can't fly any higher here")
            else:
                self.caller.msg(f"\nYou fly upwards")
                self.caller.room_vertical_position += 1
                self.caller.msg(self.caller.at_look(self.caller.location))

        elif self.direction == "down" or self.direction == "d":

            if current_level < 0:
                # regardless of whether it is up or down
                self.caller.msg(f"\nYou can't fly in water")
                return

            # neccessarily on the surface or higher
            if current_level == 0:
                if max_depth == 0:
                    self.caller.msg(f"\nYou are already on the ground")
                else:
                    self.caller.msg(f"\nYou are on the waters surface and can't fly down further")
            # must be at least 1 in the air
            else:
                self.caller.room_vertical_position -= 1
                if self.caller.room_vertical_position > 0:
                    self.caller.msg(f"\nYou fly lower")
                    self.caller.msg(self.caller.at_look(self.caller.location))
                elif max_depth == 0:
                    self.caller.msg(f"\nYou fly down to the ground")
                    self.caller.msg(self.caller.at_look(self.caller.location))
                else:
                    self.caller.msg(f"\nYou descend to the waters surface")
                    self.caller.msg(self.caller.at_look(self.caller.location))

        # direction not up or down
        else:
            self.caller.msg(f"\nYou can only {self.key} up or down e.g. fly up.\nuse regular north, south, eats west for horizontal movement.")

