"""
Tests for CarryingCapacityMixin — weight tracking, capacity checks,
at_object_receive/at_object_leave hooks, fungible weight recalculation,
and the recalculate_weight() safety net.

evennia test --settings settings tests.typeclass_tests.test_carrying_capacity
"""

from django.conf import settings

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _make_item(key, weight=0.0, token_id=None):
    """Create a BaseNFTItem with a given weight. Does NOT place it anywhere."""
    obj = create.create_object(
        "typeclasses.items.base_nft_item.BaseNFTItem",
        key=key,
        nohome=True,
    )
    obj.weight = weight
    if token_id is not None:
        obj.token_id = token_id
    return obj


class TestCarryingCapacityInit(EvenniaTest):
    """Test initialization and default values."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_default_capacity(self):
        """New character should have 50 kg capacity."""
        self.assertEqual(self.char1.max_carrying_capacity_kg, 50)

    def test_default_weight_zero(self):
        """New character should have zero weight carried."""
        self.assertAlmostEqual(self.char1.current_weight_carried, 0.0)
        self.assertAlmostEqual(self.char1.items_weight, 0.0)
        self.assertAlmostEqual(self.char1.current_weight_fungibles, 0.0)

    def test_current_weight_carried_is_property(self):
        """current_weight_carried should be the sum of nfts + fungibles."""
        self.char1.items_weight = 10.0
        self.char1.current_weight_fungibles = 5.0
        self.assertAlmostEqual(self.char1.current_weight_carried, 15.0)


class TestCapacityQueries(EvenniaTest):
    """Test can_carry, get_remaining_capacity, etc."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Neutralise STR modifier so these tests focus on capacity logic
        self.char1.strength = 10

    def test_can_carry_within_limit(self):
        """can_carry should return True when within capacity."""
        self.char1.max_carrying_capacity_kg = 50
        self.char1.items_weight = 10.0
        self.assertTrue(self.char1.can_carry(30.0))

    def test_can_carry_at_limit(self):
        """can_carry should return True at exactly the limit."""
        self.char1.max_carrying_capacity_kg = 50
        self.char1.items_weight = 40.0
        self.assertTrue(self.char1.can_carry(10.0))

    def test_can_carry_over_limit(self):
        """can_carry should return False when over capacity."""
        self.char1.max_carrying_capacity_kg = 50
        self.char1.items_weight = 40.0
        self.assertFalse(self.char1.can_carry(11.0))

    def test_remaining_capacity(self):
        """get_remaining_capacity should return max - current."""
        self.char1.max_carrying_capacity_kg = 50
        self.char1.items_weight = 20.0
        self.assertAlmostEqual(self.char1.get_remaining_capacity(), 30.0)

    def test_remaining_capacity_clamped(self):
        """get_remaining_capacity should never go below 0."""
        self.char1.max_carrying_capacity_kg = 50
        self.char1.items_weight = 60.0
        self.assertAlmostEqual(self.char1.get_remaining_capacity(), 0.0)

    def test_get_current_weight(self):
        """get_current_weight should return current_weight_carried."""
        self.char1.items_weight = 12.5
        self.char1.current_weight_fungibles = 3.5
        self.assertAlmostEqual(self.char1.get_current_weight(), 16.0)


