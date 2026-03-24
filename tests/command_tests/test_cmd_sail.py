"""
Tests for the sail command (sea travel via dock gateway rooms).

evennia test --settings settings tests.command_tests.test_cmd_sail
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.class_skill_cmdsets.class_skill_cmds.cmd_sail import CmdSail
from commands.room_specific_cmds.gateway.cmd_travel import _check_boat_level
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from typeclasses.terrain.rooms.room_gateway import RoomGateway

PATCH_DELAY = "commands.room_specific_cmds.gateway.cmd_travel.delay"


def _instant_delay(seconds, callback, *args, **kwargs):
    """Mock for utils.delay — executes callback immediately."""
    callback(*args, **kwargs)


# Patch the module-level helper in cmd_sail (not the old BaseNFTItem static methods)
PATCH_QUALIFYING = (
    "commands.class_skill_cmdsets.class_skill_cmds.cmd_sail._get_qualifying_ships"
)


def _mock_ship(key, tier):
    """Create a mock ShipNFTItem for sail tests."""
    ship = MagicMock()
    ship.key = key
    ship.ship_tier = tier
    ship.arrive_at_dock = MagicMock()
    return ship


class TestSailGates(EvenniaCommandTest):
    """Test sail command gate checks."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_gateway.RoomGateway"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.dest_room = create.create_object(
            RoomGateway, key="Far Dock",
        )
        self.room1.destinations = [
            {
                "key": "far_dock",
                "label": "The Far Dock",
                "destination": self.dest_room,
                "travel_description": "You sail away...",
                "conditions": {"boat_level": 1, "food_cost": 1},
                "hidden": False,
            },
        ]

    def tearDown(self):
        if self.dest_room:
            self.dest_room.delete()
        super().tearDown()

    def _set_seamanship(self, char, level):
        if not char.db.skill_mastery_levels:
            char.db.skill_mastery_levels = {}
        char.db.skill_mastery_levels[skills.SEAMANSHIP.value] = level.value

    def test_unskilled_blocked(self):
        """Unskilled seamanship blocks sailing."""
        self._set_seamanship(self.char1, MasteryLevel.UNSKILLED)
        result = self.call(CmdSail(), "")
        self.assertIn("no knowledge", result)

    def test_not_at_dock(self):
        """Sail from a room with no destinations."""
        self._set_seamanship(self.char1, MasteryLevel.BASIC)
        self.room1.destinations = []
        result = self.call(CmdSail(), "")
        self.assertIn("no sea routes", result)

    def test_no_sail_destinations(self):
        """Gateway with only food_cost destinations (no boat_level)."""
        self._set_seamanship(self.char1, MasteryLevel.BASIC)
        self.room1.destinations = [
            {
                "key": "overland",
                "label": "Overland Path",
                "destination": self.dest_room,
                "travel_description": "You walk...",
                "conditions": {"food_cost": 1},
                "hidden": False,
            },
        ]
        result = self.call(CmdSail(), "")
        self.assertIn("no sea routes", result)

    @patch(PATCH_QUALIFYING, return_value=[])
    def test_no_ship(self, mock_ships):
        """Player owns no ships."""
        self._set_seamanship(self.char1, MasteryLevel.BASIC)
        self.char1.db.resources = {3: 10}
        result = self.call(CmdSail(), "")
        self.assertIn("qualifying ships", result)

    @patch(PATCH_QUALIFYING, return_value=[])
    def test_ship_too_small(self, mock_ships):
        """Player has no ships meeting the tier requirement."""
        self._set_seamanship(self.char1, MasteryLevel.BASIC)
        self.char1.db.resources = {3: 10}
        self.room1.destinations[0]["conditions"]["boat_level"] = 3
        result = self.call(CmdSail(), "")
        self.assertIn("EXPERT", result)  # needed tier


