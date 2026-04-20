"""
TelemetryAggregatorScript — global script that takes hourly economy snapshots.

Ticks every minute and fires TelemetryService.take_snapshot() once per hour
at the designated wall-clock slot (HH:00). Wall-clock alignment makes the
pipeline reload-invariant: a process restart just re-arms the minute ticker,
and the next poll inside the slot minute fires the snapshot.

The hour bucket is recorded on self.db.last_run_hour to prevent double-fire
within a single hour (e.g. after a reload mid-slot).
"""

from datetime import datetime, timezone

from evennia import DefaultScript
from twisted.internet import threads


TICK_INTERVAL_SECONDS = 60
SLOT_MINUTE = 0  # fires at HH:00


class TelemetryAggregatorScript(DefaultScript):
    """
    Global persistent script that takes hourly economy snapshots at HH:00.

    Created once via at_server_startstop._ensure_global_scripts().
    """

    def at_script_creation(self):
        self.key = "telemetry_aggregator_service"
        self.desc = "Takes hourly economy telemetry snapshots at HH:00"
        self.interval = TICK_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = False
        self.repeats = 0

    def at_repeat(self):
        now = datetime.now(timezone.utc)
        if now.minute != SLOT_MINUTE:
            return
        hour_bucket = now.replace(minute=0, second=0, microsecond=0)
        if self.db.last_run_hour == hour_bucket:
            return
        self.db.last_run_hour = hour_bucket

        from blockchain.xrpl.services.telemetry import TelemetryService

        threads.deferToThread(TelemetryService.take_snapshot)
