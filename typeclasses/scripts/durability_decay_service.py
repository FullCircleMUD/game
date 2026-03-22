"""
DurabilityDecayService — time-based wear on all equipped items.

Ticks once per game day (3600 real seconds at TIME_FACTOR=24).
For every IC character, reduces durability by 1 on each equipped item.

No offline catch-up — if you're not IC, your gear doesn't decay.
Combat wear (1 per hit/parry) is additive on top of this.
"""

from datetime import datetime

from evennia import DefaultScript, ObjectDB
from evennia.utils.gametime import gametime
from evennia.utils.utils import delay


def get_game_day_number():
    """
    Return the absolute game day number (monotonically increasing).

    Uses Evennia's gametime to derive an absolute day count that never
    wraps or resets.
    """
    game_timestamp = gametime(absolute=True)
    dt = datetime.fromtimestamp(game_timestamp)
    day_of_year = dt.timetuple().tm_yday % 360
    return dt.year * 360 + day_of_year


class DurabilityDecayService(DefaultScript):
    """
    Global persistent script — once per game day, apply 1 durability
    loss to every equipped item on every IC character.
    """

    def at_script_creation(self):
        self.key = "durability_decay_service"
        self.desc = "Applies time-based durability decay to equipped items"
        self.interval = 3600  # 1 game day = 1 real hour
        self.persistent = True
        self.start_delay = True
        self.repeats = 0

    def at_start(self, **kwargs):
        self.ndb.last_game_day = get_game_day_number()

    def at_repeat(self):
        current_day = get_game_day_number()
        if current_day <= self.ndb.last_game_day:
            return
        self.ndb.last_game_day = current_day

        # Gather IC characters, then stagger processing so we don't
        # block the reactor if the player count is large.
        ic_chars = [
            char
            for char in ObjectDB.objects.filter(
                db_typeclass_path__contains="Character"
            )
            if char.has_account and char.sessions.count()
        ]

        for i, char in enumerate(ic_chars):
            delay(i * 0.1, self._decay_equipped, char)

    def _decay_equipped(self, char):
        if not hasattr(char, "get_all_worn"):
            return
        equipped = char.get_all_worn()
        seen = set()
        for item in equipped.values():
            if item is None or item.id in seen:
                continue
            seen.add(item.id)
            if getattr(item, "max_durability", 0) > 0:
                item.reduce_durability(1)
