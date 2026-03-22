"""
Superuser command to check AMM pool states from in-game.

Queries all non-gold currencies for AMM pools on the XRPL and displays
reserve balances and trading fees. Read-only — no trades executed.

Usage (OOC, superuser only):
    amm_check           — show all detected AMM pools
    amm_check wheat     — show only the wheat pool
"""

from decimal import Decimal

from evennia import Command
from twisted.internet import threads


class CmdAMMCheck(Command):
    """
    Check AMM pool states on the XRPL.

    Queries the ledger for all active AMM pools and displays their
    reserve balances and trading fees. No trades are executed.

    Usage:
        amm_check           - show all pools
        amm_check <resource> - show a specific pool
    """

    key = "amm_check"
    aliases = ["ammcheck"]
    locks = "cmd:id(1) and is_ooc()"
    help_category = "Economy"

    def func(self):
        caller = self.caller
        resource_filter = self.args.strip().lower() or None

        caller.msg("|c--- AMM Pool Status ---|n")
        caller.msg("Querying AMM pools...")

        d = threads.deferToThread(_query_pools, resource_filter)
        d.addCallback(lambda pools: _on_pools_complete(caller, pools))
        d.addErrback(lambda f: _on_pools_error(caller, f))


def _query_pools(resource_filter):
    """Worker thread — query AMM pool info for all non-gold currencies."""
    from django.conf import settings

    from blockchain.xrpl.models import CurrencyType
    from blockchain.xrpl.xrpl_amm import get_amm_info

    gold = settings.XRPL_GOLD_CURRENCY_CODE
    currencies = CurrencyType.objects.using("xrpl").filter(is_gold=False)
    pools = []

    for ct in currencies:
        if resource_filter and ct.name.lower() != resource_filter:
            continue

        try:
            info = get_amm_info(gold, ct.currency_code)
        except Exception:
            continue

        if info is None:
            continue

        r1 = info["reserve_1"]
        r2 = info["reserve_2"]
        if r1["currency"] == gold:
            gold_res, resource_res = r1["value"], r2["value"]
        else:
            gold_res, resource_res = r2["value"], r1["value"]

        fee_pct = Decimal(info["trading_fee"]) / Decimal(1000)

        pools.append({
            "name": ct.name,
            "currency_code": ct.currency_code,
            "resource_id": ct.resource_id,
            "gold_reserve": gold_res,
            "resource_reserve": resource_res,
            "fee_pct": fee_pct,
        })

    return pools


def _on_pools_complete(caller, pools):
    """Reactor thread — display pool states."""
    if not caller.sessions.count():
        return

    if not pools:
        caller.msg("No AMM pools detected.")
        caller.msg("|c--- AMM Check Complete ---|n")
        return

    for pool in pools:
        caller.msg(
            f"\n |w{pool['name']}|n ({pool['currency_code']}, "
            f"id={pool['resource_id']})"
        )
        caller.msg(
            f"   Gold reserve:     {pool['gold_reserve']}"
        )
        caller.msg(
            f"   Resource reserve: {pool['resource_reserve']}"
        )
        caller.msg(
            f"   Trading fee:      {pool['fee_pct']}%"
        )

    caller.msg("")
    caller.msg("|c--- AMM Check Complete ---|n")


def _on_pools_error(caller, failure):
    """Reactor thread — query failed."""
    if caller.sessions.count():
        caller.msg(f"|r--- AMM Check Error: {failure.getErrorMessage()} ---|n")
