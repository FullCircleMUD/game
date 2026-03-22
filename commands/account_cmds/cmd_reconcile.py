"""
Superuser command to reconcile on-chain vault balances with game state.

Compares what the vault wallet actually holds on-chain against what
the game database thinks it holds (RESERVE rows). Flags discrepancies.

Usage (OOC, superuser only):
    reconcile    — compare on-chain vs game-state for all currencies
"""

from evennia import Command
from twisted.internet import threads


class CmdReconcile(Command):
    """
    Compare vault on-chain balances against game database totals.

    Read-only check — no changes made. For each currency shows:
      On-Chain    — actual vault balance on XRPL ledger
      Reserve     — game DB reserve (unallocated)
      Distributed — CHARACTER + ACCOUNT + SPAWNED (in-play)
      Sink        — consumed assets awaiting reallocation
      Delta       — On-Chain - (Reserve + Distributed + Sink)

    Delta should be zero. Positive = vault has uncounted assets
    (recent minting or AMM liquidity change). Negative = accounting
    bug (game DB thinks more exists than vault holds).

    Usage:
        reconcile
        recon
    """

    key = "reconcile"
    aliases = ["recon"]
    locks = "cmd:id(1) and is_ooc()"
    help_category = "Economy"

    def func(self):
        caller = self.caller
        caller.msg("|c--- XRPL Reconciliation ---|n")
        caller.msg("Querying vault on-chain balances...")

        d = threads.deferToThread(_run_reconcile)
        d.addCallback(lambda rows: _on_reconcile_complete(caller, rows))
        d.addErrback(lambda f: _on_reconcile_error(caller, f))


def _run_reconcile():
    """Worker thread — query chain and compare."""
    from blockchain.xrpl.services.chain_sync import reconcile_fungibles
    return reconcile_fungibles()


def _on_reconcile_complete(caller, rows):
    """Reactor thread — display reconciliation results."""
    if not caller.sessions.count():
        return

    if not rows:
        caller.msg("No currencies found.")
        caller.msg("|c--- Reconciliation Complete ---|n")
        return

    # Header
    caller.msg(
        f"\n {'Currency':<14s} {'On-Chain':>12s} {'Reserve':>12s} "
        f"{'Distrib':>12s} {'Sink':>12s} {'Delta':>12s}"
    )
    caller.msg(f" {'-' * 14} {'-' * 12} {'-' * 12} {'-' * 12} {'-' * 12} {'-' * 12}")

    warnings = 0
    for row in rows:
        name = row["name"]
        on_chain = row["on_chain"]
        reserve = row["game_reserve"]
        distributed = row["game_distributed"]
        sink = row["game_sink"]
        delta = row["delta"]

        # Colour the delta — green if zero, red if non-zero
        if delta > 0:
            delta_str = f"|g+{delta:.3f}|n"
        elif delta < 0:
            delta_str = f"|r{delta:.3f}|n"
            warnings += 1
        else:
            delta_str = f"{delta:.3f}"

        caller.msg(
            f" {name:<14s} {on_chain:>12.3f} {reserve:>12.3f} "
            f"{distributed:>12.3f} {sink:>12.3f} {delta_str:>12s}"
        )

    caller.msg("")
    caller.msg(
        " Delta = On-Chain - (Reserve + Distributed + Sink). "
        "Should be 0."
    )
    caller.msg(
        " |gPositive|n = uncounted vault assets (minting, AMM liquidity). "
        "|rNegative|n = accounting bug."
    )

    if warnings:
        caller.msg(f"\n |r{warnings} currency(s) show negative delta — investigate.|n")
    else:
        caller.msg("\n |gAll currencies OK — deltas are zero or positive.|n")

    caller.msg("|c--- Reconciliation Complete ---|n")


def _on_reconcile_error(caller, failure):
    """Reactor thread — reconciliation failed."""
    if caller.sessions.count():
        caller.msg(f"|r--- Reconciliation Error: {failure.getErrorMessage()} ---|n")
