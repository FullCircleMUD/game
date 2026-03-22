"""
Tests for CmdFly and CmdSwim — vertical movement within rooms.

Vertical position: 0 = ground/surface, positive = flying, negative = underwater.
Room max_height caps flying upward, max_depth (negative) caps diving.

Note: EvenniaCommandTest.call() checks that msg STARTS WITH the expected
string, not substring match.

evennia test --settings settings tests.command_tests.test_cmd_fly_swim
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_fly import CmdFly
from commands.all_char_cmds.cmd_swim import CmdSwim
from enums.condition import Condition


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


# =====================================================================
#  Fly tests — land room (max_height=1, max_depth=0)
# =====================================================================

class TestCmdFlyLand(EvenniaCommandTest):
    """Test flying in a land room (no water)."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.room_vertical_position = 0
        # Grant FLY condition for all fly tests
        self.char1.add_condition(Condition.FLY)
        # RoomBase defaults: max_height=1, max_depth=0

    def test_fly_up_from_ground(self):
        """fly up from ground should move up and increment position."""
        self.call(CmdFly(), "up")
        self.assertEqual(self.char1.room_vertical_position, 1)

    def test_fly_up_alias(self):
        """fly u should work as alias for fly up."""
        self.call(CmdFly(), "u")
        self.assertEqual(self.char1.room_vertical_position, 1)

    def test_fly_up_at_max_height(self):
        """fly up at max height should be blocked."""
        self.char1.room_vertical_position = 1
        result = self.call(CmdFly(), "up")
        self.assertIn("can't fly any higher", result)
        self.assertEqual(self.char1.room_vertical_position, 1)

    def test_fly_down_to_ground(self):
        """fly down from height 1 to ground."""
        self.char1.room_vertical_position = 1
        result = self.call(CmdFly(), "down")
        self.assertIn("fly down to the ground", result)
        self.assertEqual(self.char1.room_vertical_position, 0)

    def test_fly_down_on_ground(self):
        """fly down when already on the ground should be blocked."""
        result = self.call(CmdFly(), "down")
        self.assertIn("already on the ground", result)
        self.assertEqual(self.char1.room_vertical_position, 0)

    def test_fly_down_alias(self):
        """fly d should work as alias for fly down."""
        result = self.call(CmdFly(), "d")
        self.assertIn("already on the ground", result)

    def test_fly_no_direction(self):
        """fly with no direction should show usage hint."""
        result = self.call(CmdFly(), "")
        self.assertIn("up", result)
        self.assertIn("down", result)

    def test_fly_invalid_direction(self):
        """fly with invalid direction should show usage hint."""
        result = self.call(CmdFly(), "sideways")
        self.assertIn("up", result)
        self.assertIn("down", result)

    def test_fly_down_still_in_air(self):
        """fly down from height 2 should say 'fly lower', stay above ground."""
        self.room1.max_height = 3
        self.char1.room_vertical_position = 2
        result = self.call(CmdFly(), "down")
        self.assertIn("fly lower", result)
        self.assertEqual(self.char1.room_vertical_position, 1)


# =====================================================================
#  Fly tests — water room (max_height=1, max_depth=-3)
# =====================================================================

