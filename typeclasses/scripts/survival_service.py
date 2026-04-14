"""
SurvivalService — per-character survival upkeep dispatcher.

A single global Evennia script that ticks every SURVIVAL_TICK_INTERVAL seconds,
walks all puppeted characters, and decrements every survival meter on each
one. Currently the only meter is hunger; thirst lands in a follow-up PR and
will plug into the same loop body. Future meters (sleep, sanity, etc.) are
designed to live here too — the script is just a tick dispatcher with a
puppeted-only guard, nothing meter-specific in its plumbing.

Skips:
- Sessions with no puppeted character (logged in but not in-game)
- Superuser characters (exempt from survival decay during dev work)
- Characters without a `hunger_level` attribute (defensive)
"""

from evennia import DefaultScript, SESSION_HANDLER
from django.conf import settings
from enums.hunger_level import HungerLevel


class SurvivalService(DefaultScript):
    """
    Global timer that decrements every survival meter on every puppeted
    character once per tick. See module docstring for the design rationale.
    """

    def at_script_creation(self):
        self.key = "survival_service"
        self.desc = (
            "Per-character survival upkeep — ticks hunger (and future "
            "meters) on every puppeted character."
        )
        self.interval = settings.SURVIVAL_TICK_INTERVAL
        self.persistent = True
        self.start_delay = True  # wait interval before first run
        self.repeats = 0  # repeat forever

    def at_repeat(self):
        """Called every `interval` seconds."""
        for session in SESSION_HANDLER.get_sessions():
            char = session.get_puppet()
            if not char:
                continue

            # Superuser is exempt from all survival decay
            account = char.account
            if account and account.is_superuser:
                continue

            self._tick_hunger(char)

    @staticmethod
    def _tick_hunger(char):
        """Decrement one hunger stage, honouring the free-pass-on-FULL flag."""
        if not hasattr(char, "hunger_level"):
            return

        hunger_level = char.hunger_level
        if not isinstance(hunger_level, HungerLevel):
            return

        if hunger_level == HungerLevel.STARVING:
            return

        if hunger_level == HungerLevel.FULL and char.hunger_free_pass_tick:
            char.hunger_free_pass_tick = False
            return

        char.hunger_level = hunger_level.get_level(hunger_level.value - 1)
