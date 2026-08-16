"""
Tests for the overridden inventory command — verifies carried items
(excluding worn), fungibles display, id mode, condition labels,
and encumbrance.

Note: EvenniaCommandTest.call() checks that msg STARTS WITH the expected
string, not substring match.

evennia test --settings settings tests.command_tests.test_cmd_inventory
"""

from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_override_inventory import CmdInventory


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _make_item(key, weight=0.0, location=None, token_id=None):
    """Create a BaseNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.base_nft_item.BaseNFTItem",
        key=key,
        nohome=True,
    )
    obj.weight = weight
    if token_id is not None:
        obj.token_id = token_id
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _make_wearable(key, location=None, token_id=None, durability=100, max_durability=100):
    """Create a WearableNFTItem with durability for testing."""
    obj = create.create_object(
        "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
        key=key,
        nohome=True,
    )
    obj.at_wear = MagicMock()
    obj.at_remove = MagicMock()
    obj.max_durability = max_durability
    obj.durability = durability
    if token_id is not None:
        obj.token_id = token_id
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _make_weapon(key, location=None, token_id=None):
    """Create a WeaponNFTItem with mocked hooks."""
    obj = create.create_object(
        "typeclasses.items.weapons.weapon_nft_item.WeaponNFTItem",
        key=key,
        nohome=True,
    )
    obj.at_wear = MagicMock()
    obj.at_wield = MagicMock()
    obj.at_remove = MagicMock()
    if token_id is not None:
        obj.token_id = token_id
    if location:
        obj.move_to(location, quiet=True)
    return obj


class TestInventoryEmpty(EvenniaCommandTest):
    """Test inventory when carrying nothing."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}

    def test_empty_inventory(self):
        """Empty inventory should say 'not carrying anything'."""
        result = self.call(CmdInventory(), "")
        self.assertIn("You are not carrying anything.", result)


class TestInventoryItems(EvenniaCommandTest):
    """Test inventory with carried items."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}

    def test_shows_carried_items(self):
        """Inventory should list items by name."""
        _make_item("Sword", location=self.char1)
        result = self.call(CmdInventory(), "")
        self.assertIn("Inventory:", result)
        self.assertIn("Sword", result)

    def test_excludes_worn_items(self):
        """Wielded items should not appear in carried list."""
        sword = _make_weapon("Training Longsword", location=self.char1)
        self.char1.wear(sword)
        # With only the sword (now wielded), should show empty
        result = self.call(CmdInventory(), "")
        self.assertIn("You are not carrying anything.", result)

    def test_mixed_carried_and_worn(self):
        """Should show only non-worn items."""
        sword = _make_weapon("Training Longsword", location=self.char1)
        _make_item("Bread Loaf", location=self.char1)
        self.char1.wear(sword)
        # Should show Bread Loaf but not the sword
        result = self.call(CmdInventory(), "")
        self.assertIn("Bread Loaf", result)
        self.assertNotIn("Training Longsword", result)

    def test_multiple_same_items_stacked_no_durability(self):
        """Items without durability should stack with a count."""
        _make_item("Copper Earring", location=self.char1)
        _make_item("Copper Earring", location=self.char1)
        result = self.call(CmdInventory(), "")
        self.assertIn("Copper Earring (2)", result)
        # Name should appear only once (stacked)
        self.assertEqual(result.count("Copper Earring"), 1)

    def test_multiple_same_items_individual_with_durability(self):
        """Items with durability should each appear on their own line."""
        _make_wearable("Iron Helmet", location=self.char1, durability=100, max_durability=100)
        _make_wearable("Iron Helmet", location=self.char1, durability=50, max_durability=100)
        result = self.call(CmdInventory(), "")
        # Should appear twice, not stacked
        self.assertEqual(result.count("Iron Helmet"), 2)


class TestInventoryFungibles(EvenniaCommandTest):
    """Test fungibles display in inventory."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}

    def test_shows_gold(self):
        """Inventory should show gold when > 0."""
        self.char1.db.gold = 150
        result = self.call(CmdInventory(), "")
        self.assertIn("Gold:", result)
        self.assertIn("150", result)

    def test_no_gold_when_zero(self):
        """Inventory should not show gold line when 0."""
        result = self.call(CmdInventory(), "")
        self.assertNotIn("Gold:", result)

    def test_shows_resources_inline(self):
        """Resources should appear in the items list, not under a header."""
        self.char1.db.resources = {1: 20}  # Wheat
        result = self.call(CmdInventory(), "")
        self.assertIn("Wheat (20)", result)
        self.assertNotIn("Resources:", result)

    def test_single_resource_no_count(self):
        """A resource with amount 1 should not show (1)."""
        self.char1.db.resources = {1: 1}  # Wheat
        result = self.call(CmdInventory(), "")
        self.assertIn("Wheat", result)
        self.assertNotIn("(1)", result)

    def test_no_resources_when_empty(self):
        """Inventory should not show resources when none held."""
        result = self.call(CmdInventory(), "")
        self.assertNotIn("Wheat", result)

    def test_resources_with_items(self):
        """Resources and items should both appear under 'carrying'."""
        _make_item("Sword", location=self.char1)
        self.char1.db.resources = {3: 5}  # Bread
        result = self.call(CmdInventory(), "")
        self.assertIn("Inventory:", result)
        self.assertIn("Sword", result)
        self.assertIn("Bread (5)", result)


