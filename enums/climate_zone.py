"""
Climate zones — determine weather transition probabilities per zone.

Each game zone maps to a ClimateZone via ZONE_CLIMATES in weather_tables.py.
Unmapped zones default to TEMPERATE.
"""

from enum import Enum


class ClimateZone(Enum):
    TEMPERATE = "temperate"   # balanced weather, all types possible
    ARCTIC = "arctic"         # snow/blizzard bias, no heat wave
    DESERT = "desert"         # dry bias, heat wave common, no snow
    TROPICAL = "tropical"     # heavy rain/storms, no snow
    COASTAL = "coastal"       # fog common, sea storms
