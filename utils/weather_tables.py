"""
Weather transition probability tables.

Each entry maps (ClimateZone, Season) -> {current_weather: {next_weather: probability}}.
Probabilities are ints that sum to 100.

Usage:
    from utils.weather_tables import roll_next_weather
    next_weather = roll_next_weather(ClimateZone.TEMPERATE, Season.SUMMER, Weather.CLEAR)
"""

import random

from enums.climate_zone import ClimateZone
from enums.season import Season
from enums.weather import Weather


# Zone name -> ClimateZone mapping. Unmapped zones default to TEMPERATE.
ZONE_CLIMATES = {
    "millholm": ClimateZone.TEMPERATE,
}


def get_climate_for_zone(zone_name):
    """Return the ClimateZone for a zone name, defaulting to TEMPERATE."""
    if not zone_name:
        return ClimateZone.TEMPERATE
    return ZONE_CLIMATES.get(zone_name, ClimateZone.TEMPERATE)


# ================================================================== #
#  Transition tables: (ClimateZone, Season) -> {from: {to: prob}}
# ================================================================== #

# Shorthand aliases
C = Weather.CLEAR
L = Weather.CLOUDY
R = Weather.RAIN
S = Weather.STORM
N = Weather.SNOW
F = Weather.FOG
B = Weather.BLIZZARD
H = Weather.HEAT_WAVE

# ── TEMPERATE ──────────────────────────────────────────────────────

_TEMPERATE_SPRING = {
    C: {C: 45, L: 30, R: 15, F: 10},
    L: {C: 25, L: 35, R: 30, F: 10},
    R: {C: 15, L: 30, R: 40, S: 10, F: 5},
    S: {C: 10, L: 25, R: 45, S: 15, F: 5},
    F: {C: 30, L: 30, R: 15, F: 25},
}

_TEMPERATE_SUMMER = {
    C: {C: 55, L: 25, R: 10, H: 10},
    L: {C: 30, L: 35, R: 25, S: 5, H: 5},
    R: {C: 20, L: 30, R: 35, S: 15},
    S: {C: 15, L: 25, R: 40, S: 20},
    H: {C: 40, L: 20, H: 40},
}

_TEMPERATE_AUTUMN = {
    C: {C: 35, L: 35, R: 20, F: 10},
    L: {C: 20, L: 35, R: 30, F: 10, N: 5},
    R: {C: 15, L: 25, R: 40, S: 15, F: 5},
    S: {C: 10, L: 25, R: 40, S: 20, F: 5},
    F: {C: 20, L: 30, R: 15, F: 35},
    N: {C: 20, L: 30, N: 40, F: 10},
}

_TEMPERATE_WINTER = {
    C: {C: 30, L: 35, N: 20, F: 15},
    L: {C: 15, L: 30, R: 15, N: 30, F: 10},
    R: {C: 10, L: 25, R: 30, S: 15, N: 20},
    S: {C: 5, L: 20, R: 30, S: 20, N: 20, B: 5},
    N: {C: 15, L: 20, N: 40, B: 15, F: 10},
    F: {C: 20, L: 25, N: 20, F: 35},
    B: {C: 5, L: 15, N: 40, B: 35, F: 5},
}

# ── ARCTIC ─────────────────────────────────────────────────────────

_ARCTIC_SPRING = {
    C: {C: 30, L: 30, N: 25, F: 15},
    L: {C: 15, L: 30, N: 35, F: 10, R: 10},
    N: {C: 10, L: 20, N: 45, B: 15, F: 10},
    F: {C: 20, L: 25, N: 20, F: 35},
    R: {C: 15, L: 25, R: 35, N: 20, F: 5},
    B: {C: 5, L: 15, N: 40, B: 35, F: 5},
}

_ARCTIC_SUMMER = {
    C: {C: 40, L: 30, R: 15, F: 15},
    L: {C: 25, L: 35, R: 25, F: 15},
    R: {C: 20, L: 30, R: 35, S: 10, F: 5},
    S: {C: 10, L: 25, R: 40, S: 20, F: 5},
    F: {C: 25, L: 30, R: 10, F: 35},
}

