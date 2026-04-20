"""Tests for SpawnService._persist_spawn_telemetry().

Verifies that BudgetState counters are written to the correct snapshot
tables (ResourceSnapshot for resources/gold, SaturationSnapshot for
knowledge items).
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.utils import timezone
from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.models import ResourceSnapshot, SaturationSnapshot
from blockchain.xrpl.services.spawn.budget import BudgetState
from blockchain.xrpl.services.spawn.service import SpawnService


_MINI_CONFIG = {
    ("resource", 1): {
        "calculator": "resource",
        "default_spawn_rate": 10,
        "target_price_low": 8,
        "target_price_high": 16,
        "modifier_min": 0.25,
        "modifier_max": 2.0,
    },
    ("gold", "gold"): {
        "calculator": "gold",
        "default_spawn_rate": 50,
        "buffer": 1.15,
        "min_runway_days": 7,
    },
}


class TestPersistSpawnTelemetryResources(EvenniaTest):
    """_persist_spawn_telemetry writes resource budget to ResourceSnapshot."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_resource_budget_written_to_snapshot(self):
        """Resource BudgetState counters update matching ResourceSnapshot."""
        now = timezone.now()
        bucket = now.replace(minute=0, second=0, microsecond=0)

        # Create a ResourceSnapshot for this hour (simulates telemetry service)
        ResourceSnapshot.objects.create(
            hour=bucket,
            currency_code="FCMWheat",
        )

        svc = SpawnService(_MINI_CONFIG)
        bs = BudgetState(item_type="resource", type_key=1)
        bs.total = 20
        bs.quest_debt = 3
        bs.spawned_this_hour = 15
        bs.dropped_this_hour = 2
        svc.budget_states[("resource", 1)] = bs

        with patch(
            "blockchain.xrpl.currency_cache.get_currency_code",
        ) as mock_gcc:
            mock_gcc.return_value = "FCMWheat"
            svc._persist_spawn_telemetry()

        snap = ResourceSnapshot.objects.get(hour=bucket, currency_code="FCMWheat")
        self.assertEqual(snap.spawn_budget, 20)
        self.assertEqual(snap.spawn_quest_debt, 3)
        self.assertEqual(snap.spawn_placed, 15)
        self.assertEqual(snap.spawn_dropped, 2)

    def test_resource_no_currency_code_skips(self):
        """Resource with unknown currency_code does not crash."""
        svc = SpawnService(_MINI_CONFIG)
        bs = BudgetState(item_type="resource", type_key=999)
        bs.total = 5
        svc.budget_states[("resource", 999)] = bs

        with patch(
            "blockchain.xrpl.currency_cache.get_currency_code",
        ) as mock_gcc:
            mock_gcc.return_value = None
            # Should not raise
            svc._persist_spawn_telemetry()

    def test_resource_no_matching_snapshot_is_noop(self):
        """If no ResourceSnapshot exists for this hour, update is a no-op."""
        svc = SpawnService(_MINI_CONFIG)
        bs = BudgetState(item_type="resource", type_key=1)
        bs.total = 10
        bs.spawned_this_hour = 8
        svc.budget_states[("resource", 1)] = bs

        with patch(
            "blockchain.xrpl.currency_cache.get_currency_code",
        ) as mock_gcc:
            mock_gcc.return_value = "FCMWheat"
            # No snapshot in DB — update hits zero rows, no error
            svc._persist_spawn_telemetry()

        self.assertEqual(ResourceSnapshot.objects.count(), 0)


class TestPersistSpawnTelemetryGold(EvenniaTest):
    """_persist_spawn_telemetry writes gold budget to ResourceSnapshot."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_gold_budget_written_to_snapshot(self):
        """Gold BudgetState counters update the FCMGold ResourceSnapshot."""
        now = timezone.now()
        bucket = now.replace(minute=0, second=0, microsecond=0)

        ResourceSnapshot.objects.create(
            hour=bucket,
            currency_code="FCMGold",
        )

        svc = SpawnService(_MINI_CONFIG)
        bs = BudgetState(item_type="gold", type_key="gold")
        bs.total = 50
        bs.quest_debt = 10
        bs.spawned_this_hour = 35
        bs.dropped_this_hour = 5
        svc.budget_states[("gold", "gold")] = bs

        svc._persist_spawn_telemetry()

        snap = ResourceSnapshot.objects.get(
            hour=bucket, currency_code="FCMGold",
        )
        self.assertEqual(snap.spawn_budget, 50)
        self.assertEqual(snap.spawn_quest_debt, 10)
        self.assertEqual(snap.spawn_placed, 35)
        self.assertEqual(snap.spawn_dropped, 5)


class TestPersistSpawnTelemetryKnowledge(EvenniaTest):
    """_persist_spawn_telemetry writes knowledge budget to SaturationSnapshot."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_knowledge_budget_written_to_saturation_snapshot(self):
        """Knowledge BudgetState counters update SaturationSnapshot."""
        bucket = timezone.now().replace(minute=0, second=0, microsecond=0)

        SaturationSnapshot.objects.create(
            hour=bucket,
            item_key="scroll_magic_missile",
            category="spell",
            active_players_7d=100,
            eligible_players=50,
            known_by=30,
            unlearned_copies=5,
            saturation=0.7,
        )

        svc = SpawnService(_MINI_CONFIG)
        bs = BudgetState(item_type="knowledge", type_key="scroll_magic_missile")
        bs.total = 15
        bs.quest_debt = 2
        bs.spawned_this_hour = 12
        bs.dropped_this_hour = 1
        svc.budget_states[("knowledge", "scroll_magic_missile")] = bs

        svc._persist_spawn_telemetry()

        snap = SaturationSnapshot.objects.get(
            hour=bucket, item_key="scroll_magic_missile",
        )
        self.assertEqual(snap.spawn_budget, 15)
        self.assertEqual(snap.spawn_quest_debt, 2)
        self.assertEqual(snap.spawn_placed, 12)
        self.assertEqual(snap.spawn_dropped, 1)
        # Original saturation data preserved
        self.assertEqual(snap.eligible_players, 50)
        self.assertEqual(snap.known_by, 30)

    def test_knowledge_no_matching_snapshot_is_noop(self):
        """If no SaturationSnapshot exists, update hits zero rows."""
        svc = SpawnService(_MINI_CONFIG)
        bs = BudgetState(item_type="knowledge", type_key="scroll_fireball")
        bs.total = 5
        svc.budget_states[("knowledge", "scroll_fireball")] = bs

        # No snapshot in DB — should not raise
        svc._persist_spawn_telemetry()
        self.assertEqual(SaturationSnapshot.objects.count(), 0)
