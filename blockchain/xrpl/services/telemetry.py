"""
Economy telemetry service.

Aggregates raw economic data (transfer logs, game state, gold sinks,
AMM prices, player sessions) into hourly snapshot tables for the
spawn algorithm and admin monitoring.

Game code should NOT import this directly except from:
- character hooks (session start/end)
- the TelemetryAggregatorScript (hourly snapshots)
- the economy admin command (reading snapshots)
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone

from blockchain.xrpl.models import (
    CurrencyType,
    EconomySnapshot,
    FungibleGameState,
    FungibleTransferLog,
    NFTGameState,
    NFTItemType,
    PlayerSession,
    ResourceSnapshot,
)

logger = logging.getLogger("evennia")


class TelemetryService:
    """Aggregates economy data into hourly snapshots."""

    # ================================================================== #
    #  Session tracking
    # ================================================================== #

    @staticmethod
    def record_session_start(account_id, character_key):
        """Record the start of a play session. Called from at_post_puppet."""
        PlayerSession.objects.create(
            account_id=account_id,
            character_key=character_key,
            started_at=timezone.now(),
        )

    @staticmethod
    def record_session_end(account_id, character_key):
        """Close the most recent open session. Called from at_post_unpuppet."""
        session = (
            PlayerSession.objects.filter(
                account_id=account_id,
                character_key=character_key,
                ended_at__isnull=True,
            )
            .order_by("-started_at")
            .first()
        )
        if session:
            session.ended_at = timezone.now()
            session.save(update_fields=["ended_at"])

    @staticmethod
    def close_stale_sessions():
        """Close any sessions still open (crash recovery).

        Called on server boot. Sets ended_at = now for any open sessions,
        since we can't know when they actually ended.
        """
        count = PlayerSession.objects.filter(ended_at__isnull=True).update(
            ended_at=timezone.now(),
        )
        if count:
            logger.info(
                f"Telemetry: closed {count} stale session(s) from crash recovery"
            )

    # ================================================================== #
    #  Snapshot aggregation
    # ================================================================== #

    @staticmethod
    def take_snapshot():
        """Main aggregation entry point. Called hourly by the script.

        Computes all metrics and writes EconomySnapshot + ResourceSnapshot
        rows for the current hour bucket.
        """
        now = timezone.now()
        bucket = now.replace(minute=0, second=0, microsecond=0)
        hour_ago = bucket - timedelta(hours=1)
        day_ago = bucket - timedelta(hours=24)
        week_ago = bucket - timedelta(days=7)

        gold_code = settings.XRPL_GOLD_CURRENCY_CODE

        # ── Player activity ──
        players_online = PlayerSession.objects.filter(
            ended_at__isnull=True,
        ).values("account_id").distinct().count()

        unique_1h = _unique_players_since(hour_ago)
        unique_24h = _unique_players_since(day_ago)
        unique_7d = _unique_players_since(week_ago)

        # ── Gold state ──
        gold_circulation = _sum_balance(
            gold_code,
            [FungibleGameState.LOCATION_CHARACTER, FungibleGameState.LOCATION_ACCOUNT],
        )
        gold_reserve = _sum_balance(
            gold_code,
            [FungibleGameState.LOCATION_RESERVE],
        )

        # ── Gold sinks (running total in SINK location) ──
        gold_sinks = _sum_balance(
            gold_code, [FungibleGameState.LOCATION_SINK],
        )

        # ── Gold spawned (pickup transfers in past hour) ──
        gold_spawned = _transfer_volume(gold_code, ["pickup"], hour_ago, now)

        # ── AMM trade activity ──
        amm_trades = FungibleTransferLog.objects.filter(
            transfer_type__in=["amm_buy", "amm_sell"],
            timestamp__gte=hour_ago,
            timestamp__lt=now,
        ).count()
        # Count player-side gold logs only (avoid double-counting swap legs)
        amm_gold_volume = (
            FungibleTransferLog.objects.filter(
                currency_code=gold_code,
                transfer_type__in=["amm_buy", "amm_sell"],
                timestamp__gte=hour_ago,
                timestamp__lt=now,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal(0)
        )

        # ── Chain activity ──
        imports_1h = FungibleTransferLog.objects.filter(
            transfer_type="deposit_from_chain",
            timestamp__gte=hour_ago,
            timestamp__lt=now,
        ).count()
        exports_1h = FungibleTransferLog.objects.filter(
            transfer_type="withdraw_to_chain",
            timestamp__gte=hour_ago,
            timestamp__lt=now,
        ).count()

        # ── Write EconomySnapshot ──
        EconomySnapshot.objects.update_or_create(
            hour=bucket,
            defaults={
                "players_online": players_online,
                "unique_players_1h": unique_1h,
                "unique_players_24h": unique_24h,
                "unique_players_7d": unique_7d,
                "gold_circulation": gold_circulation,
                "gold_reserve": gold_reserve,
                "gold_sinks_1h": gold_sinks,
                "gold_spawned_1h": gold_spawned,
                "amm_trades_1h": amm_trades,
                "amm_volume_gold_1h": amm_gold_volume,
                "imports_1h": imports_1h,
                "exports_1h": exports_1h,
            },
        )

        # ── Per-currency snapshots ──
        amm_prices = _fetch_amm_prices()

        # Build NFT circulation counts: one query, grouped by item_type
        # and location. Only rows with item_type assigned are in circulation.
        nft_circulation = _nft_circulation_by_tracking_token()

        for ct in CurrencyType.objects.all():
            code = ct.currency_code
            prices = amm_prices.get(code, {})

            # Check if this currency is a proxy token for an NFT item type
            nft_counts = nft_circulation.get(code)

            if nft_counts is not None:
                # Proxy token — circulation from NFTGameState, not FungibleGameState
                defaults = {
                    "in_character": Decimal(nft_counts.get("CHARACTER", 0)),
                    "in_account": Decimal(nft_counts.get("ACCOUNT", 0)),
                    "in_spawned": Decimal(nft_counts.get("SPAWNED", 0)),
                    "in_reserve": Decimal(nft_counts.get("RESERVE", 0)),
                    "in_sink": Decimal(0),  # NFTs don't have a SINK location
                    "produced_1h": _transfer_volume(
                        code, ["craft_output", "pickup", "nft_amm_swap"],
                        hour_ago, now,
                    ),
                    "consumed_1h": _transfer_volume(
                        code, ["craft_input", "sink", "nft_amm_swap"],
                        hour_ago, now,
                    ),
                    "traded_1h": _transfer_volume(
                        code, ["nft_amm_buy", "nft_amm_sell", "nft_amm_swap"],
                        hour_ago, now,
                    ),
                    "exported_1h": Decimal(0),
                    "imported_1h": Decimal(0),
                    "amm_buy_price": prices.get("buy_1"),
                    "amm_sell_price": prices.get("sell_1"),
                }
            else:
                # Regular fungible currency — circulation from FungibleGameState
                defaults = {
                    "in_character": _sum_balance(
                        code, [FungibleGameState.LOCATION_CHARACTER],
                    ),
                    "in_account": _sum_balance(
                        code, [FungibleGameState.LOCATION_ACCOUNT],
                    ),
                    "in_spawned": _sum_balance(
                        code, [FungibleGameState.LOCATION_SPAWNED],
                    ),
                    "in_reserve": _sum_balance(
                        code, [FungibleGameState.LOCATION_RESERVE],
                    ),
                    "in_sink": _sum_balance(
                        code, [FungibleGameState.LOCATION_SINK],
                    ),
                    "produced_1h": _transfer_volume(
                        code, ["craft_output", "pickup"], hour_ago, now,
                    ),
                    "consumed_1h": _transfer_volume(
                        code, ["craft_input", "sink"], hour_ago, now,
                    ),
                    "traded_1h": _transfer_volume(
                        code, ["amm_buy", "amm_sell"], hour_ago, now,
                    ),
                    "exported_1h": _transfer_volume(
                        code, ["withdraw_to_chain"], hour_ago, now,
                    ),
                    "imported_1h": _transfer_volume(
                        code, ["deposit_from_chain"], hour_ago, now,
                    ),
                    "amm_buy_price": prices.get("buy_1"),
                    "amm_sell_price": prices.get("sell_1"),
                }

            ResourceSnapshot.objects.update_or_create(
                hour=bucket,
                currency_code=code,
                defaults=defaults,
            )

        logger.info(
            f"Telemetry snapshot: {bucket:%Y-%m-%d %H:%M} — "
            f"{players_online} online, {unique_24h} active/24h, "
            f"{amm_trades} AMM trades"
        )


# ================================================================== #
#  Helper functions (module-private)
# ================================================================== #

def _unique_players_since(since):
    """Count distinct account_ids with sessions overlapping the period."""
    return (
        PlayerSession.objects.filter(
            Q(ended_at__isnull=True) | Q(ended_at__gte=since),
            started_at__lte=timezone.now(),
        )
        .values("account_id")
        .distinct()
        .count()
    )


def _sum_balance(currency_code, locations):
    """Sum FungibleGameState balance for a currency across locations."""
    return (
        FungibleGameState.objects.filter(
            currency_code=currency_code,
            location__in=locations,
        ).aggregate(total=Sum("balance"))["total"]
        or Decimal(0)
    )


def _transfer_volume(currency_code, transfer_types, since, until):
    """Sum transfer amounts for a currency and set of transfer types."""
    return (
        FungibleTransferLog.objects.filter(
            currency_code=currency_code,
            transfer_type__in=transfer_types,
            timestamp__gte=since,
            timestamp__lt=until,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal(0)
    )


def _fetch_amm_prices():
    """Fetch current AMM prices for all tradeable currencies.

    Makes two batch queries:
      1. Game resources priced against FCMGold (resource_id IS NOT NULL)
      2. Proxy tokens priced against PGold (tracking_token IS NOT NULL)

    Results are merged into a single dict keyed by currency_code.
    Wrapped in try/except so telemetry works when XRPL is unavailable.
    """
    result = {}
    try:
        from blockchain.xrpl.xrpl_amm import get_multi_pool_prices

        # 1. Resource pools (vs FCMGold)
        resource_codes = list(
            CurrencyType.objects.filter(resource_id__isnull=False)
            .values_list("currency_code", flat=True)
        )
        if resource_codes:
            result.update(get_multi_pool_prices(resource_codes))

        # 2. Proxy token pools (vs PGold)
        proxy_codes = list(
            NFTItemType.objects.filter(tracking_token__isnull=False)
            .values_list("tracking_token", flat=True)
        )
        if proxy_codes:
            pgold = settings.XRPL_PGOLD_CURRENCY_CODE
            result.update(
                get_multi_pool_prices(proxy_codes, gold_currency=pgold)
            )

    except Exception as err:
        logger.warning(f"Telemetry: AMM price fetch failed: {err}")
    return result


def _nft_circulation_by_tracking_token():
    """Query NFT circulation counts grouped by tracking_token and location.

    Returns:
        dict {tracking_token: {location: count, ...}}
        Only includes item types that have a tracking_token set.
    """
    rows = (
        NFTGameState.objects.filter(item_type__isnull=False)
        .values("item_type__tracking_token", "location")
        .annotate(count=Count("id"))
    )
    result = {}
    for row in rows:
        token = row["item_type__tracking_token"]
        if token is None:
            continue
        if token not in result:
            result[token] = {}
        result[token][row["location"]] = row["count"]
    return result