_ARCTIC_AUTUMN = {
    C: {C: 25, L: 30, N: 30, F: 15},
    L: {C: 10, L: 25, N: 40, F: 10, R: 15},
    N: {C: 10, L: 15, N: 45, B: 20, F: 10},
    F: {C: 15, L: 25, N: 25, F: 35},
    R: {C: 10, L: 20, R: 30, N: 30, F: 10},
    B: {C: 5, L: 10, N: 40, B: 40, F: 5},
}

_ARCTIC_WINTER = {
    C: {C: 15, L: 25, N: 40, F: 20},
    L: {C: 5, L: 20, N: 45, B: 20, F: 10},
    N: {C: 5, L: 10, N: 40, B: 35, F: 10},
    F: {C: 10, L: 15, N: 30, F: 40, B: 5},
    B: {C: 5, L: 5, N: 35, B: 50, F: 5},
}

# ── DESERT ─────────────────────────────────────────────────────────

_DESERT_SPRING = {
    C: {C: 55, L: 25, H: 15, F: 5},
    L: {C: 40, L: 35, R: 15, H: 10},
    R: {C: 30, L: 30, R: 30, S: 10},
    S: {C: 20, L: 30, R: 35, S: 15},
    H: {C: 35, L: 15, H: 50},
    F: {C: 40, L: 30, F: 30},
}

_DESERT_SUMMER = {
    C: {C: 45, L: 20, H: 35},
    L: {C: 30, L: 30, R: 10, H: 30},
    R: {C: 25, L: 25, R: 30, S: 20},
    S: {C: 15, L: 25, R: 35, S: 25},
    H: {C: 30, L: 10, H: 60},
}

_DESERT_AUTUMN = {
    C: {C: 55, L: 25, H: 10, R: 10},
    L: {C: 35, L: 35, R: 20, H: 10},
    R: {C: 25, L: 30, R: 35, S: 10},
    S: {C: 20, L: 30, R: 30, S: 20},
    H: {C: 40, L: 20, H: 40},
}

_DESERT_WINTER = {
    C: {C: 50, L: 30, R: 15, F: 5},
    L: {C: 30, L: 35, R: 25, F: 10},
    R: {C: 20, L: 30, R: 40, S: 10},
    S: {C: 15, L: 30, R: 35, S: 20},
    F: {C: 35, L: 30, F: 35},
}

# ── TROPICAL ───────────────────────────────────────────────────────

_TROPICAL_SPRING = {
    C: {C: 35, L: 30, R: 25, H: 10},
    L: {C: 20, L: 30, R: 35, S: 10, H: 5},
    R: {C: 15, L: 20, R: 40, S: 20, H: 5},
    S: {C: 10, L: 20, R: 35, S: 30, H: 5},
    H: {C: 30, L: 25, R: 20, H: 25},
}

_TROPICAL_SUMMER = {
    C: {C: 25, L: 25, R: 30, S: 10, H: 10},
    L: {C: 15, L: 25, R: 35, S: 15, H: 10},
    R: {C: 10, L: 15, R: 40, S: 30, H: 5},
    S: {C: 5, L: 15, R: 35, S: 40, H: 5},
    H: {C: 20, L: 20, R: 25, S: 10, H: 25},
}

_TROPICAL_AUTUMN = {
    C: {C: 30, L: 30, R: 30, H: 10},
    L: {C: 20, L: 30, R: 35, S: 10, H: 5},
    R: {C: 15, L: 20, R: 40, S: 20, H: 5},
    S: {C: 10, L: 20, R: 35, S: 30, H: 5},
    H: {C: 30, L: 25, R: 20, H: 25},
}

_TROPICAL_WINTER = {
    C: {C: 40, L: 30, R: 20, H: 10},
    L: {C: 25, L: 35, R: 30, S: 5, H: 5},
    R: {C: 20, L: 25, R: 35, S: 15, H: 5},
    S: {C: 10, L: 25, R: 35, S: 25, H: 5},
    H: {C: 35, L: 25, R: 15, H: 25},
}

# ── COASTAL ────────────────────────────────────────────────────────

_COASTAL_SPRING = {
    C: {C: 35, L: 30, R: 15, F: 20},
    L: {C: 20, L: 30, R: 25, S: 5, F: 20},
    R: {C: 15, L: 25, R: 35, S: 15, F: 10},
    S: {C: 10, L: 20, R: 35, S: 25, F: 10},
    F: {C: 25, L: 25, R: 10, F: 40},
}

