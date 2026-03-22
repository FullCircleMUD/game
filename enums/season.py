"""
Season enum — derived from the game calendar (360-day year, 90 days per season).

Query the current season from anywhere:
    from typeclasses.scripts.season_service import get_season
    season = get_season()
"""

from enum import Enum


class Season(Enum):
    SPRING = "spring"   # days 0–89
    SUMMER = "summer"   # days 90–179
    AUTUMN = "autumn"   # days 180–269
    WINTER = "winter"   # days 270–359

    @classmethod
    def from_day(cls, day_of_year):
        """
        Return the Season for a given game day (0–359).

        Days wrap via modulo so values >= 360 work correctly.
        """
        day = day_of_year % 360
        if day < 90:
            return cls.SPRING
        elif day < 180:
            return cls.SUMMER
        elif day < 270:
            return cls.AUTUMN
        else:
            return cls.WINTER
