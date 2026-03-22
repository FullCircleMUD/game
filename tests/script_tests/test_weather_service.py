"""
Tests for the Weather system.

Covers:
    - roll_next_weather (weighted random selection)
    - get_weather (default, stored values)
    - WeatherService (tick, broadcast filtering by exposure tier)
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest

from enums.climate_zone import ClimateZone
from enums.season import Season
from enums.weather import Weather
from utils.weather_tables import roll_next_weather, get_climate_for_zone


class TestRollNextWeather(EvenniaTest):
    """Test roll_next_weather returns valid Weather values."""

    def create_script(self):
        pass

    @patch("utils.weather_tables.random.choices")
    def test_returns_selected_weather(self, mock_choices):
        """roll_next_weather returns the weather chosen by random.choices."""
        mock_choices.return_value = [Weather.RAIN]
        result = roll_next_weather(ClimateZone.TEMPERATE, Season.SPRING, Weather.CLEAR)
        self.assertEqual(result, Weather.RAIN)

    def test_returns_weather_enum(self):
        """Result is always a Weather enum member."""
        result = roll_next_weather(ClimateZone.TEMPERATE, Season.SUMMER, Weather.CLEAR)
        self.assertIsInstance(result, Weather)

    def test_unknown_climate_season_returns_clear(self):
        """Missing table entry returns CLEAR."""
        # Create a fake climate that won't be in tables
        result = roll_next_weather(
            MagicMock(), Season.SPRING, Weather.CLEAR
        )
        self.assertEqual(result, Weather.CLEAR)

    def test_unknown_current_weather_returns_clear(self):
        """Current weather not in table resets to CLEAR."""
        # BLIZZARD is not in DESERT_SUMMER table
        result = roll_next_weather(ClimateZone.DESERT, Season.SUMMER, Weather.BLIZZARD)
        self.assertEqual(result, Weather.CLEAR)


class TestGetClimateForZone(EvenniaTest):
    """Test zone-to-climate mapping."""

    def create_script(self):
        pass

    def test_known_zone(self):
        self.assertEqual(get_climate_for_zone("millhaven"), ClimateZone.TEMPERATE)

    def test_unknown_zone_defaults_temperate(self):
        self.assertEqual(get_climate_for_zone("unknown_zone"), ClimateZone.TEMPERATE)

    def test_none_zone_defaults_temperate(self):
        self.assertEqual(get_climate_for_zone(None), ClimateZone.TEMPERATE)


class TestGetWeather(EvenniaTest):
    """Test the get_weather free function."""

    def create_script(self):
        pass

    def test_no_service_returns_clear(self):
        """get_weather returns CLEAR when no service exists."""
        from typeclasses.scripts.weather_service import get_weather

        with patch("typeclasses.scripts.weather_service.GLOBAL_SCRIPTS") as mock_gs:
            mock_gs.weather_service = None
            result = get_weather("millhaven")
            self.assertEqual(result, Weather.CLEAR)

    def test_untracked_zone_returns_clear(self):
        """get_weather returns CLEAR for zones not yet tracked."""
        from typeclasses.scripts.weather_service import get_weather

        service = MagicMock()
        service.db.zone_weather = {}
        with patch("typeclasses.scripts.weather_service.GLOBAL_SCRIPTS") as mock_gs:
            mock_gs.weather_service = service
            result = get_weather("unknown_zone")
            self.assertEqual(result, Weather.CLEAR)

    def test_stored_weather_returned(self):
        """get_weather returns the stored Weather for a tracked zone."""
        from typeclasses.scripts.weather_service import get_weather

        service = MagicMock()
        service.db.zone_weather = {"millhaven": Weather.STORM.value}
        with patch("typeclasses.scripts.weather_service.GLOBAL_SCRIPTS") as mock_gs:
            mock_gs.weather_service = service
            result = get_weather("millhaven")
            self.assertEqual(result, Weather.STORM)


class TestWeatherServiceBroadcast(EvenniaTest):
    """Test WeatherService broadcast filtering by room exposure tier."""

    def create_script(self):
        pass

    def test_exposed_room_gets_full_message(self):
        """Character in an exposed room receives the full transition message."""
        from typeclasses.scripts.weather_service import WeatherService
        from utils.weather_descs import TRANSITION_MESSAGES

        char = MagicMock()
        room = MagicMock()
        room.is_subterranean = False
        room.is_sheltered = False

        service = MagicMock(spec=WeatherService)
        WeatherService._broadcast_weather_change(service, Weather.STORM, [(char, room)])
        char.msg.assert_called_once_with(TRANSITION_MESSAGES[Weather.STORM])

    def test_sheltered_room_gets_muffled_message(self):
        """Character in a sheltered room receives the muffled message."""
        from typeclasses.scripts.weather_service import WeatherService
        from utils.weather_descs import SHELTERED_TRANSITION_MESSAGES

        char = MagicMock()
        room = MagicMock()
        room.is_subterranean = False
        room.is_sheltered = True

        service = MagicMock(spec=WeatherService)
        WeatherService._broadcast_weather_change(service, Weather.STORM, [(char, room)])
        char.msg.assert_called_once_with(SHELTERED_TRANSITION_MESSAGES[Weather.STORM])

    def test_sheltered_room_no_message_for_inaudible_weather(self):
        """Sheltered room gets no message for non-audible weather (e.g. CLOUDY)."""
        from typeclasses.scripts.weather_service import WeatherService

        char = MagicMock()
        room = MagicMock()
        room.is_subterranean = False
        room.is_sheltered = True

        service = MagicMock(spec=WeatherService)
        WeatherService._broadcast_weather_change(service, Weather.CLOUDY, [(char, room)])
        char.msg.assert_not_called()

    def test_subterranean_room_gets_no_message(self):
        """Character in a subterranean room receives no message."""
        from typeclasses.scripts.weather_service import WeatherService

        char = MagicMock()
        room = MagicMock()
        room.is_subterranean = True

        service = MagicMock(spec=WeatherService)
        WeatherService._broadcast_weather_change(service, Weather.STORM, [(char, room)])
        char.msg.assert_not_called()
