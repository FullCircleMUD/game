"""
Tests for the DurabilityDecayService.

Covers:
    - get_game_day_number() utility
    - DurabilityDecayService tick logic (IC-only, skip unbreakable, async stagger)
"""

from unittest.mock import patch, MagicMock, call

from evennia.utils.test_resources import EvenniaTest

from typeclasses.scripts.durability_decay_service import (
    get_game_day_number,
    DurabilityDecayService,
)


class TestGetGameDayNumber(EvenniaTest):

    def create_script(self):
        pass

    @patch("typeclasses.scripts.durability_decay_service.gametime")
    def test_returns_integer(self, mock_gametime):
        from datetime import datetime

        mock_gametime.return_value = datetime(2026, 1, 1).timestamp()
        result = get_game_day_number()
        self.assertIsInstance(result, int)

    @patch("typeclasses.scripts.durability_decay_service.gametime")
    def test_monotonically_increasing(self, mock_gametime):
        from datetime import datetime

        mock_gametime.return_value = datetime(2026, 1, 1).timestamp()
        day1 = get_game_day_number()
        mock_gametime.return_value = datetime(2026, 1, 2).timestamp()
        day2 = get_game_day_number()
        self.assertGreater(day2, day1)


class TestDurabilityDecayService(EvenniaTest):

    def create_script(self):
        pass

    def _make_mock_item(self, max_dur, dur, item_id=1):
        item = MagicMock()
        item.id = item_id
        item.max_durability = max_dur
        item.durability = dur
        return item

    def _make_mock_char(self, equipped_items=None):
        char = MagicMock()
        char.has_account = True
        char.sessions.count.return_value = 1
        char.get_all_worn.return_value = equipped_items or {}
        return char

    @patch("typeclasses.scripts.durability_decay_service.delay")
    @patch("typeclasses.scripts.durability_decay_service.ObjectDB")
    @patch("typeclasses.scripts.durability_decay_service.get_game_day_number")
    def test_no_decay_when_same_day(self, mock_day, mock_odb, mock_delay):
        """No processing when the game day hasn't changed."""
        mock_day.return_value = 100

        service = MagicMock(spec=DurabilityDecayService)
        service.ndb = MagicMock()
        service.ndb.last_game_day = 100

        DurabilityDecayService.at_repeat(service)
        mock_delay.assert_not_called()

    @patch("typeclasses.scripts.durability_decay_service.delay")
    @patch("typeclasses.scripts.durability_decay_service.ObjectDB")
    @patch("typeclasses.scripts.durability_decay_service.get_game_day_number")
    def test_schedules_decay_on_day_change(self, mock_day, mock_odb, mock_delay):
        """IC characters get scheduled for decay when the day advances."""
        mock_day.return_value = 101
        char = self._make_mock_char()
        mock_odb.objects.filter.return_value = [char]

        service = MagicMock(spec=DurabilityDecayService)
        service.ndb = MagicMock()
        service.ndb.last_game_day = 100

        DurabilityDecayService.at_repeat(service)
        mock_delay.assert_called_once()
        self.assertEqual(service.ndb.last_game_day, 101)

    @patch("typeclasses.scripts.durability_decay_service.delay")
    @patch("typeclasses.scripts.durability_decay_service.ObjectDB")
    @patch("typeclasses.scripts.durability_decay_service.get_game_day_number")
    def test_skips_offline_characters(self, mock_day, mock_odb, mock_delay):
        """Characters without an active session are skipped."""
        mock_day.return_value = 101
        offline_char = MagicMock()
        offline_char.has_account = True
        offline_char.sessions.count.return_value = 0
        mock_odb.objects.filter.return_value = [offline_char]

        service = MagicMock(spec=DurabilityDecayService)
        service.ndb = MagicMock()
        service.ndb.last_game_day = 100

        DurabilityDecayService.at_repeat(service)
        mock_delay.assert_not_called()

    def test_decay_reduces_durability_by_1(self):
        """Each equipped item loses 1 durability."""
        item = self._make_mock_item(max_dur=1440, dur=1440, item_id=1)
        char = self._make_mock_char({"body": item})

        service = DurabilityDecayService.__new__(DurabilityDecayService)
        service._decay_equipped(char)

        item.reduce_durability.assert_called_once_with(1)

    def test_decay_skips_unbreakable_items(self):
        """Items with max_durability=0 are not decayed."""
        item = self._make_mock_item(max_dur=0, dur=0, item_id=1)
        char = self._make_mock_char({"body": item})

        service = DurabilityDecayService.__new__(DurabilityDecayService)
        service._decay_equipped(char)

        item.reduce_durability.assert_not_called()

    def test_decay_deduplicates_slots(self):
        """Same item in multiple slots only decayed once."""
        item = self._make_mock_item(max_dur=3600, dur=3600, item_id=42)
        char = self._make_mock_char({"left_hand": item, "right_hand": item})

        service = DurabilityDecayService.__new__(DurabilityDecayService)
        service._decay_equipped(char)

        item.reduce_durability.assert_called_once_with(1)

    def test_decay_multiple_items(self):
        """Multiple different equipped items each lose 1."""
        sword = self._make_mock_item(max_dur=5400, dur=5400, item_id=1)
        helm = self._make_mock_item(max_dur=3600, dur=3600, item_id=2)
        char = self._make_mock_char({"right_hand": sword, "head": helm})

        service = DurabilityDecayService.__new__(DurabilityDecayService)
        service._decay_equipped(char)

        sword.reduce_durability.assert_called_once_with(1)
        helm.reduce_durability.assert_called_once_with(1)

    def test_decay_skips_none_slots(self):
        """Empty slots (None values) are safely skipped."""
        char = self._make_mock_char({"body": None, "head": None})

        service = DurabilityDecayService.__new__(DurabilityDecayService)
        # Should not raise
        service._decay_equipped(char)

    @patch("typeclasses.scripts.durability_decay_service.delay")
    @patch("typeclasses.scripts.durability_decay_service.ObjectDB")
    @patch("typeclasses.scripts.durability_decay_service.get_game_day_number")
    def test_staggered_delay(self, mock_day, mock_odb, mock_delay):
        """Multiple IC characters are staggered 0.1s apart."""
        mock_day.return_value = 101
        char1 = self._make_mock_char()
        char2 = self._make_mock_char()
        mock_odb.objects.filter.return_value = [char1, char2]

        service = MagicMock(spec=DurabilityDecayService)
        service.ndb = MagicMock()
        service.ndb.last_game_day = 100

        DurabilityDecayService.at_repeat(service)

        self.assertEqual(mock_delay.call_count, 2)
        # First char at 0.0s, second at 0.1s
        self.assertAlmostEqual(mock_delay.call_args_list[0][0][0], 0.0)
        self.assertAlmostEqual(mock_delay.call_args_list[1][0][0], 0.1)
