"""
Tests for the looker_is_blind() visibility predicate.

evennia test --settings settings tests.utils_tests.test_visibility
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition
from enums.time_of_day import TimeOfDay
from utils.visibility import looker_is_blind


class TestLookerIsBlind(EvenniaTest):
    """Test looker_is_blind() against room darkness and BLINDED."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_sighted_in_lit_room_not_blind(self):
        self.room1.always_lit = True
        self.assertFalse(looker_is_blind(self.char1))

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_no_darkvision_in_dark_room_is_blind(self, mock_tod):
        mock_tod.return_value = TimeOfDay.NIGHT
        self.assertTrue(looker_is_blind(self.char1))

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_darkvision_in_dark_room_not_blind(self, mock_tod):
        mock_tod.return_value = TimeOfDay.NIGHT
        self.char1.add_condition(Condition.DARKVISION)
        self.assertFalse(looker_is_blind(self.char1))

    def test_blinded_condition_in_lit_room_is_blind(self):
        """BLINDED applies regardless of room lighting."""
        self.room1.always_lit = True
        self.char1.add_condition(Condition.BLINDED)
        self.assertTrue(looker_is_blind(self.char1))

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_blinded_with_darkvision_still_blind(self, mock_tod):
        """DARKVISION defeats room darkness, not the BLINDED condition."""
        mock_tod.return_value = TimeOfDay.NIGHT
        self.char1.add_condition(Condition.DARKVISION)
        self.char1.add_condition(Condition.BLINDED)
        self.assertTrue(looker_is_blind(self.char1))


class TestActorRoomNameRedaction(EvenniaTest):
    """Test that get_display_name() redacts to placeholders when blind."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_character_name_redacted_in_dark_room(self, mock_tod):
        mock_tod.return_value = TimeOfDay.NIGHT
        self.assertEqual(self.char2.get_display_name(self.char1), "Someone")

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_room_name_redacted_for_blind_looker(self, mock_tod):
        mock_tod.return_value = TimeOfDay.NIGHT
        self.assertEqual(self.room1.get_display_name(self.char1), "Somewhere")

    def test_character_name_shown_when_sighted(self):
        self.room1.always_lit = True
        self.assertEqual(self.char2.get_display_name(self.char1), self.char2.key)

    def test_room_name_shown_when_sighted(self):
        self.room1.always_lit = True
        self.assertEqual(self.room1.get_display_name(self.char1), self.room1.key)

    def test_character_name_redacted_when_blinded_in_lit_room(self):
        self.room1.always_lit = True
        self.char1.add_condition(Condition.BLINDED)
        self.assertEqual(self.char2.get_display_name(self.char1), "Someone")
