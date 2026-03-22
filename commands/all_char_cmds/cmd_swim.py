from evennia import Command

from enums.condition import Condition


class CmdSwim(Command):
    """
    Swim up or down in water.

    Usage:
        swim up / swim down

    Without WATER_BREATHING, a breath timer starts when you go
    underwater. Surface before your air runs out!
    """

    key = "swim"
    aliases = ["sw"]
    locks = "cmd:all()"
    help_category = "Character"

    def parse(self):
        self.direction = self.args.strip().lower()

    def func(self):
        caller = self.caller
        current_level = caller.room_vertical_position
        room = caller.location
        max_depth = getattr(room, "max_depth", 0)

        # Encumbrance check — can't swim when overloaded
        if caller.is_encumbered and max_depth < 0:
            if current_level > max_depth:
                caller.room_vertical_position = max_depth
            caller.msg("|rYou are too heavy! You sink to the bottom!|n")
            if not caller.has_condition(Condition.WATER_BREATHING):
                caller.start_breath_timer()
            return
        elif caller.is_encumbered:
            caller.msg("You are carrying too much to swim.")
            return

        if self.direction in ("down", "d"):

            if current_level > 0:
                caller.msg("You can't swim in air.")
                return

            if current_level <= max_depth:
                if max_depth == 0:
                    caller.msg("You are on dry land, you can't swim in dirt.")
                else:
                    caller.msg("You can't swim any lower here.")
            else:
                caller.msg("You swim lower.")
                caller.room_vertical_position -= 1
                caller.msg(caller.at_look(caller.location))

                # Start breath timer when first going underwater
                if caller.room_vertical_position < 0:
                    if not caller.has_condition(Condition.WATER_BREATHING):
                        caller.start_breath_timer()

        elif self.direction in ("up", "u"):

            if current_level > 0:
                caller.msg("You can't swim in air.")
                return

            if current_level == 0:
                caller.msg("You are already on the surface and can't swim up into the air.")
                return

            caller.room_vertical_position += 1

            if caller.room_vertical_position == 0:
                caller.msg("You swim up and your head breaks the surface.")
                caller.msg(caller.at_look(caller.location))
                # Stop breath timer on surfacing
                caller.stop_breath_timer()
            else:
                caller.msg("You swim upwards.")
                caller.msg(caller.at_look(caller.location))

        else:
            caller.msg(
                f"You can only {self.key} up or down e.g. swim down.\n"
                f"Use regular north, south, east, west for horizontal movement."
            )
