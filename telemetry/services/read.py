"""Read side of the telemetry API.

Every method returns a list, a scalar, or a single row — never a queryset.
A queryset would let the caller keep querying through it, which is the
thing this API exists to stop: the telemetry tables answer questions here
and nowhere else.

Rows come back as model instances for now. They will become plain
structures once the display callers stop formatting straight off the
model; keep new callers reading named fields so that change stays a
mechanical one.
"""

from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from telemetry.constants import DEFAULT_AVERAGE_HOURS
from telemetry.models import (
    EconomySnapshot,
    PlayerSession,
    ResourceSnapshot,
    SaturationSnapshot,
)


class TelemetryReadService:
    """Stateless read API over the telemetry tables."""

    # ================================================================== #
    #  Play sessions
    # ================================================================== #

    @staticmethod
    def players_online():
        """Distinct accounts with a session still open."""
        return (
            PlayerSession.objects.filter(ended_at__isnull=True)
            .values("account_id")
            .distinct()
            .count()
        )

    @staticmethod
    def unique_players_since(since):
        """Distinct accounts whose sessions overlap the period since ``since``."""
        return (
            PlayerSession.objects.filter(
                Q(ended_at__isnull=True) | Q(ended_at__gte=since),
                started_at__lte=timezone.now(),
            )
            .values("account_id")
            .distinct()
            .count()
        )

    @staticmethod
    def active_character_keys(since):
        """Character keys with sessions overlapping the period since ``since``.

        Returns:
            (count, character_keys) — the count is of distinct keys, so it
            counts characters played rather than sessions or accounts.
        """
        keys = set(
            PlayerSession.objects.filter(
                Q(ended_at__isnull=True) | Q(ended_at__gte=since),
                started_at__lte=timezone.now(),
            )
            .values_list("character_key", flat=True)
            .distinct()
        )
        return len(keys), keys

    # ================================================================== #
    #  Economy snapshots
    # ================================================================== #

    @staticmethod
    def latest_economy_snapshot():
        """Most recent hourly economy snapshot, or None if none exist."""
        return EconomySnapshot.objects.order_by("-hour").first()

    @staticmethod
    def recent_economy_snapshots(limit=None):
        """Economy snapshots, most recent first."""
        rows = EconomySnapshot.objects.order_by("-hour")
        if limit is not None:
            rows = rows[:limit]
        return list(rows)

    @staticmethod
    def economy_snapshot_count():
        """How many hourly economy snapshots exist."""
        return EconomySnapshot.objects.count()

    @staticmethod
    def average_gold_sinks(hours=DEFAULT_AVERAGE_HOURS):
        """Mean gold_sinks_1h over the most recent ``hours`` snapshots.

        Returns Decimal(0) when there are no snapshots yet.
        """
        values = list(
            EconomySnapshot.objects.order_by("-hour")
            .values_list("gold_sinks_1h", flat=True)[:hours]
        )
        if not values:
            return Decimal(0)
        return sum(values) / len(values)

    # ================================================================== #
    #  Resource snapshots
    # ================================================================== #

    @staticmethod
    def latest_resource_hour():
        """Hour of the most recent resource snapshot, or None."""
        return (
            ResourceSnapshot.objects.order_by("-hour")
            .values_list("hour", flat=True)
            .first()
        )

    @staticmethod
    def resource_hours(limit=None):
        """Distinct hours that have resource snapshots, most recent first."""
        hours = (
            ResourceSnapshot.objects.values_list("hour", flat=True)
            .distinct()
            .order_by("-hour")
        )
        if limit is not None:
            hours = hours[:limit]
        return list(hours)

    @staticmethod
    def resource_hour_count():
        """How many distinct hours have resource snapshots."""
        return (
            ResourceSnapshot.objects.values_list("hour", flat=True)
            .distinct()
            .count()
        )

    @staticmethod
    def resource_rows_at(hour):
        """Every resource snapshot for one hour, ordered by currency code."""
        return list(
            ResourceSnapshot.objects.filter(hour=hour).order_by("currency_code")
        )

    @staticmethod
    def top_resource_rows_at(hour, limit=12, exclude_prefix=None):
        """Resource snapshots for one hour, largest player holdings first.

        Args:
            exclude_prefix: currency codes starting with this are left out —
                used to keep gold out of a resource table.
        """
        rows = ResourceSnapshot.objects.filter(hour=hour)
        if exclude_prefix:
            rows = rows.exclude(currency_code__startswith=exclude_prefix)
        return list(rows.order_by("-in_character")[:limit])

    @staticmethod
    def resource_history(currency_code, limit=DEFAULT_AVERAGE_HOURS):
        """Recent snapshots for one currency, most recent first."""
        return list(
            ResourceSnapshot.objects.filter(currency_code=currency_code)
            .order_by("-hour")[:limit]
        )

    @staticmethod
    def match_currency_codes(fragment, limit=5):
        """Currency codes that have snapshots and contain ``fragment``.

        Case-insensitive. Used to turn what an admin typed into a code.
        """
        return list(
            ResourceSnapshot.objects.filter(currency_code__icontains=fragment)
            .values_list("currency_code", flat=True)
            .distinct()[:limit]
        )

    @staticmethod
    def average_consumption(currency_code, hours=DEFAULT_AVERAGE_HOURS):
        """Mean consumed_1h for one currency over the most recent ``hours``.

        Returns Decimal(0) when the currency has no snapshots yet.
        """
        values = list(
            ResourceSnapshot.objects.filter(currency_code=currency_code)
            .order_by("-hour")
            .values_list("consumed_1h", flat=True)[:hours]
        )
        if not values:
            return Decimal(0)
        return sum(values) / len(values)

    @staticmethod
    def latest_buy_price(currency_code):
        """Most recently recorded AMM buy price, or None if never priced."""
        return (
            ResourceSnapshot.objects.filter(
                currency_code=currency_code,
                amm_buy_price__isnull=False,
            )
            .order_by("-hour")
            .values_list("amm_buy_price", flat=True)
            .first()
        )

    # ================================================================== #
    #  Saturation snapshots
    # ================================================================== #

    @staticmethod
    def saturation_hours(limit=None):
        """Distinct hours that have saturation snapshots, most recent first."""
        hours = (
            SaturationSnapshot.objects.values_list("hour", flat=True)
            .distinct()
            .order_by("-hour")
        )
        if limit is not None:
            hours = hours[:limit]
        return list(hours)

    @staticmethod
    def saturation_hour_count():
        """How many distinct hours have saturation snapshots."""
        return (
            SaturationSnapshot.objects.values_list("hour", flat=True)
            .distinct()
            .count()
        )

    @staticmethod
    def saturation_rows_at(hour):
        """Every saturation row for one hour, ordered by category then item."""
        return list(
            SaturationSnapshot.objects.filter(hour=hour).order_by(
                "category", "item_key"
            )
        )

    @staticmethod
    def latest_saturation(item_key):
        """Most recent saturation row for one item, or None."""
        return (
            SaturationSnapshot.objects.filter(item_key=item_key)
            .order_by("-hour")
            .first()
        )

    @staticmethod
    def saturation_totals():
        """How much saturation data exists.

        Returns:
            (hours, rows) — distinct hours covered, and total rows.
        """
        hours = (
            SaturationSnapshot.objects.values_list("hour", flat=True)
            .distinct()
            .count()
        )
        return hours, SaturationSnapshot.objects.count()
