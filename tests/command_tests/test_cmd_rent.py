"""
Tests for CmdRent — safe logout at an inn.

evennia test --settings settings tests.command_tests.test_cmd_rent
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.room_specific_cmds.inn.cmd_rent import CmdRent


class TestCmdRent(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_rent_blocked_in_combat(self):
        """Rent is refused when character has a combat_handler script."""
        with patch.object(
            self.char1.scripts, "get", return_value=[MagicMock()]
        ):
            self.call(
                CmdRent(), "",
                "You can't rent a room while in combat!",
            )

    def test_rent_shows_safe_message(self):
        """Rent should confirm belongings are safe."""
        with patch.object(
            self.char1.scripts, "get", return_value=[]
        ):
            result = self.call(CmdRent(), "")
            self.assertIn("belongings are safe", result)

    def test_rent_records_last_rent_location(self):
        """Renting must persist the inn as db.last_rent_location so reconnect
        can restore the character there even if the live location FK is
        invalidated (e.g. by a world rebuild)."""
        self.assertIsNone(self.char1.db.last_rent_location)

        with patch.object(self.char1.scripts, "get", return_value=[]):
            self.call(CmdRent(), "")

        self.assertEqual(self.char1.db.last_rent_location, self.room1)

    def test_rent_does_not_change_home(self):
        """home is Evennia plumbing, not the rent/respawn spot — rent must
        leave it alone."""
        original_home = self.char1.home

        with patch.object(self.char1.scripts, "get", return_value=[]):
            self.call(CmdRent(), "")

        self.assertEqual(self.char1.home, original_home)

    def test_second_rent_overwrites_first(self):
        """Renting at a new inn replaces the previous rent location."""
        with patch.object(self.char1.scripts, "get", return_value=[]):
            self.call(CmdRent(), "")
        self.assertEqual(self.char1.db.last_rent_location, self.room1)

        self.char1.location = self.room2
        with patch.object(self.char1.scripts, "get", return_value=[]):
            self.call(CmdRent(), "")
        self.assertEqual(self.char1.db.last_rent_location, self.room2)

    def test_reconnect_restores_rent_location_over_home(self):
        """End-to-end: if the live location FK is lost (e.g. world rebuild),
        at_pre_puppet must put the character back at their last rent
        location, not at home."""
        # Rent at room1 -> last_rent_location is recorded.
        with patch.object(self.char1.scripts, "get", return_value=[]):
            self.call(CmdRent(), "")
        self.assertEqual(self.char1.db.last_rent_location, self.room1)

        # Simulate the rebuild-induced broken location FK and a distinct home.
        self.char1.home = self.room2
        self.char1.location = None

        self.char1.at_pre_puppet(self.account)

        self.assertEqual(self.char1.location, self.room1)
        self.assertNotEqual(self.char1.location, self.char1.home)
