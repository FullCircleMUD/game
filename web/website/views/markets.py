"""
Markets page — AMM prices and circulation from latest telemetry snapshot.

Three tabs:
  Resources  — fungible resources (wheat, iron ore, etc.) priced via FCMGold AMM pools
  Equipment  — NFT items with proxy token AMM pricing (training dagger, etc.)
  Tradeables — NFT items without AMM pricing (circulation data only)
"""

from django.views.generic import TemplateView

from blockchain.xrpl.models import (
    CurrencyType,
    EconomySnapshot,
    NFTGameState,
    NFTItemType,
    ResourceSnapshot,
)


class MarketsView(TemplateView):
    template_name = "website/markets.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Get the most recent snapshot hour
        latest = (
            ResourceSnapshot.objects.order_by("-hour")
            .values_list("hour", flat=True)
            .first()
        )

        # Build lookup sets for filtering snapshot rows
        # Resource currencies: have a resource_id (wheat, iron ore, etc.)
        resource_codes = set(
            CurrencyType.objects.filter(resource_id__isnull=False)
            .values_list("currency_code", flat=True)
        )
        # Proxy token currencies: linked to an NFTItemType via tracking_token
        proxy_item_types = {
            it.tracking_token: it.name
            for it in NFTItemType.objects.filter(tracking_token__isnull=False)
        }
        proxy_codes = set(proxy_item_types.keys())

        # currency_code → display name
        names = dict(CurrencyType.objects.values_list("currency_code", "name"))

        if latest:
            snapshots = ResourceSnapshot.objects.filter(hour=latest).order_by(
                "currency_code"
            )

            resources = []
            equipment = []

            for snap in snapshots:
                code = snap.currency_code

                if code in resource_codes:
                    # Resource tab — round for display (players see integer prices)
                    from math import ceil, floor
                    ct_name = names.get(code, code)
                    buy_display = int(ceil(float(snap.amm_buy_price))) if snap.amm_buy_price else None
                    sell_display = int(floor(float(snap.amm_sell_price))) if snap.amm_sell_price else None
                    resources.append(
                        {
                            "name": ct_name,
                            "buy_price": buy_display,
                            "sell_price": sell_display,
                            "spread": (
                                (buy_display - sell_display)
                                if buy_display and sell_display
                                else None
                            ),
                            "in_circulation": (
                                snap.in_character + snap.in_account + snap.in_spawned
                            ),
                            "traded_1h": snap.traded_1h,
                        }
                    )

                elif code in proxy_codes:
                    # Equipment tab — round for display
                    item_name = proxy_item_types.get(code, code)
                    eq_buy = int(ceil(float(snap.amm_buy_price))) if snap.amm_buy_price else None
                    eq_sell = int(floor(float(snap.amm_sell_price))) if snap.amm_sell_price else None
                    equipment.append(
                        {
                            "name": item_name,
                            "buy_price": eq_buy,
                            "sell_price": eq_sell,
                            "spread": (
                                (eq_buy - eq_sell)
                                if eq_buy and eq_sell
                                else None
                            ),
                            "in_circulation": (
                                snap.in_character + snap.in_account + snap.in_spawned
                            ),
                            "traded_1h": snap.traded_1h,
                        }
                    )

            ctx["resources"] = resources
            ctx["equipment"] = equipment
            ctx["snapshot_time"] = latest
        else:
            ctx["resources"] = []
            ctx["equipment"] = []
            ctx["snapshot_time"] = None

        # Tradeables tab — NFT item types WITHOUT proxy tokens (no AMM pricing)
        # Circulation count only, queried live from NFTGameState
        tradeable_types = (
            NFTItemType.objects.filter(tracking_token__isnull=True)
            .exclude(name__icontains="recipe")
            .exclude(name__icontains="scroll")
            .order_by("name")
        )

        # Single query: count NFTs in circulation grouped by item_type
        from django.db.models import Count

        circulation_counts = dict(
            NFTGameState.objects.filter(
                item_type__isnull=False,
                item_type__tracking_token__isnull=True,
            )
            .values_list("item_type__name")
            .annotate(count=Count("id"))
            .values_list("item_type__name", "count")
        )

        tradeables = []
        for it in tradeable_types:
            count = circulation_counts.get(it.name, 0)
            if count > 0:
                tradeables.append(
                    {
                        "name": it.name,
                        "in_circulation": count,
                    }
                )
        ctx["tradeables"] = tradeables

        # Gold headline from EconomySnapshot
        eco = (
            EconomySnapshot.objects.order_by("-hour")
            .values("gold_circulation", "gold_sinks_1h")
            .first()
        )
        if eco:
            ctx["gold_circulation"] = eco["gold_circulation"]
            ctx["gold_sinks_1h"] = eco["gold_sinks_1h"]

        return ctx