class TestCmdFlyWater(EvenniaCommandTest):
    """Test flying in a room with water."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.room_vertical_position = 0
        self.char1.add_condition(Condition.FLY)
        self.room1.max_height = 1
        self.room1.max_depth = -3

    def test_fly_up_underwater(self):
        """fly up while underwater should be blocked."""
        self.char1.room_vertical_position = -2
        result = self.call(CmdFly(), "up")
        self.assertIn("can't fly in water", result)
        self.assertEqual(self.char1.room_vertical_position, -2)

    def test_fly_down_underwater(self):
        """fly down while underwater should be blocked."""
        self.char1.room_vertical_position = -1
        result = self.call(CmdFly(), "down")
        self.assertIn("can't fly in water", result)
        self.assertEqual(self.char1.room_vertical_position, -1)

    def test_fly_down_on_water_surface(self):
        """fly down on water surface should be blocked."""
        result = self.call(CmdFly(), "down")
        self.assertIn("waters surface", result)
        self.assertEqual(self.char1.room_vertical_position, 0)

    def test_fly_down_to_water_surface(self):
        """fly down from air to water surface."""
        self.char1.room_vertical_position = 1
        result = self.call(CmdFly(), "down")
        self.assertIn("descend to the waters surface", result)
        self.assertEqual(self.char1.room_vertical_position, 0)

    def test_fly_up_from_water_surface(self):
        """fly up from water surface should work normally."""
        self.call(CmdFly(), "up")
        self.assertEqual(self.char1.room_vertical_position, 1)


# =====================================================================
#  Fly condition gating tests
# =====================================================================

class TestCmdFlyConditionGating(EvenniaCommandTest):
    """Test that fly command requires FLY condition."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.room_vertical_position = 0

    def test_fly_blocked_without_condition(self):
        """fly up without FLY condition should be blocked."""
        result = self.call(CmdFly(), "up")
        self.assertIn("can't fly", result)
        self.assertEqual(self.char1.room_vertical_position, 0)

    def test_fly_works_with_condition(self):
        """fly up with FLY condition should succeed."""
        self.char1.add_condition(Condition.FLY)
        self.call(CmdFly(), "up")
        self.assertEqual(self.char1.room_vertical_position, 1)

    def test_fly_down_blocked_without_condition(self):
        """fly down without FLY condition should be blocked."""
        result = self.call(CmdFly(), "down")
        self.assertIn("can't fly", result)

    def test_fall_on_fly_removal_height_2(self):
        """Losing FLY at height 2 should fall to ground and take 20 damage."""
        self.char1.add_condition(Condition.FLY)
        self.char1.room_vertical_position = 2
        self.char1.hp = 100
        self.char1.remove_condition(Condition.FLY)
        self.assertEqual(self.char1.room_vertical_position, 0)
        self.assertEqual(self.char1.hp, 80)

    def test_fall_on_fly_removal_height_1(self):
        """Losing FLY at height 1 should take 10 damage."""
        self.char1.add_condition(Condition.FLY)
        self.char1.room_vertical_position = 1
        self.char1.hp = 100
        self.char1.remove_condition(Condition.FLY)
        self.assertEqual(self.char1.room_vertical_position, 0)
        self.assertEqual(self.char1.hp, 90)

    def test_no_fall_on_ground(self):
        """Losing FLY on the ground should not deal damage."""
        self.char1.add_condition(Condition.FLY)
        self.char1.hp = 100
        self.char1.remove_condition(Condition.FLY)
        self.assertEqual(self.char1.room_vertical_position, 0)
        self.assertEqual(self.char1.hp, 100)

    def test_no_fall_underwater(self):
        """Losing FLY while underwater should not deal damage."""
        self.char1.add_condition(Condition.FLY)
        self.char1.room_vertical_position = -1
        self.char1.hp = 100
        self.char1.remove_condition(Condition.FLY)
        self.assertEqual(self.char1.room_vertical_position, -1)
        self.assertEqual(self.char1.hp, 100)

    def test_fall_hp_floor_zero(self):
        """Fall damage triggers die() which resets HP to 1."""
        self.char1.add_condition(Condition.FLY)
        self.char1.room_vertical_position = 5
        self.room1.max_height = 5
        self.char1.hp = 10  # 50 damage from height 5 would go negative
        self.char1.remove_condition(Condition.FLY)
        # die() fires when HP hits 0, resetting HP to 1
        self.assertEqual(self.char1.hp, 1)


# =====================================================================
#  Swim tests — land room (max_depth=0, no water)
# =====================================================================

