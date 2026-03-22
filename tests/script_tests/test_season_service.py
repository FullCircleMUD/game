"""
Tests for the Season system.

Covers:
    - Season enum (day → season mapping, wrapping)
    - SeasonService (transition detection, broadcasts)
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest

from enums.season import Season


class TestSeasonEnum(EvenniaTest):
    """Test Season enum and day-to-season mapping."""

    def create_script(self):
        pass

    def test_spring_day_0(self):
        self.assertEqual(Season.from_day(0), Season.SPRING)

    def test_spring_day_89(self):
        self.assertEqual(Season.from_day(89), Season.SPRING)

    def test_summer_day_90(self):
        self.assertEqual(Season.from_day(90), Season.SUMMER)

    def test_summer_day_179(self):
        self.assertEqual(Season.from_day(179), Season.SUMMER)

    def test_autumn_day_180(self):
        self.assertEqual(Season.from_day(180), Season.AUTUMN)

    def test_autumn_day_269(self):
        self.assertEqual(Season.from_day(269), Season.AUTUMN)

    def test_winter_day_270(self):
        self.assertEqual(Season.from_day(270), Season.WINTER)

    def test_winter_day_359(self):
        self.assertEqual(Season.from_day(359), Season.WINTER)

    def test_wraps_at_360(self):
        """Day 360 wraps to day 0 = SPRING."""
        self.assertEqual(Season.from_day(360), Season.SPRING)

    def test_wraps_large_value(self):
        """Day 450 wraps to day 90 = SUMMER."""
        self.assertEqual(Season.from_day(450), Season.SUMMER)


class TestSeasonService(EvenniaTest):
    """Test SeasonService transition detection."""

    def create_script(self):
        pass

    @patch("typeclasses.scripts.season_service.get_season")
    def test_no_broadcast_on_same_season(self, mock_season):
        """No broadcast when season hasn't changed."""
        from typeclasses.scripts.season_service import SeasonService

        mock_season.return_value = Season.SUMMER
        service = MagicMock(spec=SeasonService)
        service.ndb = MagicMock()
        service.ndb.last_season = Season.SUMMER

        SeasonService.at_repeat(service)
        service._broadcast_transition.assert_not_called()

    @patch("typeclasses.scripts.season_service.get_season")
    def test_broadcast_on_season_change(self, mock_season):
        """Broadcast when season changes."""
        from typeclasses.scripts.season_service import SeasonService

        mock_season.return_value = Season.AUTUMN
        service = MagicMock(spec=SeasonService)
        service.ndb = MagicMock()
        service.ndb.last_season = Season.SUMMER

        SeasonService.at_repeat(service)
        service._broadcast_transition.assert_called_once_with(Season.AUTUMN)

    @patch("typeclasses.scripts.season_service.get_season")
    def test_last_season_updated_on_change(self, mock_season):
        """ndb.last_season is updated when a transition occurs."""
        from typeclasses.scripts.season_service import SeasonService

        mock_season.return_value = Season.WINTER
        service = MagicMock(spec=SeasonService)
        service.ndb = MagicMock()
        service.ndb.last_season = Season.AUTUMN

        SeasonService.at_repeat(service)
        self.assertEqual(service.ndb.last_season, Season.WINTER)
