"""
TelemetryAggregatorScript — global script that takes hourly economy snapshots.

Ticks every hour and delegates to TelemetryService.take_snapshot()
which aggregates player activity, resource circulation, velocity,
gold flows, and AMM prices into snapshot tables.
"""

from evennia import DefaultScript
from twisted.internet import threads


# How often (real seconds) the aggregator runs.
# Runs first in the hourly pipeline: telemetry → saturation → spawn.
# Staggered by 60s offsets (3600 / 3660 / 3720) so each service
# has fresh data from the previous one.
TICK_INTERVAL_SECONDS = 3600  # 1 hour (fires first)


class TelemetryAggregatorScript(DefaultScript):
    """
    Global persistent script that takes hourly economy snapshots.

    Created once via at_server_startstop._ensure_global_scripts().
    """

    def at_script_creation(self):
        self.key = "telemetry_aggregator_service"
        self.desc = "Takes hourly economy telemetry snapshots"
        self.interval = TICK_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = True
        self.repeats = 0  # repeat forever

    def at_repeat(self):
        """Take an economy snapshot in a background thread."""
        from blockchain.xrpl.services.telemetry import TelemetryService

        threads.deferToThread(TelemetryService.take_snapshot)