class TestCmdSwimLand(EvenniaCommandTest):
    """Test swimming in a land room (no water)."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.room_vertical_position = 0

    def test_swim_down_on_land(self):
        """swim down on dry land should be blocked."""
        result = self.call(CmdSwim(), "down")
        self.assertIn("can't swim in dirt", result)
        self.assertEqual(self.char1.room_vertical_position, 0)

    def test_swim_up_on_land(self):
        """swim up on surface should be blocked."""
        result = self.call(CmdSwim(), "up")
        self.assertIn("already on the surface", result)
        self.assertEqual(self.char1.room_vertical_position, 0)

    def test_swim_no_direction(self):
        """swim with no direction should show usage hint."""
        result = self.call(CmdSwim(), "")
        self.assertIn("up", result)
        self.assertIn("down", result)

    def test_swim_invalid_direction(self):
        """swim with invalid direction should show usage hint."""
        result = self.call(CmdSwim(), "sideways")
        self.assertIn("up", result)
        self.assertIn("down", result)


# =====================================================================
#  Swim tests — water room (max_depth=-3)
# =====================================================================

class TestCmdSwimWater(EvenniaCommandTest):
    """Test swimming in a room with water."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.room_vertical_position = 0
        self.room1.max_height = 1
        self.room1.max_depth = -3

    def test_swim_down_from_surface(self):
        """swim down from surface should dive."""
        self.call(CmdSwim(), "down")
        self.assertEqual(self.char1.room_vertical_position, -1)

    def test_swim_down_alias(self):
        """swim d should work as alias for swim down."""
        self.call(CmdSwim(), "d")
        self.assertEqual(self.char1.room_vertical_position, -1)

    def test_swim_down_at_max_depth(self):
        """swim down at max depth should be blocked."""
        self.char1.room_vertical_position = -3
        result = self.call(CmdSwim(), "down")
        self.assertIn("can't swim any lower", result)
        self.assertEqual(self.char1.room_vertical_position, -3)

    def test_swim_up_underwater(self):
        """swim up from underwater should move up."""
        self.char1.room_vertical_position = -3
        result = self.call(CmdSwim(), "up")
        self.assertIn("swim upwards", result)
        self.assertEqual(self.char1.room_vertical_position, -2)

    def test_swim_up_alias(self):
        """swim u should work as alias for swim up."""
        self.char1.room_vertical_position = -2
        self.call(CmdSwim(), "u")
        self.assertEqual(self.char1.room_vertical_position, -1)

    def test_swim_up_to_surface(self):
        """swim up from depth -1 should break surface."""
        self.char1.room_vertical_position = -1
        result = self.call(CmdSwim(), "up")
        self.assertIn("breaks the surface", result)
        self.assertEqual(self.char1.room_vertical_position, 0)

    def test_swim_up_already_on_surface(self):
        """swim up when already on surface should be blocked."""
        result = self.call(CmdSwim(), "up")
        self.assertIn("already on the surface", result)
        self.assertEqual(self.char1.room_vertical_position, 0)

    def test_swim_up_in_air(self):
        """swim up while in air should be blocked."""
        self.char1.room_vertical_position = 1
        result = self.call(CmdSwim(), "up")
        self.assertIn("can't swim in air", result)
        self.assertEqual(self.char1.room_vertical_position, 1)

    def test_swim_down_in_air(self):
        """swim down while in air should be blocked."""
        self.char1.room_vertical_position = 1
        result = self.call(CmdSwim(), "down")
        self.assertIn("can't swim in air", result)
        self.assertEqual(self.char1.room_vertical_position, 1)


# =====================================================================
#  Breath timer tests
# =====================================================================

