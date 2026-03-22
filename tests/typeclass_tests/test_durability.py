"""
Tests for DurabilityMixin — durability tracking, progressive warnings,
and the at_break hook.

Uses WearableNFTItem (which mixes in DurabilityMixin) for real Evennia
objects. Tests verify mixin behaviour through the concrete class.

evennia test --settings settings tests.typeclass_tests.test_durability
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.wearslot import HumanoidWearSlot


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _make_wearable(key, location, max_dur=100):
    """Create a WearableNFTItem with given durability."""
    obj = create.create_object(
        "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
        key=key,
        nohome=True,
    )
    obj.wearslot = HumanoidWearSlot.HEAD
    obj.max_durability = max_dur
    obj.durability = max_dur
    obj.move_to(location, quiet=True)
    return obj


class DurabilityTestBase(EvenniaTest):
    """Base class with common setup."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)


# ── Basic Durability Tests ───────────────────────────────────────────────

class TestReduceDurability(DurabilityTestBase):
    """Test basic durability reduction."""

    def test_reduce_durability_decrements(self):
        item = _make_wearable("Helm", self.char1)
        item.reduce_durability(1)
        self.assertEqual(item.durability, 99)

    def test_reduce_durability_by_amount(self):
        item = _make_wearable("Helm", self.char1)
        item.reduce_durability(10)
        self.assertEqual(item.durability, 90)

    def test_durability_cannot_go_negative(self):
        item = _make_wearable("Helm", self.char1, max_dur=5)
        item.durability = 3
        item.reduce_durability(10)
        # at_break fires and deletes, so item is gone
        # Just verify no error was raised (item was cleaned up)

    def test_unbreakable_item_ignores_durability(self):
        item = _make_wearable("Ring", self.char1, max_dur=0)
        item.durability = None  # unbreakable items don't track durability
        item.reduce_durability(1)
        # Should do nothing — item still exists
        self.assertIsNotNone(item.pk)

    def test_repairable_flag_defaults_true(self):
        item = _make_wearable("Helm", self.char1)
        self.assertTrue(item.repairable)

    def test_durability_init_sets_from_max(self):
        """at_durability_init sets durability = max_durability."""
        obj = create.create_object(
            "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
            key="Test Item",
            nohome=True,
        )
        # at_object_creation calls at_durability_init
        self.assertEqual(obj.durability, obj.max_durability)


# ── Progressive Warning Tests ────────────────────────────────────────────

class TestDurabilityWarnings(DurabilityTestBase):
    """Test progressive warning messages at damage thresholds."""

    def _collect_msgs(self, item, start_dur, reduce_by=1):
        """Reduce durability and capture all messages sent to char1."""
        item.durability = start_dur
        with patch.object(self.char1, "msg", new_callable=MagicMock) as mock_msg:
            item.reduce_durability(reduce_by)
            return " ".join(str(call) for call in mock_msg.call_args_list)

    def test_warning_light_at_25_pct_damaged(self):
        """Warning when crossing 25% damaged threshold."""
        item = _make_wearable("Helm", self.char1, max_dur=100)
        msgs = self._collect_msgs(item, start_dur=76)
        self.assertEqual(item.durability, 75)
        self.assertIn("showing signs of wear", msgs)

    def test_warning_moderate_at_50_pct_damaged(self):
        """Warning when crossing 50% damaged threshold."""
        item = _make_wearable("Helm", self.char1, max_dur=100)
        msgs = self._collect_msgs(item, start_dur=51)
        self.assertEqual(item.durability, 50)
        self.assertIn("moderately damaged", msgs)

    def test_warning_heavy_at_75_pct_damaged(self):
        """Warning when crossing 75% damaged threshold."""
        item = _make_wearable("Helm", self.char1, max_dur=100)
        msgs = self._collect_msgs(item, start_dur=26)
        self.assertEqual(item.durability, 25)
        self.assertIn("heavily damaged", msgs)

    def test_warning_critical_at_90_pct_damaged(self):
        """Warning when reaching 90% damaged."""
        item = _make_wearable("Helm", self.char1, max_dur=100)
        msgs = self._collect_msgs(item, start_dur=11)
        self.assertEqual(item.durability, 10)
        self.assertIn("about to break", msgs)

    def test_critical_warning_every_use(self):
        """Critical warning fires on every use past 90% damaged."""
        item = _make_wearable("Helm", self.char1, max_dur=100)
        msgs = self._collect_msgs(item, start_dur=8)
        self.assertIn("about to break", msgs)

    def test_threshold_warnings_fire_once(self):
        """25% warning should not repeat on the next use after crossing."""
        item = _make_wearable("Helm", self.char1, max_dur=100)
        # Cross 25% threshold
        item.durability = 76
        item.reduce_durability(1)  # 76 → 75, fires warning

        # Next use — 74 remaining, no new threshold crossed
        with patch.object(self.char1, "msg", new_callable=MagicMock) as mock_msg:
            item.reduce_durability(1)  # 75 → 74
            msgs = " ".join(str(call) for call in mock_msg.call_args_list)
            self.assertNotIn("showing signs of wear", msgs)


