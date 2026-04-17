"""
Superuser command to recalculate reserve balances from on-chain vault state.

Queries the vault wallet's trust line balances on XRPL and recalculates
RESERVE for each currency:

    RESERVE = on_chain - (SPAWNED + ACCOUNT + CHARACTER + SINK)

IMPORTANT: Run `reconcile` first to review deltas before syncing.
Expected deltas come from admin operations (minting new tokens,
adding/removing AMM liquidity). Unexpected deltas indicate a
potential accounting bug — investigate before syncing.

Usage (OOC, superuser only):
    sync_reserves
"""

from evennia import Command
from twisted.internet import threads


class CmdSyncReserves(Command):
    """
    Recalculate reserve balances from on-chain vault state.

    Queries the vault wallet's trust line balances on XRPL and
    recalculates RESERVE for each currency:

        RESERVE = on_chain - (SPAWNED + ACCOUNT + CHARACTER + SINK)

    IMPORTANT: Run `reconcile` first to review deltas before syncing.
    Expected deltas come from admin operations (minting new tokens,
    adding/removing AMM liquidity). Unexpected deltas indicate a
    potential accounting bug — investigate before syncing.

    Usage:
        sync_reserves
    """

    key = "sync_reserves"
    aliases = []
    locks = "cmd:id(1) and is_ooc()"
    help_category = "Economy"

    def func(self):
        caller = self.caller
        caller.msg("|c--- Sync Reserves ---|n")
        caller.msg("Querying vault on-chain balances...")

        d = threads.deferToThread(_run_sync_reserves)
        d.addCallback(lambda rows: _on_sync_complete(caller, rows))
        d.addErrback(lambda f: _on_sync_error(caller, f))


def _run_sync_reserves():
    """Worker thread — query chain and recalculate reserves."""
    from blockchain.xrpl.services.chain_sync import sync_reserves
    return sync_reserves()


def _on_sync_complete(caller, rows):
    """Reactor thread — display sync results."""
    if not caller.sessions.count():
        return

    if not rows:
        caller.msg("No currencies found.")
        caller.msg("|c--- Sync Complete ---|n")
        return

    caller.msg(
        f"\n {'Currency':<14s} {'Old Reserve':>14s} "
        f"{'New Reserve':>14s} {'Delta':>14s}"
    )
    caller.msg(f" {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 14}")

    changed = 0
    for row in rows:
        old = row["old_reserve"]
        new = row["new_reserve"]
        delta = row["delta"]

        if delta > 0:
            delta_str = f"|g+{delta:.3f}|n"
            changed += 1
        elif delta < 0:
            delta_str = f"|r{delta:.3f}|n"
            changed += 1
        else:
            delta_str = f"{delta:.3f}"

        caller.msg(
            f" {row['currency_code']:<14s} {old:>14.3f} "
            f"{new:>14.3f} {delta_str:>14s}"
        )

    caller.msg("")
    if changed:
        caller.msg(f" |y{changed} currency(s) updated.|n")
    else:
        caller.msg(" |gAll reserves already in sync — no changes.|n")

    caller.msg("|c--- Sync Complete ---|n")


def _on_sync_error(caller, failure):
    """Reactor thread — sync failed."""
    if caller.sessions.count():
        caller.msg(f"|r--- Sync Error: {failure.getErrorMessage()} ---|n")
