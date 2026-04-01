"""
Superuser command: trigger an NFT saturation snapshot out of cycle.

The saturation snapshot normally runs once per day. This command
forces an immediate snapshot so the knowledge spawn system has
data to work with on a fresh server.
"""

from evennia import Command


class CmdRunSaturation(Command):
    """
    Force an NFT saturation snapshot now.

    Usage:
        run_saturation

    Triggers the daily saturation snapshot immediately. This gives
    the knowledge spawn system (spell scrolls, recipe scrolls) the
    player data it needs to calculate drop rates. On a fresh server
    this must be run at least once before knowledge items will spawn.
    """

    key = "run_saturation"
    locks = "cmd:id(1)"
    help_category = "Economy"

    def func(self):
        from blockchain.xrpl.services.nft_saturation import NFTSaturationService

        self.msg("|yRunning saturation snapshot...|n")
        NFTSaturationService.take_daily_snapshot()
        self.msg("|gSaturation snapshot complete.|n")

        from blockchain.xrpl.models import SaturationSnapshot
        days = SaturationSnapshot.objects.values("day").distinct().count()
        rows = SaturationSnapshot.objects.count()
        self.msg(f"Snapshot data: {rows} items tracked across {days} day(s).")