# ── Break Tests ──────────────────────────────────────────────────────────

class TestAtBreak(DurabilityTestBase):
    """Test at_break fires and cleans up the item."""

    def test_at_break_called_at_zero(self):
        """Reducing to 0 triggers at_break → item deleted."""
        item = _make_wearable("Fragile Helm", self.char1, max_dur=1)
        item_pk = item.pk
        item.reduce_durability(1)
        # Item should be deleted from DB
        from evennia.objects.models import ObjectDB
        self.assertFalse(ObjectDB.objects.filter(pk=item_pk).exists())

    def test_break_message_sent(self):
        """Player receives break message."""
        item = _make_wearable("Fragile Helm", self.char1, max_dur=1)
        with patch.object(self.char1, "msg", new_callable=MagicMock) as mock_msg:
            item.reduce_durability(1)
            msgs = " ".join(str(call) for call in mock_msg.call_args_list)
            self.assertIn("breaks and is destroyed", msgs)


class TestConditionLabel(DurabilityTestBase):
    """Test get_condition_label() returns correct labels."""

    def test_pristine_at_full(self):
        item = _make_wearable("Helm", self.char1, max_dur=100)
        self.assertIn("Pristine", item.get_condition_label())

    def test_good_at_99_pct(self):
        item = _make_wearable("Helm", self.char1, max_dur=100)
        item.durability = 99
        self.assertIn("Good", item.get_condition_label())

    def test_good_at_75_pct(self):
        item = _make_wearable("Helm", self.char1, max_dur=100)
        item.durability = 75
        self.assertIn("Good", item.get_condition_label())

    def test_worn_at_74_pct(self):
        item = _make_wearable("Helm", self.char1, max_dur=100)
        item.durability = 74
        self.assertIn("Worn", item.get_condition_label())

    def test_worn_at_50_pct(self):
        item = _make_wearable("Helm", self.char1, max_dur=100)
        item.durability = 50
        self.assertIn("Worn", item.get_condition_label())

    def test_damaged_at_49_pct(self):
        item = _make_wearable("Helm", self.char1, max_dur=100)
        item.durability = 49
        self.assertIn("Damaged", item.get_condition_label())

    def test_damaged_at_25_pct(self):
        item = _make_wearable("Helm", self.char1, max_dur=100)
        item.durability = 25
        self.assertIn("Damaged", item.get_condition_label())

    def test_critical_at_24_pct(self):
        item = _make_wearable("Helm", self.char1, max_dur=100)
        item.durability = 24
        self.assertIn("Critical", item.get_condition_label())

    def test_critical_at_1_pct(self):
        item = _make_wearable("Helm", self.char1, max_dur=100)
        item.durability = 1
        self.assertIn("Critical", item.get_condition_label())

    def test_unbreakable_empty_string(self):
        item = _make_wearable("Helm", self.char1, max_dur=0)
        self.assertEqual(item.get_condition_label(), "")
