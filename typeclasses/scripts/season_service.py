"""
SeasonService — global script that tracks the game-world season.

Ticks every 5 real minutes, checks the current game day via Evennia's
gametime module, and detects season transitions (SPRING/SUMMER/AUTUMN/WINTER).

Game calendar: 360-day year, 90 days per season.
At TIME_FACTOR=24: 1 real hour = 1 game day, 1 season = 3.75 real days.

Query the current season from anywhere:
    from typeclasses.scripts.season_service import get_season
    season = get_season()
"""

from datetime import datetime

from evennia import DefaultScript, ObjectDB
from evennia.utils.gametime import gametime

from enums.season import Season


# How often (real seconds) the service checks for season transitions.
TICK_INTERVAL_SECONDS = 300  # 5 real minutes


# Messages broadcast to all players on season transitions
_TRANSITION_MESSAGES = {
    Season.SPRING: "|gThe chill of winter fades as the first buds of spring appear.|n",
    Season.SUMMER: "|YThe warmth of summer settles over the land.|n",
    Season.AUTUMN: "|rThe leaves begin to turn as autumn arrives.|n",
    Season.WINTER: "|wA cold wind sweeps in, heralding the onset of winter.|n",
}


def get_day_of_year():
    """
    Return the current game day of the year (0–359).

    Derives from Evennia's gametime: extract the day-of-year from the
    game timestamp, then map to a 360-day calendar via modulo.
    """
    game_timestamp = gametime(absolute=True)
    dt = datetime.fromtimestamp(game_timestamp)
    # Evennia uses a standard 365-day year internally.
    # Map to our 360-day calendar: use day_of_year mod 360.
    return dt.timetuple().tm_yday % 360


def get_season():
    """
    Return the current Season.

    Can be called from anywhere — no script instance needed.
    """
    return Season.from_day(get_day_of_year())


class SeasonService(DefaultScript):
    """
    Global persistent script that tracks season transitions.

    Created once via at_server_startstop._ensure_global_scripts().
    """

    def at_script_creation(self):
        self.key = "season_service"
        self.desc = "Tracks game-world seasons and broadcasts transitions"
        self.interval = TICK_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = True
        self.repeats = 0  # repeat forever

    def at_start(self, **kwargs):
        """Initialise tracking state on first start or reload."""
        self.ndb.last_season = get_season()

    def at_repeat(self):
        """Check for season transition and broadcast if one occurred."""
        current_season = get_season()
        last_season = self.ndb.last_season

        if current_season != last_season:
            self.ndb.last_season = current_season
            self._broadcast_transition(current_season)

    def _broadcast_transition(self, season):
        """Send the transition message to all connected player characters."""
        msg = _TRANSITION_MESSAGES.get(season)
        if not msg:
            return

        for char in ObjectDB.objects.filter(
            db_typeclass_path__contains="Character"
        ):
            if char.has_account and char.sessions.count():
                char.msg(msg)
