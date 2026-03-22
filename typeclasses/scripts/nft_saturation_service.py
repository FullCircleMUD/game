"""
NFTSaturationScript — global script that takes daily NFT saturation snapshots.

Ticks every 24 hours. Delegates to NFTSaturationService.take_daily_snapshot()
which collects active player counts, knowledge saturation (spells/recipes),
and NFT circulation data for the loot selection algorithm.
"""

from evennia import DefaultScript


# How often (real seconds) the saturation service runs.
TICK_INTERVAL_SECONDS = 86400  # 24 hours


class NFTSaturationScript(DefaultScript):
    """
    Global persistent script for daily NFT saturation snapshots.

    Created once via at_server_startstop._ensure_global_scripts().
    """

    def at_script_creation(self):
        self.key = "nft_saturation_service"
        self.desc = "Daily NFT saturation snapshot for spawn algorithm"
        self.interval = TICK_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = True
        self.repeats = 0  # repeat forever

    def at_repeat(self):
        """Take daily saturation snapshot."""
        from blockchain.xrpl.services.nft_saturation import NFTSaturationService

        NFTSaturationService.take_daily_snapshot()
