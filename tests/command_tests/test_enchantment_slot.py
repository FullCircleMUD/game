"""
Tests for EnchantmentSlot model and EnchantmentService.

Covers the compliance-critical pre-disclosure system: slot lazily seeds,
preview is a pure read, consume advances atomically with a slot_number
tiebreaker, and stale-slot consumes return None without mutating state.

evennia test --settings settings tests.command_tests.test_enchantment_slot
"""

from unittest.mock import patch

from django.test import TransactionTestCase

from blockchain.xrpl.models import EnchantmentSlot
from blockchain.xrpl.services.enchantment import EnchantmentService


_FLY = [{"type": "condition", "condition": "fly"}]
_DARKVISION = [{"type": "condition", "condition": "darkvision"}]
_INITIATIVE = [{"type": "stat_bonus", "stat": "initiative_bonus", "value": 1}]


def _stub_roll(effects, restrictions=None):
    """Patch helper: make roll_gem_enchantment return a fixed outcome.

    Returns (effects_list, restrictions_dict). Restrictions is a dict in
    ItemRestrictionMixin field format (required_classes, excluded_classes,
    required_races, excluded_races, min/max_alignment_score).
    """
    return patch(
        "blockchain.xrpl.services.enchantment.roll_gem_enchantment",
        return_value=(effects, restrictions or {}),
    )


class TestPreviewSlot(TransactionTestCase):
    """preview_slot lazily seeds and is a pure read."""

    databases = {"default", "xrpl"}

    def test_lazy_seed_creates_row_on_first_query(self):
        self.assertFalse(
            EnchantmentSlot.objects.filter(
                output_table="enchanted_ruby", mastery_level=1,
            ).exists()
        )
        with _stub_roll(_FLY):
            preview = EnchantmentService.preview_slot("enchanted_ruby", 1)

        self.assertEqual(preview["slot_number"], 1)
        self.assertEqual(preview["wear_effects"], _FLY)
        self.assertEqual(preview["restrictions"], {})
        self.assertTrue(
            EnchantmentSlot.objects.filter(
                output_table="enchanted_ruby", mastery_level=1,
            ).exists()
        )

    def test_preview_is_idempotent(self):
        """Multiple previews return the same outcome and don't advance."""
        with _stub_roll(_FLY):
            first = EnchantmentService.preview_slot("enchanted_ruby", 1)
            second = EnchantmentService.preview_slot("enchanted_ruby", 1)
            third = EnchantmentService.preview_slot("enchanted_ruby", 1)

        self.assertEqual(first, second)
        self.assertEqual(second, third)
        self.assertEqual(first["slot_number"], 1)

    def test_separate_pairs_have_independent_slots(self):
        """ruby/m1 and ruby/m2 are different rows with independent state."""
        with _stub_roll(_FLY):
            EnchantmentService.preview_slot("enchanted_ruby", 1)
        with _stub_roll(_DARKVISION):
            EnchantmentService.preview_slot("enchanted_ruby", 2)

        self.assertEqual(EnchantmentSlot.objects.count(), 2)


class TestConsumeSlot(TransactionTestCase):
    """consume_slot advances atomically and rolls the next outcome."""

    databases = {"default", "xrpl"}

    def test_consume_returns_seeded_outcome_and_advances(self):
        with _stub_roll(_FLY):
            EnchantmentService.preview_slot("enchanted_ruby", 1)

        with _stub_roll(_DARKVISION):
            outcome = EnchantmentService.consume_slot("enchanted_ruby", 1, 1)

        self.assertEqual(outcome["wear_effects"], _FLY)
        self.assertEqual(outcome["restrictions"], {})

        slot = EnchantmentSlot.objects.get(
            output_table="enchanted_ruby", mastery_level=1,
        )
        self.assertEqual(slot.slot_number, 2)
        self.assertEqual(slot.current_outcome["wear_effects"], _DARKVISION)

    def test_consume_with_stale_slot_number_returns_none_and_no_mutation(self):
        with _stub_roll(_FLY):
            EnchantmentService.preview_slot("enchanted_ruby", 1)
        with _stub_roll(_DARKVISION):
            EnchantmentService.consume_slot("enchanted_ruby", 1, 1)

        before = EnchantmentSlot.objects.get(
            output_table="enchanted_ruby", mastery_level=1,
        )

        with _stub_roll(_INITIATIVE):
            result = EnchantmentService.consume_slot("enchanted_ruby", 1, 1)

        self.assertIsNone(result)

        after = EnchantmentSlot.objects.get(
            output_table="enchanted_ruby", mastery_level=1,
        )
        self.assertEqual(after.slot_number, before.slot_number)
        self.assertEqual(after.current_outcome, before.current_outcome)

    def test_two_sequential_consumes_simulate_race_first_wins(self):
        """Both players preview slot N; first commits, second's commit
        with the same N returns None — no double-spend."""
        with _stub_roll(_FLY):
            preview_a = EnchantmentService.preview_slot("enchanted_ruby", 1)
        preview_b = EnchantmentService.preview_slot("enchanted_ruby", 1)
        self.assertEqual(preview_a["slot_number"], preview_b["slot_number"])

        with _stub_roll(_DARKVISION):
            winner = EnchantmentService.consume_slot(
                "enchanted_ruby", 1, preview_a["slot_number"],
            )
        with _stub_roll(_INITIATIVE):
            loser = EnchantmentService.consume_slot(
                "enchanted_ruby", 1, preview_b["slot_number"],
            )

        self.assertEqual(winner["wear_effects"], _FLY)
        self.assertIsNone(loser)

    def test_consume_persists_restrictions(self):
        restrictions = {"required_classes": ["mage"], "min_alignment_score": 300}
        with patch(
            "blockchain.xrpl.services.enchantment.roll_gem_enchantment",
            return_value=(_FLY, restrictions),
        ):
            EnchantmentService.preview_slot("enchanted_ruby", 1)

        with _stub_roll(_DARKVISION):
            outcome = EnchantmentService.consume_slot("enchanted_ruby", 1, 1)

        self.assertEqual(outcome["restrictions"], restrictions)
