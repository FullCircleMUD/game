"""Tests for KnowledgeCalculator (gap-based budget).

The calculator uses: budget = max(0, eligible - known - unlearned)
It reads the latest SaturationSnapshot via _get_snapshot().
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.services.spawn.calculators.knowledge import KnowledgeCalculator

_TEST_CONFIG = {
    ("knowledge", "scroll_magic_missile"): {
        "calculator": "knowledge",
        "base_drop_rate": 2,
        "tier": "basic",
    },
    ("knowledge", "scroll_fireball"): {
        "calculator": "knowledge",
        "base_drop_rate": 1,
        "tier": "skilled",
    },
}


def _mock_snapshot(eligible=0, known=0, unlearned=0, saturation=0.0):
    """Build a mock SaturationSnapshot with the given fields."""
    snap = MagicMock()
    snap.eligible_players = eligible
    snap.known_by = known
    snap.unlearned_copies = unlearned
    snap.saturation = saturation
    return snap


class TestKnowledgeCalculator(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    # ------------------------------------------------------------------ #
    #  Gap-based budget tests
    # ------------------------------------------------------------------ #

    @patch.object(KnowledgeCalculator, "_get_snapshot")
    def test_full_gap_returns_eligible_count(self, mock_snap):
        """No one knows it, no copies exist → budget = eligible."""
        mock_snap.return_value = _mock_snapshot(eligible=10, known=0, unlearned=0)
        calc = KnowledgeCalculator(_TEST_CONFIG)
        self.assertEqual(calc.calculate("knowledge", "scroll_magic_missile"), 10)

    @patch.object(KnowledgeCalculator, "_get_snapshot")
    def test_half_known_halves_budget(self, mock_snap):
        """Half the eligible players know it → budget = remaining half."""
        mock_snap.return_value = _mock_snapshot(eligible=10, known=5, unlearned=0)
        calc = KnowledgeCalculator(_TEST_CONFIG)
        self.assertEqual(calc.calculate("knowledge", "scroll_magic_missile"), 5)

    @patch.object(KnowledgeCalculator, "_get_snapshot")
    def test_unlearned_copies_reduce_gap(self, mock_snap):
        """Unlearned copies in player hands close the gap."""
        mock_snap.return_value = _mock_snapshot(eligible=10, known=5, unlearned=3)
        calc = KnowledgeCalculator(_TEST_CONFIG)
        self.assertEqual(calc.calculate("knowledge", "scroll_magic_missile"), 2)

    @patch.object(KnowledgeCalculator, "_get_snapshot")
    def test_fully_saturated_zero_budget(self, mock_snap):
        """Everyone knows it → zero budget."""
        mock_snap.return_value = _mock_snapshot(eligible=10, known=10, unlearned=0)
        calc = KnowledgeCalculator(_TEST_CONFIG)
        self.assertEqual(calc.calculate("knowledge", "scroll_magic_missile"), 0)

    @patch.object(KnowledgeCalculator, "_get_snapshot")
    def test_over_saturated_clamped_to_zero(self, mock_snap):
        """More copies than eligible players → clamped to zero."""
        mock_snap.return_value = _mock_snapshot(eligible=10, known=8, unlearned=5)
        calc = KnowledgeCalculator(_TEST_CONFIG)
        self.assertEqual(calc.calculate("knowledge", "scroll_magic_missile"), 0)

    @patch.object(KnowledgeCalculator, "_get_snapshot", return_value=None)
    def test_no_snapshot_zero_budget(self, mock_snap):
        """No snapshot data → zero budget."""
        calc = KnowledgeCalculator(_TEST_CONFIG)
        self.assertEqual(calc.calculate("knowledge", "scroll_magic_missile"), 0)

    @patch.object(KnowledgeCalculator, "_get_snapshot", return_value=None)
    def test_no_eligible_players_zero_budget(self, mock_snap):
        """_get_snapshot returns None when eligible=0 → zero budget."""
        calc = KnowledgeCalculator(_TEST_CONFIG)
        self.assertEqual(calc.calculate("knowledge", "scroll_fireball"), 0)

    @patch.object(KnowledgeCalculator, "_get_snapshot")
    def test_single_new_player_spawns_one(self, mock_snap):
        """One new eligible player → exactly 1 scroll spawned."""
        mock_snap.return_value = _mock_snapshot(eligible=20, known=19, unlearned=0)
        calc = KnowledgeCalculator(_TEST_CONFIG)
        self.assertEqual(calc.calculate("knowledge", "scroll_magic_missile"), 1)

    @patch.object(KnowledgeCalculator, "_get_snapshot")
    def test_self_correcting_after_spawn(self, mock_snap):
        """Scrolls spawned last hour become unlearned copies → gap closes."""
        # Hour N: 3 players need scrolls, 3 spawned
        mock_snap.return_value = _mock_snapshot(eligible=10, known=5, unlearned=2)
        calc = KnowledgeCalculator(_TEST_CONFIG)
        self.assertEqual(calc.calculate("knowledge", "scroll_magic_missile"), 3)

        # Hour N+1: those 3 are now unlearned copies → gap = 0
        mock_snap.return_value = _mock_snapshot(eligible=10, known=5, unlearned=5)
        self.assertEqual(calc.calculate("knowledge", "scroll_magic_missile"), 0)

    # ------------------------------------------------------------------ #
    #  _get_saturation helper (still used for reporting)
    # ------------------------------------------------------------------ #

    @patch.object(KnowledgeCalculator, "_get_snapshot")
    def test_get_saturation_returns_snapshot_value(self, mock_snap):
        """_get_saturation returns the snapshot's saturation field."""
        mock_snap.return_value = _mock_snapshot(eligible=10, known=5, saturation=0.5)
        result = KnowledgeCalculator._get_saturation("scroll_magic_missile")
        self.assertEqual(result, 0.5)

    @patch.object(KnowledgeCalculator, "_get_snapshot", return_value=None)
    def test_get_saturation_returns_none_without_snapshot(self, mock_snap):
        """_get_saturation returns None when no snapshot exists."""
        result = KnowledgeCalculator._get_saturation("scroll_magic_missile")
        self.assertIsNone(result)


