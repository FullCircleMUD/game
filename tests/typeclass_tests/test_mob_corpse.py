"""
Tests for mob corpse creation on death.

Verifies that CombatMob.die() creates a lootable Corpse object,
transfers contents, and that the corpse is immediately unlocked.

evennia test --settings settings tests.typeclass_tests.test_mob_corpse
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from typeclasses.world_objects.corpse import Corpse


class TestMobCorpse(EvenniaTest):
    """Test corpse creation when a CombatMob dies."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin",
            location=self.room1,
        )
        self.mob.hp = 10
        self.mob.hp_max = 10
        self.mob.is_alive = True

    def _find_corpse(self, room):
        """Find the first Corpse in a room."""
        for obj in room.contents:
            if isinstance(obj, Corpse):
                return obj
        return None

    @patch("evennia.utils.utils.delay")
    def test_die_creates_corpse_in_room(self, mock_delay):
        self.mob.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertIsNotNone(corpse)

    @patch("evennia.utils.utils.delay")
    def test_corpse_has_mob_name(self, mock_delay):
        self.mob.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertEqual(corpse.owner_name, "a goblin")
        self.assertEqual(corpse.key, "corpse")

    @patch("evennia.utils.utils.delay")
    def test_corpse_cause_of_death(self, mock_delay):
        self.mob.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertEqual(corpse.cause_of_death, "combat")

    @patch("evennia.utils.utils.delay")
    def test_corpse_is_immediately_unlocked(self, mock_delay):
        self.mob.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertTrue(corpse.is_unlocked)

    @patch("evennia.utils.utils.delay")
    def test_corpse_no_owner(self, mock_delay):
        self.mob.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertIsNone(corpse.owner_character_key)

    @patch("evennia.utils.utils.delay")
    def test_corpse_receives_contents(self, mock_delay):
        """Items on the mob should transfer to the corpse."""
        item = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="a rusty sword",
            location=self.mob,
        )
        self.mob.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertIn(item, corpse.contents)
        self.assertNotIn(item, self.mob.contents)

    @patch("evennia.utils.utils.delay")
    def test_empty_mob_still_creates_corpse(self, mock_delay):
        """A mob with no contents should still leave a corpse."""
        self.assertEqual(len(self.mob.contents), 0)
        self.mob.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertIsNotNone(corpse)

    @patch("evennia.utils.utils.delay")
    def test_mob_removed_from_world_after_death(self, mock_delay):
        self.mob.die("combat")
        self.assertIsNone(self.mob.location)

    @patch("typeclasses.actors.mob.delay")
    def test_mob_schedules_respawn(self, mock_delay):
        """Respawn delay should still be scheduled."""
        self.mob.is_unique = True
        self.mob.respawn_delay = 60
        self.mob.die("combat")
        # The mob's die() calls delay(respawn_delay, self._respawn)
        respawn_calls = [
            c for c in mock_delay.call_args_list
            if c[0][0] == 60
        ]
        self.assertEqual(len(respawn_calls), 1)

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.mob.delay")
    def test_corpse_despawn_delay_configurable(self, mock_mob_delay, mock_corpse_delay):
        self.mob.corpse_despawn_delay = 120
        self.mob.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertIsNotNone(corpse.despawn_at)
        # Check corpse delay was scheduled with the custom value
        despawn_calls = [
            c for c in mock_corpse_delay.call_args_list
            if c[0][0] == 120
        ]
        self.assertEqual(len(despawn_calls), 1)

    @patch("evennia.utils.utils.delay")
    def test_double_death_no_second_corpse(self, mock_delay):
        """Calling die() twice should only create one corpse."""
        self.mob.is_unique = True  # prevent deletion so is_alive check works
        self.mob.die("combat")
        self.mob.die("combat")  # should be no-op
        corpses = [obj for obj in self.room1.contents if isinstance(obj, Corpse)]
        self.assertEqual(len(corpses), 1)

    @patch("evennia.utils.utils.delay")
    def test_can_loot_returns_true_for_any_character(self, mock_delay):
        """Any character should be able to loot a mob corpse."""
        self.mob.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertTrue(corpse.can_loot(self.char1))
