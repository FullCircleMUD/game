"""
Markets page — AMM resource prices from latest telemetry snapshot.
"""

from django.views.generic import TemplateView

from blockchain.xrpl.models import CurrencyType, ResourceSnapshot


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

        if latest:
            # All resource snapshots for that hour
            snapshots = ResourceSnapshot.objects.filter(hour=latest).order_by(
                "currency_code"
            )

            # Build currency_code → name lookup
            names = dict(CurrencyType.objects.values_list("currency_code", "name"))

            resources = []
            for snap in snapshots:
                ct_name = names.get(snap.currency_code, snap.currency_code)
                if ct_name == "Gold":
                    continue
                resources.append(
                    {
                        "name": ct_name,
                        "buy_price": snap.amm_buy_price,
                        "sell_price": snap.amm_sell_price,
                        "spread": (
                            (snap.amm_buy_price - snap.amm_sell_price)
                            if snap.amm_buy_price and snap.amm_sell_price
                            else None
                        ),
                        "in_circulation": (
                            snap.in_character + snap.in_account + snap.in_spawned
                        ),
                        "traded_1h": snap.traded_1h,
                    }
                )
            ctx["resources"] = resources
            ctx["snapshot_time"] = latest
        else:
            ctx["resources"] = []
            ctx["snapshot_time"] = None

        return ctx
