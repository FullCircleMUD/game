"""
Tests for ExitVerticalAware — blocks movement when the character's
vertical position is incompatible with the destination room.

Height > destination max_height → blocked (too high)
Height < destination max_depth  → blocked (too deep)
Otherwise                       → movement allowed

evennia test --settings settings tests.typeclass_tests.test_exit_vertical_aware
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestExitVerticalAwareBase(EvenniaTest):
    """Base class that creates two rooms with an exit between them."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

        # Source room: can fly to 2, water to -3
        self.room1.max_height = 2
        self.room1.max_depth = -3

        # Destination room: defaults will be overridden per test
        self.room2 = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Destination",
            nohome=True,
        )

        self.exit = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.room2,
        )

        self.char1.room_vertical_position = 0


class TestExitAllowed(TestExitVerticalAwareBase):
    """Test cases where movement should be allowed."""

    def test_ground_to_land_room(self):
        """Ground level char moving to a land room (max_height=1) → allowed."""
        self.room2.max_height = 1
        self.room2.max_depth = 0
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)

    def test_ground_to_water_room(self):
        """Ground level char moving to water room (max_depth=-3) → allowed."""
        self.room2.max_height = 1
        self.room2.max_depth = -3
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)

    def test_flying_within_limit(self):
        """Flying char (height=1) to room with max_height=2 → allowed."""
        self.char1.room_vertical_position = 1
        self.room2.max_height = 2
        self.room2.max_depth = 0
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)

    def test_flying_at_exact_limit(self):
        """Flying char at exactly destination max_height → allowed."""
        self.char1.room_vertical_position = 1
        self.room2.max_height = 1
        self.room2.max_depth = 0
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)

    def test_swimming_within_limit(self):
        """Swimming char (depth=-1) to room with max_depth=-3 → allowed."""
        self.char1.room_vertical_position = -1
        self.room2.max_height = 1
        self.room2.max_depth = -3
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)

    def test_swimming_at_exact_limit(self):
        """Swimming char at exactly destination max_depth → allowed."""
        self.char1.room_vertical_position = -3
        self.room2.max_height = 1
        self.room2.max_depth = -3
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)


class TestExitBlockedTooHigh(TestExitVerticalAwareBase):
    """Test cases where movement is blocked because char is too high."""

    def test_flying_into_indoor_room(self):
        """Flying char (height=1) into indoor room (max_height=0) → blocked."""
        self.char1.room_vertical_position = 1
        self.room2.max_height = 0
        self.room2.max_depth = 0
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room1)

    def test_flying_too_high_for_destination(self):
        """Flying char (height=2) into room with max_height=1 → blocked."""
        self.char1.room_vertical_position = 2
        self.room2.max_height = 1
        self.room2.max_depth = 0
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room1)

    def test_blocked_indoor_message(self):
        """Indoor block should mention ground level."""
        self.char1.room_vertical_position = 1
        self.room2.max_height = 0
        self.room2.max_depth = 0
        self.exit.at_traverse(self.char1, self.room2)
        # char stays in room1
        self.assertEqual(self.char1.location, self.room1)

    def test_blocked_descend_message(self):
        """Height block (destination has some height but not enough) → stays."""
        self.char1.room_vertical_position = 2
        self.room2.max_height = 1
        self.room2.max_depth = 0
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room1)


class TestExitBlockedTooDeep(TestExitVerticalAwareBase):
    """Test cases where movement is blocked because char is too deep."""

    def test_swimming_into_land_room(self):
        """Swimming char (depth=-1) into land room (max_depth=0) → blocked."""
        self.char1.room_vertical_position = -1
        self.room2.max_height = 1
        self.room2.max_depth = 0
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room1)

    def test_swimming_too_deep_for_destination(self):
        """Swimming char (depth=-3) into room with max_depth=-2 → blocked."""
        self.char1.room_vertical_position = -3
        self.room2.max_height = 1
        self.room2.max_depth = -2
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room1)

    def test_blocked_no_water_message(self):
        """Land room block should keep char in place."""
        self.char1.room_vertical_position = -1
        self.room2.max_height = 1
        self.room2.max_depth = 0
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room1)

    def test_blocked_shallower_message(self):
        """Shallower water block should keep char in place."""
        self.char1.room_vertical_position = -3
        self.room2.max_height = 1
        self.room2.max_depth = -1
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room1)


