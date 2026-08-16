"""
NFTSaturationScript — global script that takes hourly NFT saturation snapshots.

Ticks every minute and fires NFTSaturationService.take_snapshot() once per
hour at the designated wall-clock slot (HH:05). The 5-minute offset behind
telemetry gives telemetry runtime headroom while remaining predictable.

The hour bucket is recorded on self.db.last_run_hour to prevent double-fire
within a single hour.
"""

from datetime import datetime, timezone

from evennia import DefaultScript
from evennia.utils import logger
from twisted.internet import threads

from typeclasses.scripts.heartbeat_script import HeartbeatMixin


TICK_INTERVAL_SECONDS = 60
SLOT_MINUTE = 5  # fires at HH:05


class NFTSaturationScript(HeartbeatMixin, DefaultScript):
    """
    Global persistent script for hourly NFT saturation snapshots at HH:05.

    Global script registration lives in server/conf/at_server_startstop.py.
    One ScriptDB row is shared cluster-wide, but each Server process
    attaches its own ticker — under a sharded deployment the script runs
    once per process, not once overall.
    """

    def at_script_creation(self):
        self.key = "nft_saturation_service"
        self.desc = "Hourly NFT saturation snapshot at HH:05 for spawn algorithm"
        self.interval = TICK_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = False
        self.repeats = 0

    def at_repeat(self):
        self.record_repeat()
        try:
            now = datetime.now(timezone.utc)
            if now.minute != SLOT_MINUTE:
                return
            hour_bucket = now.replace(minute=0, second=0, microsecond=0)
            if self.db.last_run_hour == hour_bucket:
                return
            self.db.last_run_hour = hour_bucket

            from blockchain.xrpl.services.nft_saturation import NFTSaturationService

            threads.deferToThread(NFTSaturationService.take_snapshot)

            self.record_work()
        except Exception:
            logger.log_trace("nft_saturation_service: tick failed")
