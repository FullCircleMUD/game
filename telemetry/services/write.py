"""Write side of the telemetry API.

Producers hand finished numbers to these methods. Nothing here computes a
metric — the aggregators do that against the data they own, then record
the result through this seam.
"""

import logging

from django.utils import timezone

from telemetry.models import (
    EconomySnapshot,
    PlayerSession,
    ResourceSnapshot,
    SaturationSnapshot,
)

logger = logging.getLogger("evennia")


class TelemetryWriteService:
    """Stateless write API over the telemetry tables."""

    # ================================================================== #
    #  Play sessions
    # ================================================================== #

    @staticmethod
    def record_session_start(account_id, character_key):
        """Open a session row. Called from at_post_puppet."""
        PlayerSession.objects.create(
            account_id=account_id,
            character_key=character_key,
            started_at=timezone.now(),
        )

    @staticmethod
    def record_session_end(account_id, character_key):
        """Close the most recent open session. Called from at_post_unpuppet.

        Silently does nothing when no session is open — a character can be
        unpuppeted without a matching start (a crash between the two, or a
        character created before telemetry began recording).
        """
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
        """Close every session still open. Called on server boot.

        Sets ended_at to now, because when they actually ended is not
        recoverable after a crash.

        Returns the number of sessions closed.
        """
        count = PlayerSession.objects.filter(ended_at__isnull=True).update(
            ended_at=timezone.now(),
        )
        if count:
            logger.info(
                f"Telemetry: closed {count} stale session(s) from crash recovery"
            )
        return count

    # ================================================================== #
    #  Snapshots
    # ================================================================== #

    @staticmethod
    def write_economy_snapshot(hour, metrics):
        """Record the global economy snapshot for one hour.

        Re-running an hour overwrites it, so an aggregator that runs twice
        in the same hour is harmless.
        """
        EconomySnapshot.objects.update_or_create(hour=hour, defaults=metrics)

    @staticmethod
    def write_resource_snapshot(hour, currency_code, metrics):
        """Record one currency's snapshot for one hour."""
        ResourceSnapshot.objects.update_or_create(
            hour=hour, currency_code=currency_code, defaults=metrics,
        )

    @staticmethod
    def write_saturation_snapshot(hour, item_key, category, metrics):
        """Record one tracked item's saturation for one hour."""
        SaturationSnapshot.objects.update_or_create(
            hour=hour, item_key=item_key, category=category, defaults=metrics,
        )

    # ================================================================== #
    #  Spawn counters
    # ================================================================== #
    #
    #  The spawn cycle runs after the snapshot rows exist and fills in what
    #  it did with the budget. An hour with no row is not an error — it
    #  means the aggregator has not run for that hour yet — so these report
    #  how many rows they touched rather than raising.

    @staticmethod
    def apply_resource_spawn_counters(
        hour, currency_code, budget, quest_debt, placed, dropped
    ):
        """Record what the spawn cycle did with one currency's budget."""
        return ResourceSnapshot.objects.filter(
            hour=hour, currency_code=currency_code,
        ).update(
            spawn_budget=budget,
            spawn_quest_debt=quest_debt,
            spawn_placed=placed,
            spawn_dropped=dropped,
        )

    @staticmethod
    def apply_saturation_spawn_counters(
        hour, item_key, budget, quest_debt, placed, dropped
    ):
        """Record what the spawn cycle did with one knowledge item's budget."""
        return SaturationSnapshot.objects.filter(
            hour=hour, item_key=item_key,
        ).update(
            spawn_budget=budget,
            spawn_quest_debt=quest_debt,
            spawn_placed=placed,
            spawn_dropped=dropped,
        )