_COASTAL_SUMMER = {
    C: {C: 45, L: 25, R: 10, F: 15, H: 5},
    L: {C: 25, L: 30, R: 20, S: 5, F: 15, H: 5},
    R: {C: 20, L: 25, R: 30, S: 15, F: 10},
    S: {C: 10, L: 20, R: 30, S: 30, F: 10},
    F: {C: 30, L: 25, R: 5, F: 40},
    H: {C: 35, L: 20, F: 10, H: 35},
}

_COASTAL_AUTUMN = {
    C: {C: 30, L: 30, R: 15, F: 25},
    L: {C: 15, L: 30, R: 25, S: 10, F: 20},
    R: {C: 10, L: 25, R: 35, S: 15, F: 15},
    S: {C: 10, L: 15, R: 30, S: 30, F: 15},
    F: {C: 20, L: 25, R: 10, F: 45},
}

_COASTAL_WINTER = {
    C: {C: 25, L: 30, R: 15, N: 10, F: 20},
    L: {C: 10, L: 25, R: 20, S: 10, N: 15, F: 20},
    R: {C: 10, L: 20, R: 30, S: 20, N: 10, F: 10},
    S: {C: 5, L: 15, R: 25, S: 30, N: 10, F: 10, B: 5},
    N: {C: 10, L: 20, N: 40, B: 10, F: 20},
    F: {C: 15, L: 20, R: 10, N: 10, F: 45},
    B: {C: 5, L: 15, N: 30, B: 40, F: 10},
}


# ================================================================== #
#  Master lookup table
# ================================================================== #

WEATHER_TRANSITIONS = {
    # Temperate
    (ClimateZone.TEMPERATE, Season.SPRING): _TEMPERATE_SPRING,
    (ClimateZone.TEMPERATE, Season.SUMMER): _TEMPERATE_SUMMER,
    (ClimateZone.TEMPERATE, Season.AUTUMN): _TEMPERATE_AUTUMN,
    (ClimateZone.TEMPERATE, Season.WINTER): _TEMPERATE_WINTER,
    # Arctic
    (ClimateZone.ARCTIC, Season.SPRING): _ARCTIC_SPRING,
    (ClimateZone.ARCTIC, Season.SUMMER): _ARCTIC_SUMMER,
    (ClimateZone.ARCTIC, Season.AUTUMN): _ARCTIC_AUTUMN,
    (ClimateZone.ARCTIC, Season.WINTER): _ARCTIC_WINTER,
    # Desert
    (ClimateZone.DESERT, Season.SPRING): _DESERT_SPRING,
    (ClimateZone.DESERT, Season.SUMMER): _DESERT_SUMMER,
    (ClimateZone.DESERT, Season.AUTUMN): _DESERT_AUTUMN,
    (ClimateZone.DESERT, Season.WINTER): _DESERT_WINTER,
    # Tropical
    (ClimateZone.TROPICAL, Season.SPRING): _TROPICAL_SPRING,
    (ClimateZone.TROPICAL, Season.SUMMER): _TROPICAL_SUMMER,
    (ClimateZone.TROPICAL, Season.AUTUMN): _TROPICAL_AUTUMN,
    (ClimateZone.TROPICAL, Season.WINTER): _TROPICAL_WINTER,
    # Coastal
    (ClimateZone.COASTAL, Season.SPRING): _COASTAL_SPRING,
    (ClimateZone.COASTAL, Season.SUMMER): _COASTAL_SUMMER,
    (ClimateZone.COASTAL, Season.AUTUMN): _COASTAL_AUTUMN,
    (ClimateZone.COASTAL, Season.WINTER): _COASTAL_WINTER,
}


def roll_next_weather(climate, season, current_weather):
    """
    Roll the next weather state using transition probabilities.

    Args:
        climate (ClimateZone): The zone's climate.
        season (Season): The current season.
        current_weather (Weather): The current weather state.

    Returns:
        Weather: The next weather state.
    """
    table = WEATHER_TRANSITIONS.get((climate, season))
    if not table:
        return Weather.CLEAR

    transitions = table.get(current_weather)
    if not transitions:
        # Current weather not in table for this climate/season — reset to CLEAR
        return Weather.CLEAR

    choices = list(transitions.keys())
    weights = list(transitions.values())
    return random.choices(choices, weights=weights, k=1)[0]