class TestBreathTimer(EvenniaCommandTest):
    """Test breath timer when swimming underwater."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.room_vertical_position = 0
        self.room1.max_depth = -3

    def _has_breath_timer(self):
        return bool(self.char1.scripts.get("breath_timer"))

    def test_swim_down_starts_breath_timer(self):
        """Swimming underwater without WATER_BREATHING starts breath timer."""
        self.call(CmdSwim(), "down")
        self.assertTrue(self._has_breath_timer())

    def test_swim_down_no_timer_with_water_breathing(self):
        """Swimming underwater with WATER_BREATHING does not start timer."""
        self.char1.add_condition(Condition.WATER_BREATHING)
        self.call(CmdSwim(), "down")
        self.assertFalse(self._has_breath_timer())

    def test_swim_up_to_surface_stops_timer(self):
        """Swimming to surface stops the breath timer."""
        self.call(CmdSwim(), "down")
        self.assertTrue(self._has_breath_timer())
        self.call(CmdSwim(), "up")
        self.assertFalse(self._has_breath_timer())

    def test_gain_water_breathing_stops_timer(self):
        """Gaining WATER_BREATHING while underwater stops the timer."""
        self.call(CmdSwim(), "down")
        self.assertTrue(self._has_breath_timer())
        self.char1.add_condition(Condition.WATER_BREATHING)
        self.assertFalse(self._has_breath_timer())

    def test_lose_water_breathing_starts_timer(self):
        """Losing WATER_BREATHING while underwater starts the timer."""
        self.char1.add_condition(Condition.WATER_BREATHING)
        self.call(CmdSwim(), "down")
        self.assertFalse(self._has_breath_timer())
        self.char1.remove_condition(Condition.WATER_BREATHING)
        self.assertTrue(self._has_breath_timer())

    def test_lose_water_breathing_on_surface_no_timer(self):
        """Losing WATER_BREATHING while on surface should not start timer."""
        self.char1.add_condition(Condition.WATER_BREATHING)
        self.char1.remove_condition(Condition.WATER_BREATHING)
        self.assertFalse(self._has_breath_timer())

    def test_breath_timer_countdown_message(self):
        """Breath timer should send countdown messages."""
        self.call(CmdSwim(), "down")
        timers = self.char1.scripts.get("breath_timer")
        self.assertTrue(timers)
        timer = timers[0]
        timer.at_repeat()
        # Check that a message was sent (we can't easily capture it in
        # EvenniaCommandTest, but at least verify no crash)
        self.assertTrue(self._has_breath_timer())

    def test_breath_timer_drowning_damage(self):
        """After breath runs out, timer should deal drowning damage."""
        self.call(CmdSwim(), "down")
        timers = self.char1.scripts.get("breath_timer")
        timer = timers[0]
        # Exhaust all breath by setting elapsed past duration
        total_breath = timer._get_breath_duration()
        timer.ndb.elapsed = total_breath
        self.char1.hp = 50  # ensure enough HP to survive one tick
        starting_hp = self.char1.hp
        timer.at_repeat()
        self.assertLess(self.char1.hp, starting_hp)

    def test_con_modifier_affects_duration(self):
        """Higher CON should give more breath time."""
        self.call(CmdSwim(), "down")
        timers = self.char1.scripts.get("breath_timer")
        timer = timers[0]
        base_duration = timer._get_breath_duration()

        # Increase CON and check duration increases
        original_con = self.char1.constitution
        self.char1.constitution = 18  # +4 modifier
        high_con_duration = timer._get_breath_duration()
        self.assertGreater(high_con_duration, base_duration)
        self.char1.constitution = original_con

    def test_breath_minimum_10_seconds(self):
        """Breath duration should never go below 10 seconds."""
        self.call(CmdSwim(), "down")
        timers = self.char1.scripts.get("breath_timer")
        timer = timers[0]
        # Set CON very low
        self.char1.constitution = 1  # -5 modifier → 30 + (-5*15) = -45 → clamped to 10
        self.assertEqual(timer._get_breath_duration(), 10)


# =====================================================================
#  Encumbrance tests — fly & swim blocked when overloaded
# =====================================================================


class TestFlyEncumbered(EvenniaCommandTest):
    """Test that flying is blocked when over carrying capacity."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.room_vertical_position = 0
        self.char1.add_condition(Condition.FLY)
        # Make character over-encumbered
        self.char1.strength = 10
        self.char1.max_carrying_capacity_kg = 50
        self.char1.current_weight_nfts = 60.0

    def test_fly_up_blocked_when_encumbered(self):
        """Can't fly up when over-encumbered on ground."""
        result = self.call(CmdFly(), "up")
        self.assertIn("too much to fly", result)
        self.assertEqual(self.char1.room_vertical_position, 0)

    def test_fly_falls_when_encumbered_and_airborne(self):
        """If already airborne and encumbered, trying to fly triggers fall."""
        self.char1.room_vertical_position = 2
        self.char1.hp = 100
        self.call(CmdFly(), "up")
        # Should have fallen to ground
        self.assertEqual(self.char1.room_vertical_position, 0)
        # Should have taken fall damage (2 * 10 = 20)
        self.assertEqual(self.char1.hp, 80)


class TestSwimEncumbered(EvenniaCommandTest):
    """Test that swimming is blocked when over carrying capacity."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.room_vertical_position = 0
        self.room1.max_depth = -3
        # Make character over-encumbered
        self.char1.strength = 10
        self.char1.max_carrying_capacity_kg = 50
        self.char1.current_weight_nfts = 60.0

    def test_swim_encumbered_sinks_from_surface(self):
        """Encumbered on water surface → sink to bottom."""
        result = self.call(CmdSwim(), "down")
        self.assertIn("sink to the bottom", result)
        self.assertEqual(self.char1.room_vertical_position, -3)

    def test_swim_encumbered_sinks_from_underwater(self):
        """Encumbered underwater → sink to bottom."""
        self.char1.room_vertical_position = -1
        result = self.call(CmdSwim(), "up")
        self.assertIn("sink to the bottom", result)
        self.assertEqual(self.char1.room_vertical_position, -3)

    def test_swim_encumbered_on_dry_land(self):
        """Encumbered on dry land → can't swim."""
        self.room1.max_depth = 0
        result = self.call(CmdSwim(), "down")
        self.assertIn("too much to swim", result)
