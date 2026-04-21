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
from twisted.internet import threads


TICK_INTERVAL_SECONDS = 60
SLOT_MINUTE = 5  # fires at HH:05


class NFTSaturationScript(DefaultScript):
    """
    Global persistent script for hourly NFT saturation snapshots at HH:05.

    Created once via at_server_startstop._ensure_global_scripts().
    """

    def at_script_creation(self):
        self.key = "nft_saturation_service"
        self.desc = "Hourly NFT saturation snapshot at HH:05 for spawn algorithm"
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

        from blockchain.xrpl.services.nft_saturation import NFTSaturationService

        threads.deferToThread(NFTSaturationService.take_snapshot)