class TestNFTWeightTracking(EvenniaTest):
    """Test at_object_receive/at_object_leave hooks for NFT weight."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.items_weight = 0.0
        self.char1.current_weight_fungibles = 0.0

    def test_receive_adds_weight(self):
        """Moving an item to character should add its weight."""
        item = _make_item("Sword", weight=3.0)
        item.move_to(self.char1, quiet=True)
        self.assertAlmostEqual(self.char1.items_weight, 3.0)

    def test_leave_removes_weight(self):
        """Moving an item away from character should remove its weight."""
        item = _make_item("Sword", weight=3.0)
        item.move_to(self.char1, quiet=True)
        self.assertAlmostEqual(self.char1.items_weight, 3.0)
        item.move_to(self.room1, quiet=True)
        self.assertAlmostEqual(self.char1.items_weight, 0.0)

    def test_multiple_items(self):
        """Multiple items should accumulate weight."""
        item1 = _make_item("Sword", weight=3.0)
        item2 = _make_item("Shield", weight=5.0)
        item1.move_to(self.char1, quiet=True)
        item2.move_to(self.char1, quiet=True)
        self.assertAlmostEqual(self.char1.items_weight, 8.0)

    def test_zero_weight_item(self):
        """Items with zero weight shouldn't change weight tracking."""
        item = _make_item("Feather", weight=0.0)
        item.move_to(self.char1, quiet=True)
        self.assertAlmostEqual(self.char1.items_weight, 0.0)

    def test_weight_never_negative(self):
        """Weight should never go below 0 even with mismatched tracking."""
        self.char1.items_weight = 1.0
        item = _make_item("Heavy Sword", weight=5.0)
        # Directly set item in contents and force leave
        item.move_to(self.char1, quiet=True)
        # Now nfts weight = 1.0 + 5.0 = 6.0
        self.char1.items_weight = 0.5  # Simulate drift
        item.move_to(self.room1, quiet=True)
        # Should clamp to 0.0, not go to -4.5
        self.assertAlmostEqual(self.char1.items_weight, 0.0)


class TestFungibleWeightTracking(EvenniaTest):
    """Test _at_balance_changed hook for fungible weight."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        self.char1.items_weight = 0.0
        self.char1.current_weight_fungibles = 0.0

    def test_gold_adds_weight(self):
        """Adding gold should update fungible weight."""
        self.char1._add_gold(100)
        expected = 100 * settings.GOLD_WEIGHT_PER_UNIT_KG
        self.assertAlmostEqual(self.char1.current_weight_fungibles, expected)

    def test_gold_removes_weight(self):
        """Removing gold should update fungible weight."""
        self.char1.db.gold = 100
        self.char1._at_balance_changed()  # sync initial weight
        self.char1._remove_gold(50)
        expected = 50 * settings.GOLD_WEIGHT_PER_UNIT_KG
        self.assertAlmostEqual(self.char1.current_weight_fungibles, expected)

    def test_resource_adds_weight(self):
        """Adding a resource should update fungible weight."""
        # resource_id 4 = Iron Ore, weight 1.5 kg
        self.char1._add_resource(4, 10)
        self.assertAlmostEqual(self.char1.current_weight_fungibles, 15.0)

    def test_combined_weight(self):
        """Total weight should include both NFTs and fungibles."""
        item = _make_item("Sword", weight=3.0)
        item.move_to(self.char1, quiet=True)
        self.char1._add_gold(100)  # 100 * 0.01 = 1.0 kg
        self.assertAlmostEqual(self.char1.items_weight, 3.0)
        self.assertAlmostEqual(self.char1.current_weight_fungibles, 1.0)
        self.assertAlmostEqual(self.char1.current_weight_carried, 4.0)


class TestRecalculateWeight(EvenniaTest):
    """Test recalculate_weight() safety net."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_recalculate_from_scratch(self):
        """recalculate_weight should rebuild both components."""
        item1 = _make_item("Sword", weight=3.0)
        item2 = _make_item("Shield", weight=5.0)
        item1.move_to(self.char1, quiet=True)
        item2.move_to(self.char1, quiet=True)
        self.char1.db.gold = 200  # 200 * 0.01 = 2.0 kg
        self.char1.db.resources = {4: 5}  # 5 * 1.5 = 7.5 kg

        # Corrupt the stored weights
        self.char1.items_weight = 999.0
        self.char1.current_weight_fungibles = 999.0

        self.char1.recalculate_weight()
        self.assertAlmostEqual(self.char1.items_weight, 8.0)
        self.assertAlmostEqual(self.char1.current_weight_fungibles, 9.5)

    def test_recalculate_empty(self):
        """recalculate_weight with no items/fungibles should be 0."""
        self.char1.items_weight = 50.0
        self.char1.current_weight_fungibles = 50.0
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        self.char1.recalculate_weight()
        self.assertAlmostEqual(self.char1.items_weight, 0.0)
        self.assertAlmostEqual(self.char1.current_weight_fungibles, 0.0)


