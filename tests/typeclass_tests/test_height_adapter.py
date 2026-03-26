"""
Tests for height adapter exit features — height gating, arrival heights,
fall warnings, vert_descriptions, and exit visibility filtering.

evennia test --settings settings tests.typeclass_tests.test_height_adapter
"""

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_override_look import CmdLook


class TestHeightAccessibility(EvenniaCommandTest):
    """Test ExitVerticalAware.is_height_accessible()."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.room2.always_lit = True
        from typeclasses.terrain.exits.exit_vertical_aware import (
            ExitVerticalAware,
        )

        self.exit = create_object(
            ExitVerticalAware,
            key="north",
            location=self.room1,
            destination=self.room2,
        )
        self.exit.set_direction("north")

    def test_no_gating_all_heights_accessible(self):
        """Default (no height attrs set) — all heights accessible."""
        self.assertTrue(self.exit.is_height_accessible(0))
        self.assertTrue(self.exit.is_height_accessible(1))
        self.assertTrue(self.exit.is_height_accessible(-3))

    def test_min_height_gate(self):
        """required_min_height gates out lower heights."""
        self.exit.required_min_height = 1
        self.assertFalse(self.exit.is_height_accessible(0))
        self.assertTrue(self.exit.is_height_accessible(1))
        self.assertTrue(self.exit.is_height_accessible(2))

    def test_max_height_gate(self):
        """required_max_height gates out higher heights."""
        self.exit.required_max_height = 0
        self.assertTrue(self.exit.is_height_accessible(0))
        self.assertTrue(self.exit.is_height_accessible(-1))
        self.assertFalse(self.exit.is_height_accessible(1))

    def test_min_max_range(self):
        """Both bounds create a range."""
        self.exit.required_min_height = -2
        self.exit.required_max_height = 0
        self.assertFalse(self.exit.is_height_accessible(-3))
        self.assertTrue(self.exit.is_height_accessible(-2))
        self.assertTrue(self.exit.is_height_accessible(-1))
        self.assertTrue(self.exit.is_height_accessible(0))
        self.assertFalse(self.exit.is_height_accessible(1))

    def test_exact_height(self):
        """Same min and max = exact height only."""
        self.exit.required_min_height = -3
        self.exit.required_max_height = -3
        self.assertFalse(self.exit.is_height_accessible(-2))
        self.assertTrue(self.exit.is_height_accessible(-3))
        self.assertFalse(self.exit.is_height_accessible(-4))

    def test_arrival_heights_implicit_gate(self):
        """Heights not in arrival_heights dict are blocked."""
        self.exit.arrival_heights = {1: 0, 2: 1}
        self.assertFalse(self.exit.is_height_accessible(0))
        self.assertTrue(self.exit.is_height_accessible(1))
        self.assertTrue(self.exit.is_height_accessible(2))

    def test_arrival_heights_with_range(self):
        """arrival_heights + range both must pass."""
        self.exit.required_min_height = 1
        self.exit.arrival_heights = {1: 0, 2: 1}
        self.assertFalse(self.exit.is_height_accessible(0))
        self.assertTrue(self.exit.is_height_accessible(1))
        self.assertTrue(self.exit.is_height_accessible(2))


class TestExitVisibilityByHeight(EvenniaCommandTest):
    """Test that height-gated exits are hidden from auto-exit display."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.room1.max_height = 2
        from typeclasses.terrain.exits.exit_vertical_aware import (
            ExitVerticalAware,
        )

        # Ground exit — always visible
        self.ground_exit = create_object(
            ExitVerticalAware,
            key="east",
            location=self.room1,
            destination=self.room2,
        )
        self.ground_exit.set_direction("east")

        # Flying-only exit
        self.fly_exit = create_object(
            ExitVerticalAware,
            key="north",
            location=self.room1,
            destination=self.room2,
        )
        self.fly_exit.set_direction("north")
        self.fly_exit.required_min_height = 1

    def test_ground_sees_ground_exit_only(self):
        """At ground level, only the ground exit shows."""
        self.char1.room_vertical_position = 0
        display = self.room1.get_display_exits(self.char1)
        self.assertIn("e", display)
        self.assertNotIn("n", display)

    def test_flying_sees_both_exits(self):
        """At height 1, both exits show."""
        self.char1.room_vertical_position = 1
        display = self.room1.get_display_exits(self.char1)
        self.assertIn("e", display)
        self.assertIn("n", display)


