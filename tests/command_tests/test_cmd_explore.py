"""
Tests for CmdExplore — gateway exploration to discover hidden destinations.

evennia test --settings settings tests.command_tests.test_cmd_explore
"""

from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.room_specific_cmds.gateway.cmd_explore import CmdExplore


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdExplore(EvenniaCommandTest):
    """Test the explore command."""

    room_typeclass = "typeclasses.terrain.rooms.room_gateway.RoomGateway"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 100
        self.char1.db.resources = {3: 5}  # 5 bread

        self.dest_room = create_object(
            "typeclasses.terrain.rooms.room_gateway.RoomGateway",
            key="Hidden Cove",
        )

    def _hidden_dest(self, explore_chance=20, conditions=None):
        """Return a standard hidden destination config."""
        return {
            "key": "hidden_cove",
            "label": "Hidden Cove",
            "destination": self.dest_room,
            "travel_description": "You reach the hidden cove.",
            "conditions": conditions or {},
            "hidden": True,
            "explore_chance": explore_chance,
        }

    def test_explore_no_hidden_dests(self):
        """No hidden destinations → nothing to discover."""
        self.room1.destinations = [
            {
                "key": "visible",
                "label": "Visible Place",
                "destination": self.dest_room,
                "conditions": {},
                "hidden": False,
            },
        ]
        self.call(CmdExplore(), "", "There's nothing new to discover")

    def test_explore_no_bread(self):
        """No bread → can't explore."""
        self.char1.db.resources = {}
        self.room1.destinations = [self._hidden_dest()]
        self.call(CmdExplore(), "", "You need food")

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("random.randint", return_value=10)  # 10 <= 20 = success
    @patch("random.choice", side_effect=lambda x: x[0])
    def test_explore_success_first_roll(self, mock_choice, mock_roll, mock_craft):
        """Success on first roll → 1 bread consumed, discovered, teleported."""
        self.room1.destinations = [self._hidden_dest(explore_chance=20)]

        result = self.call(CmdExplore(), "")
        self.assertIn("discover Hidden Cove", result)
        self.assertEqual(self.char1.location, self.dest_room)
        self.assertEqual(self.char1.get_resource(3), 4)  # 5 - 1

        # Discovery tag should be set
        tag = f"discovered:{self.room1.key}:hidden_cove"
        self.assertTrue(self.char1.tags.get(tag, category="discovery"))

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("random.randint", side_effect=[90, 90, 15])  # fail, fail, success
    @patch("random.choice", side_effect=lambda x: x[0])
    def test_explore_success_third_roll(self, mock_choice, mock_roll, mock_craft):
        """Success on third roll → 3 bread consumed."""
        self.room1.destinations = [self._hidden_dest(explore_chance=20)]

        result = self.call(CmdExplore(), "")
        self.assertIn("After 3 days", result)
        self.assertEqual(self.char1.location, self.dest_room)
        self.assertEqual(self.char1.get_resource(3), 2)  # 5 - 3

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("random.randint", return_value=90)  # always fail
    @patch("random.choice", side_effect=lambda x: x[0])
    def test_explore_failure_all_rolls(self, mock_choice, mock_roll, mock_craft):
        """All rolls fail → all bread consumed, stays put."""
        self.room1.destinations = [self._hidden_dest(explore_chance=20)]

        result = self.call(CmdExplore(), "")
        self.assertIn("find nothing", result)
        self.assertEqual(self.char1.location, self.room1)
        self.assertEqual(self.char1.get_resource(3), 0)  # all 5 consumed

    def test_explore_already_discovered(self):
        """Already discovered destination → nothing new."""
        self.room1.destinations = [self._hidden_dest()]
        tag = f"discovered:{self.room1.key}:hidden_cove"
        self.char1.tags.add(tag, category="discovery")

        self.call(CmdExplore(), "", "There's nothing new to discover")

    def test_explore_conditions_not_met(self):
        """Can't explore dest you don't meet conditions for."""
        self.room1.destinations = [
            self._hidden_dest(conditions={"level_required": 99}),
        ]
        self.call(CmdExplore(), "", "There's nothing new to discover")