class TestEncumbranceDisplay(EvenniaTest):
    """Test get_encumbrance_display."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Neutralise STR modifier so these tests focus on display logic
        self.char1.strength = 10

    def test_display_format(self):
        """Should return 'Carrying: X.X / Y.Y kg'."""
        self.char1.items_weight = 12.5
        self.char1.current_weight_fungibles = 0.0
        self.char1.max_carrying_capacity_kg = 50
        result = self.char1.get_encumbrance_display()
        self.assertIn("Carrying:", result)
        self.assertIn("12.5 / 50.0 kg", result)

    def test_display_empty(self):
        """Should show 0.0 when carrying nothing."""
        self.char1.items_weight = 0.0
        self.char1.current_weight_fungibles = 0.0
        self.char1.max_carrying_capacity_kg = 50
        result = self.char1.get_encumbrance_display()
        self.assertIn("Carrying:", result)
        self.assertIn("0.0 / 50.0 kg", result)


class TestGetTotalFungibleWeight(EvenniaTest):
    """Test FungibleInventoryMixin.get_total_fungible_weight()."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}

    def test_gold_weight(self):
        """Gold weight should use GOLD_WEIGHT_PER_UNIT_KG."""
        self.char1.db.gold = 500
        weight = self.char1.get_total_fungible_weight()
        self.assertAlmostEqual(weight, 500 * settings.GOLD_WEIGHT_PER_UNIT_KG)

    def test_resource_weight(self):
        """Resource weight should use weight_per_unit_kg from cache."""
        # Iron Ore (id=4) = 1.5 kg per unit
        self.char1.db.resources = {4: 10}
        weight = self.char1.get_total_fungible_weight()
        self.assertAlmostEqual(weight, 15.0)

    def test_mixed_weight(self):
        """Combined gold and resource weight."""
        self.char1.db.gold = 100  # 100 * 0.01 = 1.0 kg
        self.char1.db.resources = {1: 20, 4: 5}  # 20*0.5 + 5*1.5 = 10.0 + 7.5
        weight = self.char1.get_total_fungible_weight()
        self.assertAlmostEqual(weight, 18.5)

    def test_empty_weight(self):
        """No fungibles should return 0."""
        weight = self.char1.get_total_fungible_weight()
        self.assertAlmostEqual(weight, 0.0)


