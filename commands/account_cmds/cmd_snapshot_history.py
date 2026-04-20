"""
Superuser command: view snapshot history and detail.

With no arguments, shows a summary of recent economy, saturation,
and resource snapshots. With a type argument, shows full detail
of a specific snapshot.

Usage:
    snapshot_history                — summary of last 3 per type
    snapshot_history economy [N]   — full detail of Nth most recent economy snapshot
    snapshot_history saturation [N] — all rows for Nth most recent saturation hour
    snapshot_history resources [N] — all rows for Nth most recent resource hour
"""

from evennia import Command

from blockchain.xrpl.models import (
    EconomySnapshot,
    ResourceSnapshot,
    SaturationSnapshot,
)


def _resolve_type(name):
    """Resolve a snapshot type from partial input."""
    name = name.lower().strip()
    for full in ("economy", "saturation", "resources"):
        if full.startswith(name) or name in full:
            return full
    return None


class CmdSnapshotHistory(Command):
    """
    View snapshot history and detail.

    Usage:
        snapshot_history                 — summary of last 3 per type
        snapshot_history economy [N]     — Nth most recent economy snapshot
        snapshot_history saturation [N]  — Nth most recent saturation hour
        snapshot_history resources [N]   — Nth most recent resource hour

    N defaults to 1 (most recent). Supports partial names:
        snapshot_history eco
        snapshot_history sat 2
        snapshot_history res
    """

    key = "snapshot_history"
    aliases = []
    locks = "cmd:id(1)"
    help_category = "Economy"

    def func(self):
        args = self.args.strip().lower().split()

        if not args:
            self._show_summary()
        else:
            type_name = _resolve_type(args[0])
            if not type_name:
                self.msg(f"|rUnknown snapshot type: {args[0]}|n")
                self.msg("Types: economy, saturation, resources")
                return

            # Parse optional index (1-based, default 1)
            index = 1
            if len(args) > 1:
                try:
                    index = int(args[1])
                    if index < 1:
                        index = 1
                except ValueError:
                    self.msg(f"|rInvalid index: {args[1]}|n")
                    return

            if type_name == "economy":
                self._show_economy_detail(index)
            elif type_name == "saturation":
                self._show_saturation_detail(index)
            elif type_name == "resources":
                self._show_resources_detail(index)

    # ── Summary view ──────────────────────────────────────────────

    def _show_summary(self):
        self.msg("|w=== Snapshot History ===|n\n")

        # Economy snapshots
        economy = EconomySnapshot.objects.order_by("-hour")[:3]
        if economy:
            self.msg("|wEconomy Snapshots|n (hourly):")
            for snap in economy:
                self.msg(
                    f"  {snap.hour:%Y-%m-%d %H:%M} UTC  |  "
                    f"{snap.players_online} online  |  "
                    f"24h: {snap.unique_players_24h}  |  "
                    f"circ: {snap.gold_circulation:,.0f}g"
                )
        else:
            self.msg("|wEconomy Snapshots|n: |yNone yet|n")

        self.msg("")

        # Saturation snapshots — group by hour
        sat_hours = (
            SaturationSnapshot.objects
            .values_list("hour", flat=True)
            .distinct()
            .order_by("-hour")[:3]
        )
        if sat_hours:
            self.msg("|wSaturation Snapshots|n (hourly):")
            for hour in sat_hours:
                rows = SaturationSnapshot.objects.filter(hour=hour)
                active = rows.first().active_players_7d if rows.exists() else 0
                spells = rows.filter(category="spell").count()
                recipes = rows.filter(category="recipe").count()
                items = rows.filter(category="item").count()
                self.msg(
                    f"  {hour:%Y-%m-%d %H:%M} UTC  |  "
                    f"{active} active 7d  |  "
                    f"{spells} spells  |  "
                    f"{recipes} recipes  |  "
                    f"{items} items"
                )
        else:
            self.msg("|wSaturation Snapshots|n: |yNone yet|n")

        self.msg("")

        # Resource snapshots — just a count summary
        res_hours = (
            ResourceSnapshot.objects
            .values_list("hour", flat=True)
            .distinct()
            .order_by("-hour")[:1]
        )
        if res_hours:
            latest = res_hours[0]
            count = ResourceSnapshot.objects.filter(hour=latest).count()
            self.msg(
                f"|wResource Snapshots|n: "
                f"{count} resources tracked "
                f"(latest: {latest:%Y-%m-%d %H:%M} UTC)"
            )
        else:
            self.msg("|wResource Snapshots|n: |yNone yet|n")

    # ── Economy detail ────────────────────────────────────────────

    def _show_economy_detail(self, index):
        snaps = EconomySnapshot.objects.order_by("-hour")
        count = snaps.count()
        if not count:
            self.msg("No economy snapshots found.")
            return
        if index > count:
            self.msg(f"Only {count} economy snapshot(s) available.")
            return

        snap = snaps[index - 1]
        self.msg(f"|w=== Economy Snapshot #{index} ===|n")
        self.msg(f"|wTimestamp:|n       {snap.hour:%Y-%m-%d %H:%M} UTC")
        self.msg("")
        self.msg(f"|wPlayers Online:|n  {snap.players_online}")
        self.msg(f"|wUnique 1h:|n       {snap.unique_players_1h}")
        self.msg(f"|wUnique 24h:|n      {snap.unique_players_24h}")
        self.msg(f"|wUnique 7d:|n       {snap.unique_players_7d}")
        self.msg("")
        self.msg(f"|wGold Circulation:|n {snap.gold_circulation:,.0f}")
        self.msg(f"|wGold Reserve:|n     {snap.gold_reserve:,.0f}")
        self.msg(f"|wGold Sinks (1h):|n  {snap.gold_sinks_1h:,.0f}")
        self.msg(f"|wGold Spawned (1h):|n {snap.gold_spawned_1h:,.0f}")
        self.msg("")
        self.msg(f"|wAMM Trades (1h):|n  {snap.amm_trades_1h}")
        self.msg(f"|wAMM Volume (1h):|n  {snap.amm_volume_gold_1h:,.0f}g")
        self.msg(f"|wImports (1h):|n     {snap.imports_1h}")
        self.msg(f"|wExports (1h):|n     {snap.exports_1h}")

    # ── Saturation detail ─────────────────────────────────────────

    def _show_saturation_detail(self, index):
        hours = (
            SaturationSnapshot.objects
            .values_list("hour", flat=True)
            .distinct()
            .order_by("-hour")
        )
        count = hours.count()
        if not count:
            self.msg("No saturation snapshots found.")
            return
        if index > count:
            self.msg(f"Only {count} saturation hour(s) available.")
            return

        hour = hours[index - 1]
        rows = SaturationSnapshot.objects.filter(hour=hour).order_by(
            "category", "item_key"
        )
        active = rows.first().active_players_7d if rows.exists() else 0

        self.msg(f"|w=== Saturation Snapshot #{index} — {hour:%Y-%m-%d %H:%M} UTC ===|n")
        self.msg(f"|wActive Players (7d):|n {active}\n")

        current_cat = None
        for row in rows:
            if row.category != current_cat:
                current_cat = row.category
                self.msg(f"|w--- {current_cat.title()}s ---|n")

            sat_pct = f"{row.saturation * 100:.1f}%" if row.saturation else "n/a"

            if current_cat in ("spell", "recipe"):
                self.msg(
                    f"  {row.item_key}: "
                    f"sat={sat_pct}  "
                    f"known={row.known_by}/{row.eligible_players}  "
                    f"unlearned={row.unlearned_copies}  "
                    f"spawn: {row.spawn_placed}/{row.spawn_budget}"
                )
            else:
                self.msg(
                    f"  {row.item_key}: "
                    f"circ={row.in_circulation}  "
                    f"sat={sat_pct}  "
                    f"spawn: {row.spawn_placed}/{row.spawn_budget}"
                )

    # ── Resource detail ───────────────────────────────────────────

    def _show_resources_detail(self, index):
        hours = (
            ResourceSnapshot.objects
            .values_list("hour", flat=True)
            .distinct()
            .order_by("-hour")
        )
        count = hours.count()
        if not count:
            self.msg("No resource snapshots found.")
            return
        if index > count:
            self.msg(f"Only {count} resource hour(s) available.")
            return

        hour = hours[index - 1]
        rows = ResourceSnapshot.objects.filter(hour=hour).order_by(
            "currency_code"
        )

        self.msg(f"|w=== Resource Snapshot #{index} — {hour:%Y-%m-%d %H:%M} UTC ===|n\n")

        for row in rows:
            buy = f"{row.amm_buy_price:.1f}g" if row.amm_buy_price else "n/a"
            sell = f"{row.amm_sell_price:.1f}g" if row.amm_sell_price else "n/a"

            self.msg(f"|w{row.currency_code}|n")
            self.msg(
                f"  char={row.in_character:,.0f}  "
                f"bank={row.in_account:,.0f}  "
                f"spawned={row.in_spawned:,.0f}  "
                f"reserve={row.in_reserve:,.0f}  "
                f"sink={row.in_sink:,.0f}"
            )
            self.msg(
                f"  produced={row.produced_1h:,.0f}  "
                f"consumed={row.consumed_1h:,.0f}  "
                f"traded={row.traded_1h:,.0f}  "
                f"buy={buy}  sell={sell}"
            )
            self.msg(
                f"  spawn: budget={row.spawn_budget}  "
                f"placed={row.spawn_placed}  "
                f"dropped={row.spawn_dropped}  "
                f"quest_debt={row.spawn_quest_debt}"
            )
            self.msg("")