class TestArrivalHeightTransition(EvenniaCommandTest):
    """Test that arrival_heights changes character height on traverse."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.room1.max_height = 2
        self.room2.always_lit = True
        self.room2.max_height = 2
        from typeclasses.terrain.exits.exit_vertical_aware import (
            ExitVerticalAware,
        )

        self.exit = create_object(
            ExitVerticalAware,
            key="north",
            location=self.room1,
            destination=self.room2,
        )
        self.exit.set_direction("north")
        self.exit.arrival_heights = {1: 0, 2: 1}

    def test_height_1_arrives_at_0(self):
        """Flying at height 1 → land on arrival (height 0)."""
        self.char1.room_vertical_position = 1
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)
        self.assertEqual(self.char1.room_vertical_position, 0)

    def test_height_2_arrives_at_1(self):
        """Flying at height 2 → still airborne (height 1).
        Character has FLY so no fall triggers."""
        from enums.condition import Condition
        self.char1.add_condition(Condition.FLY)
        self.char1.room_vertical_position = 2
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)
        self.assertEqual(self.char1.room_vertical_position, 1)

    def test_ground_blocked(self):
        """Ground level (0) not in arrival_heights → blocked."""
        self.char1.room_vertical_position = 0
        self.exit.at_traverse(self.char1, self.room2)
        # Should still be in room1
        self.assertEqual(self.char1.location, self.room1)

    def test_no_arrival_heights_keeps_height(self):
        """Without arrival_heights, height is preserved on ground."""
        self.exit.arrival_heights = None
        self.char1.room_vertical_position = 0
        self.exit.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)
        self.assertEqual(self.char1.room_vertical_position, 0)


class TestFallWarning(EvenniaCommandTest):
    """Test fall warning message and fall damage on height transition."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.room1.max_height = 0  # indoor, can't fly
        self.room2.always_lit = True
        self.room2.max_height = 3  # outdoor, can fly high
        from typeclasses.terrain.exits.exit_vertical_aware import (
            ExitVerticalAware,
        )

        # Tower window exit — ground level → arrive at height 2
        self.exit = create_object(
            ExitVerticalAware,
            key="north",
            location=self.room1,
            destination=self.room2,
        )
        self.exit.set_direction("north")
        self.exit.arrival_heights = {0: 2}
        self.exit.fall_warning = "You climb through the window!"

    def test_fall_reduces_hp(self):
        """Arrival at height > 0 without FLY triggers fall damage."""
        # Give enough HP to survive the fall (height 2 = 20 damage)
        self.char1.hp = 100
        self.char1.hp_max = 100
        self.char1.room_vertical_position = 0
        self.exit.at_traverse(self.char1, self.room2)
        # Should have moved and taken fall damage
        self.assertEqual(
            self.char1.location, self.room2,
            f"Character at {self.char1.location.key}, hp={self.char1.hp}"
        )
        self.assertLess(self.char1.hp, 100)
        # Fall resets height to 0
        self.assertEqual(self.char1.room_vertical_position, 0)


class TestVertDescriptions(EvenniaCommandTest):
    """Test height-dependent room descriptions via vert_descriptions."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.room1.max_height = 2
        self.room1.db.desc = "A normal courtyard."
        self.room1.vert_descriptions = {
            0: "A cobblestone courtyard surrounded by high walls.",
            1: "From above, the courtyard spreads out below you.",
        }

    def test_ground_level_desc(self):
        """Ground level gets height-specific description."""
        self.char1.room_vertical_position = 0
        desc = self.room1.get_display_desc(self.char1)
        self.assertIn("cobblestone courtyard", desc)
        self.assertNotIn("normal courtyard", desc)

    def test_flying_desc(self):
        """Flying gets height-specific description."""
        self.char1.room_vertical_position = 1
        desc = self.room1.get_display_desc(self.char1)
        self.assertIn("spreads out below you", desc)

    def test_unmapped_height_falls_back(self):
        """Height not in vert_descriptions falls back to db.desc."""
        self.char1.room_vertical_position = 2
        desc = self.room1.get_display_desc(self.char1)
        self.assertIn("normal courtyard", desc)

    def test_no_vert_descriptions_uses_desc(self):
        """Without vert_descriptions, always uses db.desc."""
        self.room1.vert_descriptions = None
        self.char1.room_vertical_position = 0
        desc = self.room1.get_display_desc(self.char1)
        self.assertIn("normal courtyard", desc)
