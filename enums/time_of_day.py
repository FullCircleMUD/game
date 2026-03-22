"""
Time-of-day phases for the day/night cycle.

Used by DayNightService to track the current phase and by rooms
to determine natural lighting state.
"""

from enum import Enum


class TimeOfDay(Enum):
    DAWN = "dawn"       # 5:00 – 7:59
    DAY = "day"         # 8:00 – 17:59
    DUSK = "dusk"       # 18:00 – 20:59
    NIGHT = "night"     # 21:00 – 4:59

    @property
    def is_light(self):
        """True during phases where natural light is available."""
        return self in (TimeOfDay.DAWN, TimeOfDay.DAY, TimeOfDay.DUSK)

    @classmethod
    def from_hour(cls, hour):
        """
        Return the TimeOfDay phase for a given game hour (0–23).

        Args:
            hour (int): Game hour, 0–23.

        Returns:
            TimeOfDay: The corresponding phase.
        """
        if 5 <= hour < 8:
            return cls.DAWN
        elif 8 <= hour < 18:
            return cls.DAY
        elif 18 <= hour < 21:
            return cls.DUSK
        else:
            return cls.NIGHT
