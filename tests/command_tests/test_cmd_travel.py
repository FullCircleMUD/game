"""
Tests for CmdTravel — gateway zone transitions.

evennia test --settings settings tests.command_tests.test_cmd_travel
"""

from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.room_specific_cmds.gateway.cmd_travel import CmdTravel


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdTravel(EvenniaCommandTest):
    """Test the travel command."""

    room_typeclass = "typeclasses.terrain.rooms.room_gateway.RoomGateway"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 100
        self.char1.db.resources = {3: 10}  # 10 bread

        # Create a destination room
        self.dest_room = create_object(
            "typeclasses.terrain.rooms.room_gateway.RoomGateway",
            key="Destination Gateway",
        )

    def _set_destinations(self, destinations):
        """Set destinations on room1."""
        self.room1.destinations = destinations

    def test_travel_no_destinations(self):
        """No destinations configured → error."""
        self._set_destinations([])
        self.call(CmdTravel(), "", "This gateway has no destinations configured.")

    def test_travel_single_dest_no_conditions(self):
        """Single destination, no conditions → auto-travel."""
        self._set_destinations([
            {
                "key": "dest",
                "label": "Destination",
                "destination": self.dest_room,
                "travel_description": "You travel there.",
                "conditions": {},
                "hidden": False,
            },
        ])
        self.call(CmdTravel(), "", "You travel there.")
        self.assertEqual(self.char1.location, self.dest_room)

    def test_travel_list_multiple_dests(self):
        """Multiple destinations, no args → list them."""
        dest2 = create_object(
            "typeclasses.terrain.rooms.room_gateway.RoomGateway",
            key="Second Dest",
        )
        self._set_destinations([
            {
                "key": "beach",
                "label": "The Beach",
                "destination": self.dest_room,
                "conditions": {},
                "hidden": False,
            },
            {
                "key": "arena",
                "label": "The Arena",
                "destination": dest2,
                "conditions": {},
                "hidden": False,
            },
        ])
        result = self.call(CmdTravel(), "")
        self.assertIn("The Beach", result)
        self.assertIn("The Arena", result)
        self.assertIn("travel <destination>", result)

    def test_travel_by_key(self):
        """travel beach → matches by key."""
        dest2 = create_object(
            "typeclasses.terrain.rooms.room_gateway.RoomGateway",
            key="Second Dest",
        )
        self._set_destinations([
            {
                "key": "beach",
                "label": "The Beach",
                "destination": self.dest_room,
                "travel_description": "Sandy shores await.",
                "conditions": {},
                "hidden": False,
            },
            {
                "key": "arena",
                "label": "The Arena",
                "destination": dest2,
                "conditions": {},
                "hidden": False,
            },
        ])
        self.call(CmdTravel(), "beach", "Sandy shores await.")
        self.assertEqual(self.char1.location, self.dest_room)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    def test_travel_food_cost_success(self, mock_craft):
        """Has enough bread → consumed and teleported."""
        self._set_destinations([
            {
                "key": "dest",
                "label": "Destination",
                "destination": self.dest_room,
                "travel_description": "Journey complete.",
                "conditions": {"food_cost": 3},
                "hidden": False,
            },
        ])
        self.call(CmdTravel(), "", "Journey complete.")
        self.assertEqual(self.char1.location, self.dest_room)
        self.assertEqual(self.char1.get_resource(3), 7)  # 10 - 3

    def test_travel_food_cost_fail(self):
        """Insufficient bread → blocked."""
        self.char1.db.resources = {3: 1}
        self._set_destinations([
            {
                "key": "dest",
                "label": "Destination",
                "destination": self.dest_room,
                "conditions": {"food_cost": 5},
                "hidden": False,
            },
        ])
        result = self.call(CmdTravel(), "")
        self.assertIn("requires 5 bread", result)
        self.assertIn("You have 1", result)
        self.assertEqual(self.char1.location, self.room1)

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_travel_gold_cost_success(self, mock_gold):
        """Has enough gold → consumed and teleported."""
        self._set_destinations([
            {
                "key": "dest",
                "label": "Destination",
                "destination": self.dest_room,
                "travel_description": "Paid and travelled.",
                "conditions": {"gold_cost": 10},
                "hidden": False,
            },
        ])
        self.call(CmdTravel(), "", "Paid and travelled.")
        self.assertEqual(self.char1.location, self.dest_room)
        self.assertEqual(self.char1.get_gold(), 90)

    def test_travel_gold_cost_fail(self):
        """Insufficient gold → blocked."""
        self.char1.db.gold = 3
        self._set_destinations([
            {
                "key": "dest",
                "label": "Destination",
                "destination": self.dest_room,
                "conditions": {"gold_cost": 10},
                "hidden": False,
            },
        ])
        result = self.call(CmdTravel(), "")
        self.assertIn("costs 10 gold", result)
        self.assertIn("You have 3", result)

    def test_travel_level_required_fail(self):
        """Below level requirement → blocked."""
        self._set_destinations([
            {
                "key": "dest",
                "label": "Destination",
                "destination": self.dest_room,
                "conditions": {"level_required": 50},
                "hidden": False,
            },
        ])
        result = self.call(CmdTravel(), "")
        self.assertIn("at least level 50", result)

    def test_travel_level_required_success(self):
        """Meets level → teleported."""
        self._set_destinations([
            {
                "key": "dest",
                "label": "Destination",
                "destination": self.dest_room,
                "travel_description": "You are worthy.",
                "conditions": {"level_required": 1},
                "hidden": False,
            },
        ])
        self.call(CmdTravel(), "", "You are worthy.")
        self.assertEqual(self.char1.location, self.dest_room)

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    def test_travel_combined_costs(self, mock_res, mock_gold):
        """Both food + gold → both consumed."""
        self._set_destinations([
            {
                "key": "dest",
                "label": "Destination",
                "destination": self.dest_room,
                "travel_description": "Expensive journey.",
                "conditions": {"food_cost": 2, "gold_cost": 15},
                "hidden": False,
            },
        ])
        self.call(CmdTravel(), "", "Expensive journey.")
        self.assertEqual(self.char1.location, self.dest_room)
        self.assertEqual(self.char1.get_resource(3), 8)
        self.assertEqual(self.char1.get_gold(), 85)

    def test_travel_hidden_dest_not_listed(self):
        """Hidden destination not shown in travel list."""
        self._set_destinations([
            {
                "key": "secret",
                "label": "Secret Island",
                "destination": self.dest_room,
                "conditions": {},
                "hidden": True,
            },
        ])
        result = self.call(CmdTravel(), "")
        self.assertIn("don't know of any destinations", result)

    def test_travel_hidden_dest_with_discovery_tag(self):
        """Discovered destination becomes visible."""
        self._set_destinations([
            {
                "key": "secret",
                "label": "Secret Island",
                "destination": self.dest_room,
                "travel_description": "Found it!",
                "conditions": {},
                "hidden": True,
            },
        ])
        # Add discovery tag
        discovery_tag = f"discovered:{self.room1.key}:secret"
        self.char1.tags.add(discovery_tag, category="discovery")

        self.call(CmdTravel(), "", "Found it!")
        self.assertEqual(self.char1.location, self.dest_room)

    def test_travel_hidden_dest_with_chart_item(self):
        """Chart item reveals hidden destination."""
        self._set_destinations([
            {
                "key": "secret",
                "label": "Secret Island",
                "destination": self.dest_room,
                "travel_description": "The chart leads the way.",
                "conditions": {},
                "hidden": True,
                "discover_item_tag": "chart_secret_island",
            },
        ])
        # Create a chart item in caller's inventory
        chart = create_object(
            "evennia.objects.objects.DefaultObject",
            key="A Nautical Chart",
            location=self.char1,
        )
        chart.tags.add("chart_secret_island", category="chart")

        self.call(CmdTravel(), "", "The chart leads the way.")
        self.assertEqual(self.char1.location, self.dest_room)

    def test_travel_no_match(self):
        """Travel to non-existent destination → error."""
        self._set_destinations([
            {
                "key": "beach",
                "label": "The Beach",
                "destination": self.dest_room,
                "conditions": {},
                "hidden": False,
            },
        ])
        result = self.call(CmdTravel(), "nowhere")
        self.assertIn("No known destination", result)
