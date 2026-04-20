"""
Superuser command to view economy telemetry snapshots.

Displays the latest hourly economy snapshot including player activity,
gold flows, AMM trading, and per-resource breakdowns.

Usage (OOC, superuser only):
    economy             — show latest economy snapshot
    economy <resource>  — show detailed history for a resource
"""

from evennia import Command


class CmdEconomy(Command):
    """
    View economy telemetry snapshots.

    Displays the latest hourly economy snapshot including player
    activity, gold flows, AMM trading, and per-resource detail.

    Usage:
        economy             - latest global snapshot + top resources
        economy <resource>  - detailed history for one resource
    """

    key = "economy"
    aliases = []
    locks = "cmd:id(1) and is_ooc()"
    help_category = "Economy"

    def func(self):
        resource_filter = self.args.strip().lower() or None

        if resource_filter:
            _show_resource_detail(self.caller, resource_filter)
        else:
            _show_latest_snapshot(self.caller)


def _show_latest_snapshot(caller):
    """Display the most recent EconomySnapshot + top resources."""
    from blockchain.xrpl.models import EconomySnapshot, ResourceSnapshot

    snap = EconomySnapshot.objects.first()
    if not snap:
        caller.msg("|yNo economy snapshots yet. Wait for the hourly aggregator.|n")
        return

    caller.msg(f"|c=== Economy Snapshot ({snap.hour:%Y-%m-%d %H:%M} UTC) ===|n")

    # Player activity
    caller.msg(
        f"|wPlayers:|n {snap.players_online} online | "
        f"{snap.unique_players_1h} (1h) | "
        f"{snap.unique_players_24h} (24h) | "
        f"{snap.unique_players_7d} (7d)"
    )

    # Gold
    caller.msg(
        f"|wGold:|n {_fmt(snap.gold_circulation)} circulating | "
        f"{_fmt(snap.gold_reserve)} reserve | "
        f"{_fmt(snap.gold_sinks_1h)} sinks/hr | "
        f"{_fmt(snap.gold_spawned_1h)} spawned/hr"
    )

    # AMM
    caller.msg(
        f"|wAMM:|n {snap.amm_trades_1h} trades/hr | "
        f"{_fmt(snap.amm_volume_gold_1h)} gold volume"
    )

    # Chain
    caller.msg(
        f"|wChain:|n {snap.imports_1h} imports | {snap.exports_1h} exports"
    )

    # Per-resource summary (top resources by total in CHARACTER + ACCOUNT)
    resources = (
        ResourceSnapshot.objects.filter(hour=snap.hour)
        .exclude(currency_code__startswith="FCMGold")
        .order_by("-in_character")[:12]
    )

    if resources:
        caller.msg("\n|c--- Resources (top by player holdings) ---|n")
        caller.msg(
            f"  {'Resource':<16} {'Char':>8} {'Bank':>8} "
            f"{'Buy':>6} {'Sell':>6} "
            f"{'Prod':>6} {'Cons':>6} {'Trade':>6}"
        )
        for r in resources:
            name = r.currency_code.replace("FCM", "")
            buy = _fmt(r.amm_buy_price) if r.amm_buy_price else "-"
            sell = _fmt(r.amm_sell_price) if r.amm_sell_price else "-"
            caller.msg(
                f"  {name:<16} {_fmt(r.in_character):>8} {_fmt(r.in_account):>8} "
                f"{buy:>6} {sell:>6} "
                f"{_fmt(r.produced_1h):>6} {_fmt(r.consumed_1h):>6} "
                f"{_fmt(r.traded_1h):>6}"
            )


def _show_resource_detail(caller, resource_filter):
    """Show recent history for a single resource."""
    from blockchain.xrpl.models import ResourceSnapshot

    # Find matching currency code
    matches = (
        ResourceSnapshot.objects.filter(
            currency_code__icontains=resource_filter,
        )
        .values_list("currency_code", flat=True)
        .distinct()[:5]
    )
    matches = list(matches)

    if not matches:
        caller.msg(f"|yNo snapshots found matching '{resource_filter}'.|n")
        return

    if len(matches) > 1:
        caller.msg(
            f"|yMultiple matches: {', '.join(matches)}. Be more specific.|n"
        )
        return

    code = matches[0]
    snapshots = ResourceSnapshot.objects.filter(currency_code=code)[:24]

    if not snapshots:
        caller.msg(f"|yNo snapshots for {code}.|n")
        return

    name = code.replace("FCM", "")
    caller.msg(f"|c=== {name} — Last {len(snapshots)} Hours ===|n")
    caller.msg(
        f"  {'Hour':<14} {'Char':>8} {'Bank':>8} {'Spawn':>8} "
        f"{'Reserve':>8} {'Buy':>6} {'Sell':>6} "
        f"{'Prod':>6} {'Cons':>6}"
    )

    for s in snapshots:
        buy = _fmt(s.amm_buy_price) if s.amm_buy_price else "-"
        sell = _fmt(s.amm_sell_price) if s.amm_sell_price else "-"
        caller.msg(
            f"  {s.hour:%m-%d %H:%M}  {_fmt(s.in_character):>8} "
            f"{_fmt(s.in_account):>8} {_fmt(s.in_spawned):>8} "
            f"{_fmt(s.in_reserve):>8} {buy:>6} {sell:>6} "
            f"{_fmt(s.produced_1h):>6} {_fmt(s.consumed_1h):>6}"
        )


def _fmt(value):
    """Format a Decimal for display — strip trailing zeros."""
    if value is None:
        return "-"
    # Convert to int if it's a whole number
    if value == int(value):
        return f"{int(value):,}"
    return f"{value:,.2f}"
