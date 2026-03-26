"""
Tests for character death mechanics — corpse creation, double-death guard,
defeat path, and purgatory fallback.

evennia test --settings settings tests.typeclass_tests.test_character_death
"""

from unittest.mock import patch, MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from typeclasses.world_objects.corpse import Corpse


class TestCharacterDeath(EvenniaTest):
    """Test full death path — corpse, items, gold, XP penalty."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.character_key = "test-char-key-001"
        self.char1.experience_points = 1000
        self.char1.hp = 0
        self.room1.allow_combat = True
        self.room1.allow_death = True

    def _find_corpse(self, room):
        for obj in room.contents:
            if isinstance(obj, Corpse):
                return obj
        return None

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.character.delay")
    def test_die_creates_corpse(self, mock_char_delay, mock_corpse_delay):
        """Character death creates a corpse in the room."""
        self.char1.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertIsNotNone(corpse)
        self.assertEqual(corpse.key, "corpse")

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.character.delay")
    def test_corpse_owner_locked(self, mock_char_delay, mock_corpse_delay):
        """Character corpse starts locked with correct owner."""
        self.char1.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertFalse(corpse.is_unlocked)
        self.assertEqual(corpse.owner_character_key, "test-char-key-001")

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.character.delay")
    def test_xp_penalty_applied(self, mock_char_delay, mock_corpse_delay):
        """Death applies 5% XP penalty."""
        self.char1.experience_points = 1000
        self.char1.die("combat")
        self.assertEqual(self.char1.experience_points, 950)

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.character.delay")
    def test_hp_reset_to_one(self, mock_char_delay, mock_corpse_delay):
        """HP resets to 1 after death."""
        self.char1.die("combat")
        self.assertEqual(self.char1.hp, 1)

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.character.delay")
    def test_double_death_one_corpse(self, mock_char_delay, mock_corpse_delay):
        """Calling die() twice creates only one corpse."""
        self.char1.die("combat")
        self.char1.die("combat")  # should be no-op
        corpses = [obj for obj in self.room1.contents if isinstance(obj, Corpse)]
        self.assertEqual(len(corpses), 1)

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.character.delay")
    def test_double_death_single_xp_penalty(self, mock_char_delay, mock_corpse_delay):
        """Double death only applies XP penalty once."""
        self.char1.experience_points = 1000
        self.char1.die("combat")
        self.char1.die("combat")
        # 5% of 1000 = 50, applied once = 950
        self.assertEqual(self.char1.experience_points, 950)

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.character.delay")
    def test_no_purgatory_sends_home(self, mock_char_delay, mock_corpse_delay):
        """Without a purgatory room, character goes directly home."""
        home_room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Home",
        )
        self.char1.home = home_room
        self.char1.die("combat")
        self.assertEqual(self.char1.location, home_room)


class TestCharacterDefeat(EvenniaTest):
    """Test defeat path — no item loss, effects cleared."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.character_key = "test-char-key-002"
        self.char1.experience_points = 1000
        self.char1.hp = 0
        self.room1.allow_combat = True
        self.room1.allow_death = False  # defeat room

    @patch("typeclasses.world_objects.corpse.delay")
    def test_defeat_keeps_items(self, mock_delay):
        """Defeat path does not transfer items to corpse."""
        item = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="a sword",
            location=self.char1,
        )
        self.char1.die("combat")
        self.assertIn(item, self.char1.contents)

    @patch("typeclasses.world_objects.corpse.delay")
    def test_defeat_keeps_xp(self, mock_delay):
        """Defeat path does not apply XP penalty."""
        self.char1.die("combat")
        self.assertEqual(self.char1.experience_points, 1000)

    @patch("typeclasses.world_objects.corpse.delay")
    def test_defeat_clears_effects(self, mock_delay):
        """Defeat path strips all effects."""
        with patch.object(self.char1, "clear_all_effects") as mock_clear:
            self.char1.die("combat")
            mock_clear.assert_called_once()

    @patch("typeclasses.world_objects.corpse.delay")
    def test_defeat_resets_hp(self, mock_delay):
        """Defeat resets HP to 1."""
        self.char1.die("combat")
        self.assertEqual(self.char1.hp, 1)
