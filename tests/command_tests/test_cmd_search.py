"""
Tests for CmdSearch — searching for hidden objects.

evennia test --settings settings tests.command_tests.test_cmd_search
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_search import CmdSearch


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdSearch(EvenniaCommandTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def _make_hidden_fixture(self, find_dc=10):
        obj = create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="hidden chest",
            location=self.room1,
            nohome=True,
        )
        obj.is_hidden = True
        obj.find_dc = find_dc
        return obj

    def test_search_nothing_hidden(self):
        self.call(CmdSearch(), "", "You search but find nothing unusual.")

    @patch("utils.dice_roller.randint", return_value=20)
    def test_search_finds_hidden_object(self, mock_roll):
        self._make_hidden_fixture(find_dc=5)
        # discover() broadcasts room msg first, so startswith matches that
        self.call(CmdSearch(), "", "Char discovers hidden chest")

    @patch("utils.dice_roller.randint", return_value=1)
    def test_search_fails_high_dc(self, mock_roll):
        self._make_hidden_fixture(find_dc=30)
        self.call(CmdSearch(), "", "You search but find nothing unusual.")

    @patch("utils.dice_roller.randint", return_value=15)
    def test_search_discovers_object(self, mock_roll):
        obj = self._make_hidden_fixture(find_dc=5)
        self.call(CmdSearch(), "", "Char discovers hidden chest")
        self.assertFalse(obj.is_hidden)
        self.assertIn(self.char1.key, obj.discovered_by)

    def test_search_already_discovered_not_shown(self):
        """Once discovered, object is no longer hidden — search finds nothing."""
        obj = self._make_hidden_fixture(find_dc=5)
        obj.discover(self.char1)
        self.call(CmdSearch(), "", "You search but find nothing unusual.")
