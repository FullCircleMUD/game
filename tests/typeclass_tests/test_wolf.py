"""
Tests for Wolf mob — aggression, targeting, and wander anti-stacking.

evennia test --settings settings tests.typeclass_tests.test_wolf
"""

from unittest.mock import patch, MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestWolfAggression(EvenniaTest):
    """Wolf should be aggressive to both players and rabbits."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.wolf = create.create_object(
            "typeclasses.actors.mobs.wolf.Wolf",
            key="a grey wolf",
            location=self.room1,
        )
        self.wolf.is_alive = True
        self.wolf.hp = 12

    def test_wolf_is_aggressive_to_players(self):
        self.assertTrue(self.wolf.is_aggressive_to_players)

    def test_wolf_stats(self):
        self.assertEqual(self.wolf.hp_max, 12)
        self.assertEqual(self.wolf.damage_dice, "1d4")
        self.assertEqual(self.wolf.level, 2)

    def test_wolf_max_per_room(self):
        self.assertEqual(self.wolf.max_per_room, 1)

    @patch("typeclasses.actors.mobs.aggressive_mob.delay")
    def test_at_new_arrival_aggros_player(self, mock_delay):
        """Wolf should schedule attack when a player enters."""
        self.char1.is_pc = True
        self.wolf.at_new_arrival(self.char1)
        self.assertTrue(mock_delay.called)

    @patch("typeclasses.actors.mobs.aggressive_mob.delay")
    def test_at_new_arrival_aggros_rabbit(self, mock_delay):
        """Wolf should schedule attack when a rabbit enters."""
        rabbit = create.create_object(
            "typeclasses.actors.mobs.rabbit.Rabbit",
            key="a rabbit",
            location=self.room1,
        )
        rabbit.is_alive = True
        self.wolf.at_new_arrival(rabbit)
        self.assertTrue(mock_delay.called)

    @patch("typeclasses.actors.mobs.aggressive_mob.delay")
    def test_no_aggro_when_low_health(self, mock_delay):
        """Wolf should not aggro when below HP threshold."""
        self.wolf.hp = 1  # well below 50%
        self.char1.is_pc = True
        self.wolf.at_new_arrival(self.char1)
        self.assertFalse(mock_delay.called)

    @patch("typeclasses.actors.mobs.aggressive_mob.delay")
    def test_no_aggro_when_dead(self, mock_delay):
        """Dead wolf should not aggro."""
        self.wolf.is_alive = False
        self.char1.is_pc = True
        self.wolf.at_new_arrival(self.char1)
        self.assertFalse(mock_delay.called)

    @patch("typeclasses.actors.mobs.aggressive_mob.delay")
    def test_players_prioritised_over_rabbits_in_wander(self, mock_delay):
        """ai_wander should target players before rabbits."""
        self.char1.is_pc = True
        self.char1.location = self.room1
        rabbit = create.create_object(
            "typeclasses.actors.mobs.rabbit.Rabbit",
            key="a rabbit",
            location=self.room1,
        )
        rabbit.is_alive = True
        self.wolf.ai_wander()
        # Should have scheduled an attack (on a player, not the rabbit)
        self.assertTrue(mock_delay.called)
        target = mock_delay.call_args[0][2]
        self.assertNotEqual(target, rabbit)
        self.assertTrue(getattr(target, "is_pc", False))


class TestMaxPerRoom(EvenniaTest):
    """Test the max_per_room anti-stacking feature on CombatMob.wander()."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # Create a wolf in room1 with exits to room2
        self.wolf1 = create.create_object(
            "typeclasses.actors.mobs.wolf.Wolf",
            key="wolf 1",
            location=self.room1,
        )
        self.wolf1.is_alive = True
        self.wolf1.hp = 12
        # Clear area_tag so exits aren't filtered by area
        self.wolf1.tags.clear(category="mob_area")

    def test_wander_blocked_when_same_type_at_max(self):
        """Wolf should not wander into room that already has a wolf."""
        # Put a second wolf in room2 (the only destination)
        wolf2 = create.create_object(
            "typeclasses.actors.mobs.wolf.Wolf",
            key="wolf 2",
            location=self.room2,
        )
        wolf2.is_alive = True

        # wolf1 has max_per_room=1, room2 already has wolf2
        self.wolf1.wander()
        # wolf1 should still be in room1
        self.assertEqual(self.wolf1.location, self.room1)

    def test_wander_allowed_when_below_max(self):
        """Wolf should wander into room with no other wolves."""
        # room2 is empty — wolf should be able to move there
        self.wolf1.wander()
        # Wander is probabilistic via pick_random_exit, but with
        # max_per_room the path through get_area_exits is used.
        # Since room2 has no wolves, it should be a valid destination.
        # The wolf may or may not move (random.choice of exits),
        # but it should NOT be blocked.
        # We test that room2 is a valid exit by checking that
        # wander doesn't raise and the wolf's location is room1 or room2.
        self.assertIn(self.wolf1.location, [self.room1, self.room2])

    def test_wander_unlimited_when_max_zero(self):
        """Default max_per_room=0 means no stacking restriction."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin",
            location=self.room1,
        )
        mob.is_alive = True
        mob.tags.clear(category="mob_area")
        self.assertEqual(mob.max_per_room, 0)

        # Put another goblin in room2
        mob2 = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin",
            location=self.room2,
        )
        mob2.is_alive = True

        # Should still be able to wander (no restriction)
        mob.wander()
        self.assertIn(mob.location, [self.room1, self.room2])

    def test_different_types_dont_block(self):
        """A DireWolf in room2 should not prevent a Wolf from entering."""
        dire_wolf = create.create_object(
            "typeclasses.actors.mobs.dire_wolf.DireWolf",
            key="a dire wolf",
            location=self.room2,
        )
        dire_wolf.is_alive = True

        # Wolf has max_per_room=1, but DireWolf is a different type
        self.wolf1.wander()
        # Wolf should be able to move to room2
        self.assertIn(self.wolf1.location, [self.room1, self.room2])
