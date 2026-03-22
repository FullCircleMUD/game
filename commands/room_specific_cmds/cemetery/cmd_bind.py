from evennia import Command



class CmdBind(Command):
    """
    Bind your soul to this cemetery.

    Usage:
        bind

    When you die, you will respawn at the cemetery you are bound to.
    You can only bind at a cemetery. Binding to a new cemetery
    replaces your previous binding. Costs gold.
    """

    key = "bind"
    aliases = ["bi", "bin"]
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        room = caller.location

        if caller.home == room:
            caller.msg("You are already bound to this cemetery.")
            return

        cost = room.bind_cost
        if cost > 0:
            if not caller.has_gold(cost):
                caller.msg(
                    f"You need {cost} gold to bind here "
                    f"but only have {caller.get_gold()}."
                )
                return

            caller.return_gold_to_sink(cost)

        caller.home = room
        if cost > 0:
            caller.msg(
                f"You bind your soul to {room.key} for {cost} gold. "
                "You will return here when you die."
            )
        else:
            caller.msg(
                f"You bind your soul to {room.key}. "
                "You will return here when you die."
            )