class TestInventoryIdMode(EvenniaCommandTest):
    """Test inventory id mode — shows NFT token IDs and resource IDs."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}

    def test_id_shows_nft_item_ids(self):
        """'inventory id' should show [#<id>] for each item."""
        item = _make_item("Copper Necklace", location=self.char1, token_id=76)
        result = self.call(CmdInventory(), "id")
        self.assertIn(f"[#{item.id}]", result)

    def test_id_shows_stacked_item_ids(self):
        """Stacked items should show all item IDs on one line."""
        item1 = _make_item("Copper Earring", location=self.char1, token_id=23)
        item2 = _make_item("Copper Earring", location=self.char1, token_id=76)
        result = self.call(CmdInventory(), "id")
        self.assertIn(f"#{item1.id}", result)
        self.assertIn(f"#{item2.id}", result)

    def test_id_shows_individual_item_ids(self):
        """Items with durability should show item IDs individually."""
        item1 = _make_wearable("Iron Helmet", location=self.char1, token_id=10, durability=100, max_durability=100)
        item2 = _make_wearable("Iron Helmet", location=self.char1, token_id=11, durability=50, max_durability=100)
        result = self.call(CmdInventory(), "id")
        self.assertIn(f"[#{item1.id}]", result)
        self.assertIn(f"[#{item2.id}]", result)

    def test_id_shows_resource_ids(self):
        """'inventory id' should show [Resource #X] for resources."""
        self.char1.db.resources = {3: 5}  # Bread
        result = self.call(CmdInventory(), "id")
        self.assertIn("Bread (5)", result)
        self.assertIn("[Resource #3]", result)

    def test_default_mode_no_ids(self):
        """Default inventory should NOT show token IDs."""
        _make_item("Sword", location=self.char1, token_id=42)
        result = self.call(CmdInventory(), "")
        self.assertNotIn("[NFT #42]", result)
        self.assertNotIn("[Resource", result)


class TestInventoryConditionLabels(EvenniaCommandTest):
    """Test durability condition labels in inventory display."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}

    def test_pristine_item(self):
        """Full durability item should show (Pristine)."""
        _make_wearable("Iron Helmet", location=self.char1, durability=100, max_durability=100)
        result = self.call(CmdInventory(), "")
        self.assertIn("Iron Helmet", result)
        self.assertIn("Pristine", result)

    def test_damaged_item(self):
        """Item at 25% should show (Damaged)."""
        _make_wearable("Iron Helmet", location=self.char1, durability=25, max_durability=100)
        result = self.call(CmdInventory(), "")
        self.assertIn("Damaged", result)

    def test_critical_item(self):
        """Item below 25% should show (Critical)."""
        _make_wearable("Iron Helmet", location=self.char1, durability=10, max_durability=100)
        result = self.call(CmdInventory(), "")
        self.assertIn("Critical", result)

    def test_base_nft_no_condition(self):
        """BaseNFTItem (no DurabilityMixin) should not show condition."""
        _make_item("Mystery Orb", location=self.char1)
        result = self.call(CmdInventory(), "")
        self.assertIn("Mystery Orb", result)
        self.assertNotIn("Pristine", result)
        self.assertNotIn("Good", result)

    def test_different_conditions_on_same_type(self):
        """Two earrings with different durability show different labels."""
        _make_wearable("Copper Earring", location=self.char1, durability=100, max_durability=100)
        _make_wearable("Copper Earring", location=self.char1, durability=30, max_durability=100)
        result = self.call(CmdInventory(), "")
        self.assertIn("Pristine", result)
        self.assertIn("Damaged", result)


class TestInventoryEncumbrance(EvenniaCommandTest):
    """Test encumbrance display in inventory."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}

    def test_shows_encumbrance(self):
        """Inventory should show carrying weight at the bottom."""
        result = self.call(CmdInventory(), "")
        self.assertIn("Carrying:", result)
        self.assertIn("kg", result)

    def test_encumbrance_with_items(self):
        """Encumbrance should reflect item weight."""
        _make_item("Sword", weight=3.0, location=self.char1)
        result = self.call(CmdInventory(), "")
        self.assertIn("3.0", result)


class TestInventoryWithoutSight(EvenniaCommandTest):
    """A pack gone through by feel: you know how much, not what."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        self.room1.always_lit = True

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False

    def test_a_sighted_character_reads_their_pack(self):
        _make_item("Sword", location=self.char1)
        result = self.call(CmdInventory(), "")
        self.assertIn("Sword", result)
        self.assertNotIn("Something", result)

    def test_darkness_leaves_only_somethings(self):
        _make_item("Sword", location=self.char1)
        result = self.call(CmdInventory(), "")
        self._darken()
        result = self.call(CmdInventory(), "")
        self.assertIn("Something", result)
        self.assertNotIn("Sword", result)

    def test_a_blinded_character_cannot_read_their_pack_in_a_lit_room(self):
        """is_dark alone never asked this — a blind character read it fine."""
        from enums.condition import Condition

        _make_item("Sword", location=self.char1)
        self.char1.add_condition(Condition.BLINDED)
        result = self.call(CmdInventory(), "")
        self.assertIn("Something", result)
        self.assertNotIn("Sword", result)

    def test_darkvision_reads_the_pack_in_the_dark(self):
        from enums.condition import Condition

        _make_item("Sword", location=self.char1)
        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        result = self.call(CmdInventory(), "")
        self.assertIn("Sword", result)

    def test_blindness_beats_darkvision(self):
        from enums.condition import Condition

        _make_item("Sword", location=self.char1)
        self.char1.add_condition(Condition.DARKVISION)
        self.char1.add_condition(Condition.BLINDED)
        result = self.call(CmdInventory(), "")
        self.assertIn("Something", result)
        self.assertNotIn("Sword", result)

    def test_the_count_survives_even_when_the_names_do_not(self):
        for name in ("Sword", "Shield", "Rope"):
            _make_item(name, location=self.char1)
        from enums.condition import Condition

        self.char1.add_condition(Condition.BLINDED)
        result = self.call(CmdInventory(), "")
        self.assertEqual(result.count("Something"), 3)

    def test_gold_is_hard_to_see(self):
        from enums.condition import Condition

        self.char1.db.gold = 50
        self.char1.add_condition(Condition.BLINDED)
        result = self.call(CmdInventory(), "")
        self.assertIn("hard to see", result)
        self.assertNotIn("50", result)

    def test_a_concealed_item_reads_as_something_to_a_sighted_owner(self):
        """Concealment masks per item; sight suppresses the whole list."""
        _make_item("Sword", location=self.char1)
        hidden = _make_item("Dagger", location=self.char1)
        hidden.is_hidden = True
        result = self.call(CmdInventory(), "")
        self.assertIn("Sword", result)
        self.assertIn("Something", result)
        self.assertNotIn("Dagger", result)
