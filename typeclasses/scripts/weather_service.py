"""
WeatherService — global script that manages per-zone weather states.

Ticks every 3 real minutes, rolls weather transitions for each zone
with connected players using probabilistic tables based on climate
zone and current season.

At TIME_FACTOR=24: 3 real minutes ≈ 1.2 game hours.

Query the current weather for any zone from anywhere:
    from typeclasses.scripts.weather_service import get_weather
    weather = get_weather("millhaven")
"""

from evennia import DefaultScript, ObjectDB, GLOBAL_SCRIPTS

from enums.weather import Weather
from typeclasses.scripts.season_service import get_season
from utils.weather_descs import (
    TRANSITION_MESSAGES,
    SHELTERED_TRANSITION_MESSAGES,
)
from utils.weather_tables import get_climate_for_zone, roll_next_weather


# How often (real seconds) the service rolls weather transitions.
TICK_INTERVAL_SECONDS = 180  # 3 real minutes


def get_weather(zone_name):
    """
    Return the current Weather for a zone.

    Returns Weather.CLEAR if the zone has no tracked weather yet.
    Can be called from anywhere — no script instance needed.
    """
    service = getattr(GLOBAL_SCRIPTS, "weather_service", None)
    if not service:
        return Weather.CLEAR
    zone_weather = service.db.zone_weather or {}
    weather_value = zone_weather.get(zone_name)
    if weather_value is None:
        return Weather.CLEAR
    # Stored as string value for DB serialisation safety
    try:
        return Weather(weather_value)
    except ValueError:
        return Weather.CLEAR


class WeatherService(DefaultScript):
    """
    Global persistent script that manages per-zone weather.

    Weather state is persisted in self.db.zone_weather so it
    survives server reloads.
    """

    def at_script_creation(self):
        self.key = "weather_service"
        self.desc = "Manages per-zone weather states with probabilistic transitions"
        self.interval = TICK_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = True
        self.repeats = 0  # repeat forever
        self.db.zone_weather = {}

    def at_start(self, **kwargs):
        """Ensure zone_weather dict exists after reload."""
        if self.db.zone_weather is None:
            self.db.zone_weather = {}

    def at_repeat(self):
        """Roll weather transitions for zones with connected players."""
        # Gather zones with connected players and their rooms
        zone_chars = self._get_zone_characters()
        if not zone_chars:
            return

        season = get_season()
        zone_weather = dict(self.db.zone_weather or {})

        for zone_name, chars_with_rooms in zone_chars.items():
            climate = get_climate_for_zone(zone_name)
            current_value = zone_weather.get(zone_name, Weather.CLEAR.value)
            try:
                current = Weather(current_value)
            except ValueError:
                current = Weather.CLEAR

            new_weather = roll_next_weather(climate, season, current)
            zone_weather[zone_name] = new_weather.value

            if new_weather != current:
                self._broadcast_weather_change(new_weather, chars_with_rooms)

        self.db.zone_weather = zone_weather

    def _get_zone_characters(self):
        """
        Return a dict of {zone_name: [(char, room), ...]} for all
        connected player characters, grouped by their room's zone.

        Characters in rooms with no zone are skipped.
        """
        zone_chars = {}
        for char in ObjectDB.objects.filter(
            db_typeclass_path__contains="Character"
        ):
            if not (char.has_account and char.sessions.count()):
                continue
            room = char.location
            if not room or not hasattr(room, "get_zone"):
                continue
            zone = room.get_zone()
            if not zone:
                continue
            zone_chars.setdefault(zone, []).append((char, room))
        return zone_chars

    def _broadcast_weather_change(self, weather, chars_with_rooms):
        """
        Send weather transition messages to characters based on their
        room's weather exposure tier.

        Exposed rooms get the full transition message.
        Sheltered rooms get muffled variants (for audible weather only).
        Subterranean rooms get nothing.
        """
        exposed_msg = TRANSITION_MESSAGES.get(weather)
        sheltered_msg = SHELTERED_TRANSITION_MESSAGES.get(weather)

        for char, room in chars_with_rooms:
            if hasattr(room, "is_subterranean") and room.is_subterranean:
                continue

            if hasattr(room, "is_sheltered") and room.is_sheltered:
                if sheltered_msg:
                    char.msg(sheltered_msg)
            elif exposed_msg:
                char.msg(exposed_msg)