class TestIsEncumbered(EvenniaTest):
    """Test the is_encumbered property."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.strength = 10  # neutralise STR modifier

    def test_not_encumbered_within_limit(self):
        """Under capacity → not encumbered."""
        self.char1.max_carrying_capacity_kg = 50
        self.char1.items_weight = 30.0
        self.assertFalse(self.char1.is_encumbered)

    def test_not_encumbered_at_exact_limit(self):
        """At exactly capacity → not encumbered."""
        self.char1.max_carrying_capacity_kg = 50
        self.char1.items_weight = 50.0
        self.assertFalse(self.char1.is_encumbered)

    def test_encumbered_over_limit(self):
        """Over capacity → encumbered."""
        self.char1.max_carrying_capacity_kg = 50
        self.char1.items_weight = 51.0
        self.assertTrue(self.char1.is_encumbered)


class TestNuclearRecalculateWithContainers(EvenniaTest):
    """Test nuclear item weight recalculate with containers."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.items_weight = 0.0
        self.char1.current_weight_fungibles = 0.0

    def _make_container(self, key="Backpack", weight=1.0, transfer_weight=True):
        """Create a container item."""
        obj = create.create_object(
            "typeclasses.items.containers.container_nft_item.ContainerNFTItem",
            key=key,
            nohome=True,
        )
        obj.weight = weight
        obj.transfer_weight = transfer_weight
        obj.max_container_capacity_kg = 50.0
        return obj

    def test_container_contents_weight_included(self):
        """Container with transfer_weight=True should include contents weight."""
        container = self._make_container()
        container.move_to(self.char1, quiet=True)
        self.assertAlmostEqual(self.char1.items_weight, 1.0)

        item = _make_item("Sword", weight=3.0)
        item.move_to(container, quiet=True)
        # container (1.0) + contents (3.0) = 4.0
        self.assertAlmostEqual(self.char1.items_weight, 4.0)

    def test_container_no_transfer_weight(self):
        """Container with transfer_weight=False should NOT include contents."""
        container = self._make_container(transfer_weight=False)
        container.move_to(self.char1, quiet=True)
        self.assertAlmostEqual(self.char1.items_weight, 1.0)

        item = _make_item("Hay", weight=5.0)
        item.move_to(container, quiet=True)
        # Only container's own weight, not contents
        self.assertAlmostEqual(self.char1.items_weight, 1.0)

    def test_move_item_into_carried_container(self):
        """Moving item from inventory into a carried backpack: net weight unchanged."""
        container = self._make_container()
        container.move_to(self.char1, quiet=True)
        item = _make_item("Sword", weight=3.0)
        item.move_to(self.char1, quiet=True)
        # container (1.0) + sword (3.0) = 4.0
        self.assertAlmostEqual(self.char1.items_weight, 4.0)

        # Move sword into backpack — net weight should stay 4.0
        item.move_to(container, quiet=True)
        self.assertAlmostEqual(self.char1.items_weight, 4.0)

    def test_take_item_from_carried_container(self):
        """Taking item from carried backpack to inventory: net weight unchanged."""
        container = self._make_container()
        container.move_to(self.char1, quiet=True)
        item = _make_item("Sword", weight=3.0)
        item.move_to(container, quiet=True)
        self.assertAlmostEqual(self.char1.items_weight, 4.0)

        # Take sword out of backpack into inventory
        item.move_to(self.char1, quiet=True)
        self.assertAlmostEqual(self.char1.items_weight, 4.0)

    def test_pick_up_container_with_items(self):
        """Picking up a backpack with items inside should include all weight."""
        container = self._make_container()
        container.move_to(self.room1, quiet=True)
        item = _make_item("Sword", weight=3.0)
        item.move_to(container, quiet=True)

        # Pick up the backpack
        container.move_to(self.char1, quiet=True)
        # container (1.0) + contents (3.0) = 4.0
        self.assertAlmostEqual(self.char1.items_weight, 4.0)

    def test_drop_container_with_items(self):
        """Dropping a backpack with items should remove all weight."""
        container = self._make_container()
        container.move_to(self.char1, quiet=True)
        item = _make_item("Sword", weight=3.0)
        item.move_to(container, quiet=True)
        self.assertAlmostEqual(self.char1.items_weight, 4.0)

        container.move_to(self.room1, quiet=True)
        self.assertAlmostEqual(self.char1.items_weight, 0.0)

    def test_recalculate_corrects_after_delete(self):
        """item.delete() leaves stale weight; recalculate_weight fixes it."""
        item = _make_item("Sword", weight=3.0)
        item.move_to(self.char1, quiet=True)
        self.assertAlmostEqual(self.char1.items_weight, 3.0)

        item.delete()
        # Weight may be stale after delete — recalculate fixes it
        self.char1.recalculate_weight()
        self.assertAlmostEqual(self.char1.items_weight, 0.0)

    def test_recalculate_includes_container_contents(self):
        """recalculate_weight should include container contents weight."""
        container = self._make_container()
        container.move_to(self.char1, quiet=True)
        item = _make_item("Sword", weight=3.0)
        item.move_to(container, quiet=True)

        # Corrupt stored weight
        self.char1.items_weight = 999.0

        self.char1.recalculate_weight()
        # container (1.0) + contents (3.0) = 4.0
        self.assertAlmostEqual(self.char1.items_weight, 4.0)
