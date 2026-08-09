"""
UnifiedSpawnScript — global script that drives the unified spawn system.

Ticks every minute and fires SpawnService.run_hourly_cycle() once per hour
at the designated wall-clock slot (HH:10). The 10-minute offset behind
telemetry (and 5 min behind saturation) lets both predecessor snapshots
finish before spawn reads their data.

The hour bucket is recorded on self.db.last_run_hour to prevent double-fire
within a single hour.
"""

from datetime import datetime, timezone

from evennia import DefaultScript
from evennia.utils import logger
from twisted.internet import threads

from typeclasses.scripts.heartbeat_script import HeartbeatMixin


TICK_INTERVAL_SECONDS = 60
SLOT_MINUTE = 10  # fires at HH:10


class UnifiedSpawnScript(HeartbeatMixin, DefaultScript):
    """
    Global persistent script for the unified item spawn system.

    Registered for router and monolith roles only — see the _SCRIPTS table
    in server/conf/at_server_startstop.py. Deciding how much the world needs
    and which targets receive it requires seeing every shard's rows, which
    only the unscoped router does.

    Shards run no spawn script at all. They receive placements as bus
    messages and carry them out through the message handler, which is a
    Twisted LoopingCall started in at_server_start() rather than a script —
    one less thing to check is running.
    """

    def at_script_creation(self):
        self.key = "unified_spawn_service"
        self.desc = "Unified hourly spawn system at HH:10 for resources, gold, and NFTs"
        self.interval = TICK_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = False
        self.repeats = 0

    def at_start(self, **kwargs):
        """Register the SpawnService singleton when the script starts."""
        from blockchain.xrpl.services.spawn.config import SPAWN_CONFIG
        from blockchain.xrpl.services.spawn.service import SpawnService, set_spawn_service

        self._service = SpawnService(SPAWN_CONFIG)
        set_spawn_service(self._service)

    def at_repeat(self):
        self.record_repeat()
        try:
            now = datetime.now(timezone.utc)
            if now.minute != SLOT_MINUTE:
                return
            hour_bucket = now.replace(minute=0, second=0, microsecond=0)
            if self.db.last_run_hour == hour_bucket:
                return
            if not hasattr(self, "_service"):
                return
            self.db.last_run_hour = hour_bucket

            threads.deferToThread(self._service.run_hourly_cycle)

            self.record_work()
        except Exception:
            logger.log_trace("unified_spawn_service: tick failed")