class TestSailSuccess(EvenniaCommandTest):
    """Test successful sailing scenarios."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_gateway.RoomGateway"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self._delay_patcher = patch(PATCH_DELAY, side_effect=_instant_delay)
        self._delay_patcher.start()
        self.dest_room = create.create_object(
            RoomGateway, key="Far Dock",
        )
        self.dest_room2 = create.create_object(
            RoomGateway, key="Another Dock",
        )
        self.room1.destinations = [
            {
                "key": "far_dock",
                "label": "The Far Dock",
                "destination": self.dest_room,
                "travel_description": "You sail away...",
                "conditions": {"boat_level": 1, "food_cost": 1},
                "hidden": False,
            },
        ]
        self._set_seamanship(self.char1, MasteryLevel.BASIC)
        self.char1.db.resources = {3: 5}

    def tearDown(self):
        self._delay_patcher.stop()
        if self.dest_room:
            self.dest_room.delete()
        if self.dest_room2:
            self.dest_room2.delete()
        super().tearDown()

    def _set_seamanship(self, char, level):
        if not char.db.skill_mastery_levels:
            char.db.skill_mastery_levels = {}
        char.db.skill_mastery_levels[skills.SEAMANSHIP.value] = level.value

    @patch(PATCH_QUALIFYING, return_value=[_mock_ship("Cog", 1)])
    def test_sail_single_ship_auto(self, mock_ships):
        """Single qualifying ship auto-selects and sails."""
        result = self.call(CmdSail(), "")
        self.assertIn("board your Cog", result)
        self.assertIn("sail away", result)
        self.assertEqual(self.char1.location, self.dest_room)

    @patch(PATCH_QUALIFYING, return_value=[_mock_ship("Cog", 1)])
    def test_sail_named_destination(self, mock_ships):
        """Sail to a named destination."""
        result = self.call(CmdSail(), "far_dock")
        self.assertIn("sail away", result)
        self.assertEqual(self.char1.location, self.dest_room)

    @patch(PATCH_QUALIFYING, return_value=[_mock_ship("Cog", 1)])
    def test_sail_label_prefix(self, mock_ships):
        """Match by label prefix."""
        result = self.call(CmdSail(), "The Far")
        self.assertIn("sail away", result)
        self.assertEqual(self.char1.location, self.dest_room)

    @patch(PATCH_QUALIFYING, return_value=[_mock_ship("Cog", 1)])
    def test_sail_no_match(self, mock_ships):
        """No destination matches input."""
        result = self.call(CmdSail(), "nowhere")
        self.assertIn("No known destination", result)

    @patch(PATCH_QUALIFYING, return_value=[_mock_ship("Cog", 1)])
    def test_list_destinations(self, mock_ships):
        """Multiple destinations lists them."""
        self.room1.destinations.append(
            {
                "key": "another_dock",
                "label": "Another Dock",
                "destination": self.dest_room2,
                "travel_description": "You sail elsewhere...",
                "conditions": {"boat_level": 1, "food_cost": 2},
                "hidden": False,
            },
        )
        result = self.call(CmdSail(), "")
        self.assertIn("Sea Routes", result)
        self.assertIn("The Far Dock", result)
        self.assertIn("Another Dock", result)


class TestSailShipSelection(EvenniaCommandTest):
    """Test the ship selection flow with multiple qualifying ships."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_gateway.RoomGateway"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self._delay_patcher = patch(PATCH_DELAY, side_effect=_instant_delay)
        self._delay_patcher.start()
        self.dest_room = create.create_object(
            RoomGateway, key="Far Dock",
        )
        self.room1.destinations = [
            {
                "key": "far_dock",
                "label": "The Far Dock",
                "destination": self.dest_room,
                "travel_description": "You sail away...",
                "conditions": {"boat_level": 1, "food_cost": 1},
                "hidden": False,
            },
        ]
        self._set_seamanship(self.char1, MasteryLevel.BASIC)
        self.char1.db.resources = {3: 5}
        # Use distinct ship names so we can assert which ship was selected
        self.multi_ships = [
            _mock_ship("Grey Widow", 1),
            _mock_ship("Sea Dragon", 1),
            _mock_ship("Blue Pearl", 2),
        ]

    def tearDown(self):
        self._delay_patcher.stop()
        if self.dest_room:
            self.dest_room.delete()
        super().tearDown()

    def _set_seamanship(self, char, level):
        if not char.db.skill_mastery_levels:
            char.db.skill_mastery_levels = {}
        char.db.skill_mastery_levels[skills.SEAMANSHIP.value] = level.value

    @patch(PATCH_QUALIFYING)
    def test_multiple_ships_shows_list(self, mock_ships):
        """Multiple ships shows selection list."""
        mock_ships.return_value = self.multi_ships
        result = self.call(CmdSail(), "far_dock")
        self.assertIn("Choose Your Ship", result)
        self.assertIn("Grey Widow", result)
        self.assertIn("Sea Dragon", result)
        self.assertIn("Blue Pearl", result)
        # Player should NOT have moved
        self.assertEqual(self.char1.location, self.room1)

    @patch(PATCH_QUALIFYING)
    def test_select_ship_by_number(self, mock_ships):
        """Sail with a specific ship choice (ship #2 = Sea Dragon)."""
        mock_ships.return_value = self.multi_ships
        result = self.call(CmdSail(), "far_dock 2")
        self.assertIn("Sea Dragon", result)
        self.assertEqual(self.char1.location, self.dest_room)

    @patch(PATCH_QUALIFYING)
    def test_select_first_ship(self, mock_ships):
        """Selecting ship 1 works (Grey Widow)."""
        mock_ships.return_value = self.multi_ships
        result = self.call(CmdSail(), "far_dock 1")
        self.assertIn("Grey Widow", result)
        self.assertEqual(self.char1.location, self.dest_room)

    @patch(PATCH_QUALIFYING)
    def test_select_last_ship(self, mock_ships):
        """Selecting the last ship works (Blue Pearl)."""
        mock_ships.return_value = self.multi_ships
        result = self.call(CmdSail(), "far_dock 3")
        self.assertIn("Blue Pearl", result)
        self.assertEqual(self.char1.location, self.dest_room)

    @patch(PATCH_QUALIFYING)
    def test_invalid_ship_number_too_high(self, mock_ships):
        """Ship number out of range."""
        mock_ships.return_value = self.multi_ships
        result = self.call(CmdSail(), "far_dock 99")
        self.assertIn("Invalid choice", result)
        self.assertEqual(self.char1.location, self.room1)

    @patch(PATCH_QUALIFYING)
    def test_invalid_ship_number_zero(self, mock_ships):
        """Ship number 0 is invalid (1-indexed)."""
        mock_ships.return_value = self.multi_ships
        result = self.call(CmdSail(), "far_dock 0")
        self.assertIn("Invalid choice", result)
        self.assertEqual(self.char1.location, self.room1)


