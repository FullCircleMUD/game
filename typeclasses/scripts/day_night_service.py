"""
DayNightService — global script that tracks the game-world time of day.

Ticks every 30 real seconds, checks the current game hour via Evennia's
gametime module, and detects phase transitions (DAWN/DAY/DUSK/NIGHT).

When a transition occurs, it broadcasts a message to all connected players.

Query the current phase from anywhere:
    from typeclasses.scripts.day_night_service import get_time_of_day
    phase = get_time_of_day()
"""

from datetime import datetime

from evennia import DefaultScript, ObjectDB
from evennia.utils.gametime import gametime

from enums.time_of_day import TimeOfDay


# How often (real seconds) the service checks for phase transitions.
TICK_INTERVAL_SECONDS = 30


# Messages broadcast to all players on phase transitions
_TRANSITION_MESSAGES = {
    TimeOfDay.DAWN: "|yThe first light of dawn breaks over the horizon.|n",
    TimeOfDay.DAY: "|YThe sun rises fully, bathing the world in daylight.|n",
    TimeOfDay.DUSK: "|rThe sun begins to set, casting long shadows across the land.|n",
    TimeOfDay.NIGHT: "|xDarkness falls as night settles over the world.|n",
}


def get_game_hour():
    """Return the current game hour (0–23)."""
    game_timestamp = gametime(absolute=True)
    return datetime.fromtimestamp(game_timestamp).hour


def get_time_of_day():
    """
    Return the current TimeOfDay phase.

    Can be called from anywhere — no script instance needed.
    """
    return TimeOfDay.from_hour(get_game_hour())


class DayNightService(DefaultScript):
    """
    Global persistent script that tracks day/night phase transitions.

    Created once via: evennia.create_script("typeclasses.scripts.day_night_service.DayNightService")
    """

    def at_script_creation(self):
        self.key = "day_night_service"
        self.desc = "Tracks game-world time of day and broadcasts phase transitions"
        self.interval = TICK_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = True
        self.repeats = 0  # repeat forever

    def at_start(self, **kwargs):
        """Initialise tracking state on first start or reload."""
        self.ndb.last_phase = get_time_of_day()

    def at_repeat(self):
        """Check for phase transition and broadcast if one occurred."""
        current_phase = get_time_of_day()
        last_phase = self.ndb.last_phase

        if current_phase != last_phase:
            self.ndb.last_phase = current_phase
            self._broadcast_transition(current_phase)

    def _broadcast_transition(self, phase):
        """Send the transition message to all connected player characters."""
        msg = _TRANSITION_MESSAGES.get(phase)
        if not msg:
            return

        for char in ObjectDB.objects.filter(
            db_typeclass_path__contains="Character"
        ):
            if char.has_account and char.sessions.count():
                char.msg(msg)
