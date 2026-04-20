"""
XPButton — a dev/test fixture that awards XP when pressed.

Place in a room and players can use `press button` to gain XP.
"""

from evennia import AttributeProperty, CmdSet, Command

from enums.size import Size
from typeclasses.world_objects.base_fixture import WorldFixture


class CmdPressButton(Command):
    """
    Press the big red button.

    Usage:
        press button
        press
    """

    key = "press"
    aliases = ["press button", "push button", "push", "click", "click button"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        from utils.experience_table import get_xp_for_next_level
        xp_needed = get_xp_for_next_level(caller.total_level)
        if xp_needed <= 0:
            caller.msg("|rYou press the button but nothing happens. You're already max level!|n")
            return
        xp = max(1, xp_needed - caller.experience_points)
        caller.at_gain_experience_points(xp)
        caller.msg(f"|rYou slam your fist down on the big red button!|n")
        caller.msg(f"|yYou gain {xp} experience points!|n")
        caller.location.msg_contents(
            f"$You() $conj(slam) a fist down on the big red button!",
            from_obj=caller,
            exclude=[caller],
        )


class CmdSetXPButton(CmdSet):
    key = "XPButtonCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdPressButton())


class XPButton(WorldFixture):
    """
    A big red button that awards XP when pressed. Dev/test only.
    """

    size = AttributeProperty(Size.TINY.value)
    xp_amount = AttributeProperty(1000)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetXPButton, persistent=True)
        self.locks.add("call:true()")

    def return_appearance(self, looker, **kwargs):
        name = self.get_display_name(looker)
        return (
            f"|w{name}|n\n"
            f"A large, candy-red button mounted on a brass pedestal. "
            f"It practically begs to be pressed. A small plaque reads: "
            f"|y'PRESS TO LEVEL UP'|n."
        )
