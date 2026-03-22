"""
Tests for room weather exposure properties and weather description lines.

Covers:
    - is_subterranean, is_sheltered, is_weather_exposed properties
    - sheltered override via AttributeProperty
    - Weather description lines in get_display_desc
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from enums.terrain_type import TerrainType
from enums.time_of_day import TimeOfDay
from enums.weather import Weather


class TestWeatherExposure(EvenniaTest):
    """Test room weather exposure tier properties."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_forest_is_weather_exposed(self):
        """Forest room is fully exposed to weather."""
        self.room1.set_terrain(TerrainType.FOREST.value)
        self.assertTrue(self.room1.is_weather_exposed)
        self.assertFalse(self.room1.is_sheltered)
        self.assertFalse(self.room1.is_subterranean)

    def test_plains_is_weather_exposed(self):
        self.room1.set_terrain(TerrainType.PLAINS.value)
        self.assertTrue(self.room1.is_weather_exposed)

    def test_mountain_is_weather_exposed(self):
        self.room1.set_terrain(TerrainType.MOUNTAIN.value)
        self.assertTrue(self.room1.is_weather_exposed)

    def test_urban_is_sheltered(self):
        """Urban room is sheltered by default."""
        self.room1.set_terrain(TerrainType.URBAN.value)
        self.assertTrue(self.room1.is_sheltered)
        self.assertFalse(self.room1.is_weather_exposed)
        self.assertFalse(self.room1.is_subterranean)

    def test_underground_is_subterranean(self):
        """Underground room is subterranean."""
        self.room1.set_terrain(TerrainType.UNDERGROUND.value)
        self.assertTrue(self.room1.is_subterranean)
        self.assertFalse(self.room1.is_weather_exposed)

    def test_dungeon_is_subterranean(self):
        """Dungeon room is subterranean."""
        self.room1.set_terrain(TerrainType.DUNGEON.value)
        self.assertTrue(self.room1.is_subterranean)
        self.assertFalse(self.room1.is_weather_exposed)

    def test_no_terrain_is_exposed(self):
        """Room with no terrain tag is exposed (not sheltered, not subterranean)."""
        self.assertTrue(self.room1.is_weather_exposed)
        self.assertFalse(self.room1.is_sheltered)
        self.assertFalse(self.room1.is_subterranean)

    def test_sheltered_override_true(self):
        """Explicit sheltered=True on a forest room makes it sheltered."""
        self.room1.set_terrain(TerrainType.FOREST.value)
        self.room1.sheltered = True
        self.assertTrue(self.room1.is_sheltered)
        self.assertFalse(self.room1.is_weather_exposed)

    def test_sheltered_override_false(self):
        """Explicit sheltered=False on an urban room makes it exposed."""
        self.room1.set_terrain(TerrainType.URBAN.value)
        self.room1.sheltered = False
        self.assertFalse(self.room1.is_sheltered)
        self.assertTrue(self.room1.is_weather_exposed)


class TestWeatherDescLine(EvenniaTest):
    """Test weather description lines in get_display_desc."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    @patch("typeclasses.scripts.weather_service.get_weather")
    def test_exposed_rain_shows_desc(self, mock_weather, mock_tod):
        """Exposed room during rain shows rain description."""
        mock_tod.return_value = TimeOfDay.DAY
        mock_weather.return_value = Weather.RAIN
        self.room1.set_terrain(TerrainType.FOREST.value)
        self.room1.db.desc = "A dense forest."
        desc = self.room1.get_display_desc(self.char1)
        self.assertIn("Rain falls steadily", desc)
        self.assertIn("A dense forest.", desc)

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    @patch("typeclasses.scripts.weather_service.get_weather")
    def test_exposed_clear_no_weather_line(self, mock_weather, mock_tod):
        """Exposed room during clear weather has no weather line."""
        mock_tod.return_value = TimeOfDay.DAY
        mock_weather.return_value = Weather.CLEAR
        self.room1.set_terrain(TerrainType.FOREST.value)
        self.room1.db.desc = "A dense forest."
        desc = self.room1.get_display_desc(self.char1)
        self.assertEqual(desc, "A dense forest.")

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    @patch("typeclasses.scripts.weather_service.get_weather")
    def test_sheltered_storm_shows_muffled(self, mock_weather, mock_tod):
        """Sheltered room during storm shows muffled thunder."""
        mock_tod.return_value = TimeOfDay.DAY
        mock_weather.return_value = Weather.STORM
        self.room1.set_terrain(TerrainType.URBAN.value)
        self.room1.db.desc = "A cozy shop."
        desc = self.room1.get_display_desc(self.char1)
        self.assertIn("Thunder rumbles outside", desc)

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    @patch("typeclasses.scripts.weather_service.get_weather")
    def test_sheltered_fog_no_weather_line(self, mock_weather, mock_tod):
        """Sheltered room during fog has no weather line (not audible)."""
        mock_tod.return_value = TimeOfDay.DAY
        mock_weather.return_value = Weather.FOG
        self.room1.set_terrain(TerrainType.URBAN.value)
        self.room1.db.desc = "A cozy shop."
        desc = self.room1.get_display_desc(self.char1)
        self.assertEqual(desc, "A cozy shop.")

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    @patch("typeclasses.scripts.weather_service.get_weather")
    def test_subterranean_no_weather_line(self, mock_weather, mock_tod):
        """Subterranean room never shows weather."""
        mock_tod.return_value = TimeOfDay.DAY
        mock_weather.return_value = Weather.STORM
        self.room1.set_terrain(TerrainType.DUNGEON.value)
        # Must provide light to avoid pitch-black override
        self.room1.natural_light = True
        self.room1.db.desc = "A dark dungeon."
        desc = self.room1.get_display_desc(self.char1)
        self.assertNotIn("Thunder", desc)
        self.assertNotIn("Lightning", desc)
        self.assertEqual(desc, "A dark dungeon.")

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    @patch("typeclasses.scripts.weather_service.get_weather")
    def test_exposed_blizzard_shows_desc(self, mock_weather, mock_tod):
        """Exposed room during blizzard shows blizzard description."""
        mock_tod.return_value = TimeOfDay.DAY
        mock_weather.return_value = Weather.BLIZZARD
        self.room1.set_terrain(TerrainType.ARCTIC.value)
        self.room1.db.desc = "A frozen wasteland."
        desc = self.room1.get_display_desc(self.char1)
        self.assertIn("Driving snow", desc)

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    @patch("typeclasses.scripts.weather_service.get_weather")
    def test_sheltered_blizzard_shows_muffled(self, mock_weather, mock_tod):
        """Sheltered room during blizzard shows muffled wind."""
        mock_tod.return_value = TimeOfDay.DAY
        mock_weather.return_value = Weather.BLIZZARD
        self.room1.sheltered = True
        self.room1.db.desc = "A warm cabin."
        desc = self.room1.get_display_desc(self.char1)
        self.assertIn("wind howls outside", desc)
