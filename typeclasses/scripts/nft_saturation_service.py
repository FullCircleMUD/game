"""
NFTSaturationScript — global script that takes hourly NFT saturation snapshots.

Ticks every hour (aligned with the spawn cycle). Delegates to
NFTSaturationService.take_snapshot() which collects active player
counts, knowledge saturation (spells/recipes), and NFT circulation data
for the knowledge spawn calculator.

Hourly snapshots ensure the knowledge spawn budget reflects the current
saturation gap — a scroll spawned in hour 1 is seen by hour 2, preventing
over-spawning for small gaps (e.g. 1 new GM evocation player).
"""

from evennia import DefaultScript
from twisted.internet import threads


# How often (real seconds) the saturation service runs.
# Runs second in the hourly pipeline: telemetry → saturation → spawn.
# All three pipeline scripts use the same 3600s interval. The 60-second
# offset behind telemetry is established once at cold boot by staggering
# the script creation moments — see at_server_startstop.py
# _ensure_pipeline_scripts(). Once created the offset is preserved
# indefinitely, with zero drift.
TICK_INTERVAL_SECONDS = 3600  # 1 hour


class NFTSaturationScript(DefaultScript):
    """
    Global persistent script for hourly NFT saturation snapshots.

    Created once via at_server_startstop._ensure_global_scripts().
    """

    def at_script_creation(self):
        self.key = "nft_saturation_service"
        self.desc = "Hourly NFT saturation snapshot for spawn algorithm"
        self.interval = TICK_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = True
        self.repeats = 0  # repeat forever

    def at_repeat(self):
        """Take saturation snapshot in a background thread."""
        from blockchain.xrpl.services.nft_saturation import NFTSaturationService

        threads.deferToThread(NFTSaturationService.take_snapshot)
