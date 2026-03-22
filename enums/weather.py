"""
Weather states for the weather system.

Query the current weather for a zone from anywhere:
    from typeclasses.scripts.weather_service import get_weather
    weather = get_weather("millhaven")
"""

from enum import Enum


class Weather(Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    STORM = "storm"
    SNOW = "snow"
    FOG = "fog"
    BLIZZARD = "blizzard"
    HEAT_WAVE = "heat_wave"