class TestSailCosts(EvenniaCommandTest):
    """Test cost consumption during sailing."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_gateway.RoomGateway"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self._delay_patcher = patch(PATCH_DELAY, side_effect=_instant_delay)
        self._delay_patcher.start()
        self.dest_room = create.create_object(
            RoomGateway, key="Far Dock",
        )
        self.room1.destinations = [
            {
                "key": "far_dock",
                "label": "The Far Dock",
                "destination": self.dest_room,
                "travel_description": "You sail away...",
                "conditions": {"boat_level": 1, "food_cost": 2},
                "hidden": False,
            },
        ]
        self._set_seamanship(self.char1, MasteryLevel.BASIC)

    def tearDown(self):
        self._delay_patcher.stop()
        if self.dest_room:
            self.dest_room.delete()
        super().tearDown()

    def _set_seamanship(self, char, level):
        if not char.db.skill_mastery_levels:
            char.db.skill_mastery_levels = {}
        char.db.skill_mastery_levels[skills.SEAMANSHIP.value] = level.value

    @patch(PATCH_QUALIFYING, return_value=[_mock_ship("Cog", 1)])
    def test_bread_consumed(self, mock_ships):
        """Bread is consumed after sailing."""
        self.char1.db.resources = {3: 5}
        self.call(CmdSail(), "")
        self.assertEqual(self.char1.db.resources[3], 3)  # 5 - 2 = 3

    @patch(PATCH_QUALIFYING, return_value=[_mock_ship("Cog", 1)])
    def test_insufficient_bread(self, mock_ships):
        """Not enough bread blocks sailing."""
        self.char1.db.resources = {3: 1}  # need 2
        result = self.call(CmdSail(), "")
        self.assertIn("bread", result)
        self.assertEqual(self.char1.location, self.room1)

    @patch(PATCH_QUALIFYING, return_value=[_mock_ship("Cog", 1)])
    @patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_sail.consume_costs")
    def test_gold_consumed(self, mock_consume, mock_ships):
        """Gold cost destination calls consume_costs and teleports."""
        self.room1.destinations[0]["conditions"]["gold_cost"] = 10
        self.char1.db.resources = {3: 5}
        self.char1.db.gold = 50
        self.call(CmdSail(), "")
        mock_consume.assert_called_once()
        args = mock_consume.call_args
        self.assertEqual(args[0][1]["gold_cost"], 10)
        self.assertEqual(self.char1.location, self.dest_room)


class TestCheckBoatLevel(EvenniaCommandTest):
    """Test the _check_boat_level validator directly."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def _add_ship(self, tier):
        """Add a ShipNFTItem to char1 without triggering blockchain hooks."""
        ship = create.create_object(
            "typeclasses.items.untakeables.ship_nft_item.ShipNFTItem",
            key=f"Test Ship T{tier}",
            nohome=True,
        )
        ship.db.ship_tier = tier
        ship.db_location = self.char1
        ship.save(update_fields=["db_location"])
        return ship

    def test_check_passes(self):
        """Ship tier meets requirement."""
        self._add_ship(3)
        ok, msg = _check_boat_level(self.char1, {"boat_level": 2})
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_check_fails_no_ship(self):
        """No ships owned."""
        ok, msg = _check_boat_level(self.char1, {"boat_level": 1})
        self.assertFalse(ok)
        self.assertIn("don't own any ships", msg)

    def test_check_fails_low_tier(self):
        """Ship tier below requirement shows both tier names."""
        self._add_ship(1)
        ok, msg = _check_boat_level(self.char1, {"boat_level": 3})
        self.assertFalse(ok)
        self.assertIn("EXPERT", msg)  # needed
        self.assertIn("BASIC", msg)   # have

    def test_no_boat_level_passes(self):
        """No boat_level condition always passes."""
        ok, msg = _check_boat_level(self.char1, {"food_cost": 1})
        self.assertTrue(ok)
