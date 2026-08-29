"""
Superuser command: trigger an NFT saturation snapshot out of cycle.

The saturation snapshot normally runs hourly. This command forces an
immediate snapshot so the knowledge spawn system has data to work with
on a fresh server.
"""

from evennia import Command
from utils.db_threads import defer_to_db_thread


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
        from evennia_shards import ROLE_MONOLITH, ROLE_ROUTER, get_role

        role = get_role()
        if role not in (ROLE_MONOLITH, ROLE_ROUTER):
            self.msg("|rThis command can only be run OOC on the router.|n")
            return

        self.msg("|yRunning saturation snapshot...|n")

        def _run():
            from blockchain.xrpl.services.nft_saturation import NFTSaturationService
            NFTSaturationService.take_snapshot()
            from blockchain.xrpl.models import SaturationSnapshot
            hours = SaturationSnapshot.objects.values("hour").distinct().count()
            rows = SaturationSnapshot.objects.count()
            return hours, rows

        def _done(result):
            hours, rows = result
            self.msg("|gSaturation snapshot complete.|n")
            self.msg(f"Snapshot data: {rows} items tracked across {hours} hour(s).")

        d = defer_to_db_thread(_run)
        d.addCallback(_done)
        d.addErrback(
            lambda f: self.msg(f"|rSaturation snapshot failed: {f.getErrorMessage()}|n")
        )