class TestExitEncumbered(TestExitVerticalAwareBase):
    """Test encumbrance blocking movement through exits."""

    def _make_encumbered(self):
        """Put character over capacity."""
        self.char1.strength = 10  # neutralise STR modifier
        self.char1.max_carrying_capacity_kg = 50
        self.char1.current_weight_nfts = 60.0  # over limit

    def test_encumbered_blocks_ground_movement(self):
        """Over-encumbered on dry ground → can't move."""
        self._make_encumbered()
        self.room1.max_depth = 0
        self.room2.max_height = 1
        self.room2.max_depth = 0
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room1)

    def test_not_encumbered_allows_movement(self):
        """Within capacity → movement allowed."""
        self.char1.strength = 10
        self.char1.max_carrying_capacity_kg = 50
        self.char1.current_weight_nfts = 30.0
        self.room2.max_height = 1
        self.room2.max_depth = 0
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)

    def test_encumbered_fall_while_flying(self):
        """Over-encumbered while flying → fall to ground + take damage."""
        self._make_encumbered()
        self.char1.room_vertical_position = 2
        self.char1.hp = 100
        self.room2.max_height = 2
        self.room2.max_depth = 0
        self.exit.at_traverse(self.char1, self.room2)
        # Should not have moved
        self.assertEqual(self.char1.location, self.room1)
        # Should have fallen to ground
        self.assertEqual(self.char1.room_vertical_position, 0)
        # Should have taken fall damage (2 * 10 = 20)
        self.assertEqual(self.char1.hp, 80)

    def test_encumbered_sink_while_underwater(self):
        """Over-encumbered while underwater → sink to bottom."""
        self._make_encumbered()
        self.char1.room_vertical_position = -1
        self.room1.max_depth = -3
        self.room2.max_height = 1
        self.room2.max_depth = -3
        self.exit.at_traverse(self.char1, self.room2)
        # Should not have moved
        self.assertEqual(self.char1.location, self.room1)
        # Should have sunk to bottom
        self.assertEqual(self.char1.room_vertical_position, -3)

    def test_encumbered_sink_from_water_surface(self):
        """Over-encumbered on water surface (height=0, max_depth<0) → sink."""
        self._make_encumbered()
        self.char1.room_vertical_position = 0
        self.room1.max_depth = -2
        self.room2.max_height = 1
        self.room2.max_depth = -2
        self.exit.at_traverse(self.char1, self.room2)
        # Should not have moved
        self.assertEqual(self.char1.location, self.room1)
        # Should have sunk to bottom
        self.assertEqual(self.char1.room_vertical_position, -2)


# ================================================================
#  Direction system tests
# ================================================================


class TestExitDirectionSystem(TestExitVerticalAwareBase):
    """Test direction auto-aliasing and display formatting."""

    def test_set_direction_adds_aliases(self):
        """set_direction('east') adds 'e' and 'east' as aliases."""
        self.exit.set_direction("east")
        aliases = self.exit.aliases.all()
        self.assertIn("e", aliases)
        self.assertIn("east", aliases)

    def test_set_direction_stores_attribute(self):
        """set_direction sets the direction attribute."""
        self.exit.set_direction("south")
        self.assertEqual(self.exit.direction, "south")

    def test_display_name_with_direction(self):
        """Exit with direction set shows 'direction: desc'."""
        self.exit.set_direction("east")
        self.exit.db.desc = "a small dirt track"
        name = self.exit.get_display_name(self.char1)
        self.assertEqual(name, "east: a small dirt track")

    def test_display_name_with_direction_uses_key_fallback(self):
        """Exit with direction but no desc falls back to key."""
        self.exit.set_direction("east")
        # db.desc is None, key is "north"
        name = self.exit.get_display_name(self.char1)
        self.assertEqual(name, "east: north")

    def test_display_name_without_direction(self):
        """Exit with default direction just shows desc or key."""
        self.exit.db.desc = "a dusty path"
        name = self.exit.get_display_name(self.char1)
        self.assertEqual(name, "a dusty path")

    def test_display_name_default_no_desc(self):
        """Exit with default direction and no desc shows key."""
        name = self.exit.get_display_name(self.char1)
        self.assertEqual(name, "north")

    def test_set_direction_multiple_calls(self):
        """Multiple set_direction calls accumulate aliases without duplicates."""
        self.exit.set_direction("east")
        self.exit.set_direction("east")  # second call
        aliases = self.exit.aliases.all()
        # Should not have duplicates
        self.assertEqual(aliases.count("e"), 1)
        self.assertEqual(aliases.count("east"), 1)

    def test_all_cardinal_directions(self):
        """All compass directions produce correct display format."""
        for direction in ["north", "south", "east", "west"]:
            exit_obj = create.create_object(
                "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
                key="test path",
                location=self.room1,
                destination=self.room2,
                nohome=True,
            )
            exit_obj.set_direction(direction)
            exit_obj.db.desc = "a path"
            name = exit_obj.get_display_name(self.char1)
            self.assertEqual(name, f"{direction}: a path")
            exit_obj.delete()

    def test_up_down_directions(self):
        """Up/down directions produce correct aliases and display."""
        self.exit.set_direction("up")
        aliases = self.exit.aliases.all()
        self.assertIn("u", aliases)
        self.assertIn("up", aliases)
        self.exit.db.desc = "a ladder"
        name = self.exit.get_display_name(self.char1)
        self.assertEqual(name, "up: a ladder")
