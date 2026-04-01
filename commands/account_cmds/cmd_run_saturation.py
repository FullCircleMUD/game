"""
Superuser command: trigger an NFT saturation snapshot out of cycle.

The saturation snapshot normally runs hourly. This command forces an
immediate snapshot so the knowledge spawn system has data to work with
on a fresh server.
"""

from evennia import Command
from twisted.internet import threads


class CmdRunSaturation(Command):
    """
    Force an NFT saturation snapshot now.

    Usage:
        run_saturation

    Triggers the hourly saturation snapshot immediately. This gives
    the knowledge spawn system (spell scrolls, recipe scrolls) the
    player data it needs to calculate spawn budgets. On a fresh server
    this must be run at least once before knowledge items will spawn.
    Runs in a background thread so the game stays responsive.
    """

    key = "run_saturation"
    locks = "cmd:id(1)"
    help_category = "Economy"

    def func(self):
        self.msg("|yRunning saturation snapshot...|n")

        def _run():
            from blockchain.xrpl.services.nft_saturation import NFTSaturationService
            NFTSaturationService.take_daily_snapshot()
            from blockchain.xrpl.models import SaturationSnapshot
            days = SaturationSnapshot.objects.values("day").distinct().count()
            rows = SaturationSnapshot.objects.count()
            return days, rows

        def _done(result):
            days, rows = result
            self.msg("|gSaturation snapshot complete.|n")
            self.msg(f"Snapshot data: {rows} items tracked across {days} day(s).")

        d = threads.deferToThread(_run)
        d.addCallback(_done)
        d.addErrback(
            lambda f: self.msg(f"|rSaturation snapshot failed: {f.getErrorMessage()}|n")
        )
