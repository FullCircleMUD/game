"""
Tests for CmdHunger — verifies the hunger command displays the correct
first-person message based on the character's hunger level.
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_hunger import CmdHunger
from enums.hunger_level import HungerLevel


class TestCmdHunger(EvenniaCommandTest):
    """Test the hunger command displays correct messages."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_hunger_full(self):
        """When FULL, should show the full message."""
        self.char1.hunger_level = HungerLevel.FULL
        self.call(CmdHunger(), "", "You feel completely satisfied and full of energy!")

    def test_hunger_satisfied(self):
        """When SATISFIED, should show the satisfied message."""
        self.char1.hunger_level = HungerLevel.SATISFIED
        self.call(CmdHunger(), "", "You feel well-fed and content.")

    def test_hunger_peckish(self):
        """When PECKISH, should show the peckish message."""
        self.char1.hunger_level = HungerLevel.PECKISH
        self.call(CmdHunger(), "", "You're starting to feel a bit peckish.")

    def test_hunger_hungry(self):
        """When HUNGRY, should show the hungry message."""
        self.char1.hunger_level = HungerLevel.HUNGRY
        self.call(CmdHunger(), "", "Your stomach is growling")

    def test_hunger_famished(self):
        """When FAMISHED, should show the famished message."""
        self.char1.hunger_level = HungerLevel.FAMISHED
        self.call(CmdHunger(), "", "You're famished!")

    def test_hunger_starving(self):
        """When STARVING, should show the starving message."""
        self.char1.hunger_level = HungerLevel.STARVING
        self.call(CmdHunger(), "", "You're starving!")
