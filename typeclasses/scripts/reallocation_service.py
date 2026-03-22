"""
ReallocationServiceScript — global script that drains SINK → RESERVE daily.

Ticks every 24 hours and moves all accumulated SINK balances back to
RESERVE, making consumed assets available for re-spawning.
"""

from evennia import DefaultScript


# How often (real seconds) the reallocation runs.
TICK_INTERVAL_SECONDS = 86400  # 24 hours


class ReallocationServiceScript(DefaultScript):
    """
    Global persistent script that periodically drains SINK → RESERVE.

    Created once via at_server_startstop._ensure_global_scripts().
    """

    def at_script_creation(self):
        self.key = "reallocation_service"
        self.desc = "Drains SINK back to RESERVE daily"
        self.interval = TICK_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = True
        self.repeats = 0  # repeat forever

    def at_repeat(self):
        """Drain SINK → RESERVE."""
        from blockchain.xrpl.services.reallocation import reallocate_sinks

        reallocate_sinks()