class TestGetSnapshotDB(EvenniaTest):
    """DB-level tests for KnowledgeCalculator._get_snapshot()."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_returns_latest_hour(self):
        """_get_snapshot returns the most recent hour's snapshot."""
        from datetime import timedelta
        from django.utils import timezone
        from blockchain.xrpl.models import SaturationSnapshot

        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        prev_hour = now - timedelta(hours=1)

        SaturationSnapshot.objects.create(
            hour=prev_hour, item_key="scroll_magic_missile",
            category="spell", active_players_7d=10,
            eligible_players=5, known_by=2, unlearned_copies=1,
            saturation=0.6,
        )
        SaturationSnapshot.objects.create(
            hour=now, item_key="scroll_magic_missile",
            category="spell", active_players_7d=12,
            eligible_players=8, known_by=3, unlearned_copies=2,
            saturation=0.625,
        )

        snap = KnowledgeCalculator._get_snapshot("scroll_magic_missile")
        self.assertIsNotNone(snap)
        self.assertEqual(snap.hour, now)
        self.assertEqual(snap.eligible_players, 8)

    def test_returns_none_when_no_snapshots(self):
        """_get_snapshot returns None when no snapshots exist."""
        snap = KnowledgeCalculator._get_snapshot("scroll_nonexistent")
        self.assertIsNone(snap)

    def test_returns_none_when_zero_eligible(self):
        """_get_snapshot returns None when eligible_players is 0."""
        from django.utils import timezone
        from blockchain.xrpl.models import SaturationSnapshot

        hour = timezone.now().replace(minute=0, second=0, microsecond=0)
        SaturationSnapshot.objects.create(
            hour=hour, item_key="scroll_magic_missile",
            category="spell", active_players_7d=10,
            eligible_players=0, known_by=0, unlearned_copies=0,
            saturation=0.0,
        )

        snap = KnowledgeCalculator._get_snapshot("scroll_magic_missile")
        self.assertIsNone(snap)

    def test_end_to_end_budget_from_db(self):
        """Full path: DB snapshot → _get_snapshot → calculate → correct gap."""
        from django.utils import timezone
        from blockchain.xrpl.models import SaturationSnapshot

        hour = timezone.now().replace(minute=0, second=0, microsecond=0)
        SaturationSnapshot.objects.create(
            hour=hour, item_key="scroll_magic_missile",
            category="spell", active_players_7d=50,
            eligible_players=20, known_by=12, unlearned_copies=3,
            saturation=0.75,
        )

        calc = KnowledgeCalculator(_TEST_CONFIG)
        budget = calc.calculate("knowledge", "scroll_magic_missile")
        # gap = 20 - 12 - 3 = 5
        self.assertEqual(budget, 5)
