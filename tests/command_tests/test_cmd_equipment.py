"""
Tests for wear, wield, hold, remove, and equipment commands.

Uses EvenniaCommandTest with test items created as real item typeclasses
with mocked at_wear/at_remove/at_wield/at_hold hooks (avoids
NotImplementedError from abstract base classes).

Note: EvenniaCommandTest.call() checks that msg STARTS WITH the expected
string, not substring match.

evennia test --settings settings tests.command_tests.test_cmd_equipment
"""

from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from enums.wearslot import HumanoidWearSlot
from commands.all_char_cmds.cmd_wear import CmdWear
from commands.all_char_cmds.cmd_wield import CmdWield
from commands.all_char_cmds.cmd_hold import CmdHold
from commands.all_char_cmds.cmd_remove import CmdRemove
from commands.all_char_cmds.cmd_equipment import CmdEquipment


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _make_wearable(key, wearslot_value, location=None, token_id=None):
    """Create a test WearableNFTItem with mocked hooks."""
    obj = create.create_object(
        "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
        key=key,
        nohome=True,
    )
    obj.db.wearslot = wearslot_value
    obj.at_wear = MagicMock()
    obj.at_remove = MagicMock()
    if token_id is not None:
        obj.token_id = token_id
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _make_weapon(key, location=None, token_id=None):
    """Create a test WeaponNFTItem with mocked hooks."""
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


def _make_holdable(key, location=None, token_id=None):
    """Create a test HoldableNFTItem with mocked hooks."""
    obj = create.create_object(
        "typeclasses.items.holdables.holdable_nft_item.HoldableNFTItem",
        key=key,
        nohome=True,
    )
    obj.at_wear = MagicMock()
    obj.at_hold = MagicMock()
    obj.at_remove = MagicMock()
    if token_id is not None:
        obj.token_id = token_id
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _make_plain_item(key, location=None):
    """Create a plain BaseNFTItem with no wearslot."""
    obj = create.create_object(
        "typeclasses.items.base_nft_item.BaseNFTItem",
        key=key,
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


# ================================================================== #
#  Wear Command Tests
# ================================================================== #

class TestCmdWear(EvenniaCommandTest):
    """Test the wear command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_wear_wearable_success(self):
        """Wearing a wearable item should succeed."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.call(CmdWear(), "Iron Helmet", "You wear Iron Helmet")

    def test_wear_weapon_rejected(self):
        """Trying to wear a weapon should suggest 'wield'."""
        _make_weapon("Iron Longsword", self.char1)
        self.call(CmdWear(), "Iron Longsword", "Use 'wield' for weapons.")

    def test_wear_holdable_rejected(self):
        """Trying to wear a holdable should suggest 'hold'."""
        _make_holdable("Iron Shield", self.char1)
        self.call(CmdWear(), "Iron Shield", "Use 'hold' for that.")

    def test_wear_plain_item_rejected(self):
        """Wearing a plain item with no wearslot should fail."""
        _make_plain_item("Glass Bauble", self.char1)
        self.call(CmdWear(), "Glass Bauble", "Glass Bauble is not something that can be worn.")

    def test_wear_already_worn(self):
        """Wearing an already-worn item should fail."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.wear(helmet)
        self.call(CmdWear(), "Iron Helmet", "You must remove Iron Helmet first.")

    def test_wear_slot_occupied(self):
        """Wearing when the slot is already occupied should fail."""
        helmet1 = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        _make_wearable("Steel Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.wear(helmet1)
        self.call(CmdWear(), "Steel Helmet", "Your Head slot is already occupied.")

    def test_wear_no_args(self):
        """Wear with no arguments should show error."""
        self.call(CmdWear(), "", "Wear what?")

    def test_wear_by_token_id(self):
        """Wearing by token ID should work."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1, token_id=7)
        self.call(CmdWear(), "#7", "You wear Iron Helmet")

    def test_wear_by_partial_name(self):
        """Wearing by partial name (substring) should work."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.call(CmdWear(), "helmet", "You wear Iron Helmet")

    def test_wear_excludes_already_worn_from_search(self):
        """With two identical items, one worn, 'wear earring' should find the unworn one."""
        ear1 = _make_wearable("Copper Earring", HumanoidWearSlot.LEFT_EAR.value, self.char1)
        _make_wearable("Copper Earring", HumanoidWearSlot.RIGHT_EAR.value, self.char1)
        self.char1.wear(ear1)
        # Should not get ambiguity error — worn earring excluded from search
        self.call(CmdWear(), "earring", "You wear Copper Earring")

    def test_wear_all_matches_worn_shows_message(self):
        """If every match is already worn, show 'must remove first'."""
        ear1 = _make_wearable("Copper Earring", HumanoidWearSlot.LEFT_EAR.value, self.char1)
        self.char1.wear(ear1)
        self.call(CmdWear(), "earring", "You must remove Copper Earring first.")


# ================================================================== #
#  Wield Command Tests
# ================================================================== #

class TestCmdWield(EvenniaCommandTest):
    """Test the wield command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_wield_weapon_success(self):
        """Wielding a weapon should succeed."""
        _make_weapon("Iron Longsword", self.char1)
        self.call(CmdWield(), "Iron Longsword", "You wear Iron Longsword")

    def test_wield_non_weapon_rejected(self):
        """Wielding a non-weapon should fail."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.call(CmdWield(), "Iron Helmet", "That's not a weapon.")

    def test_wield_slot_occupied(self):
        """Wielding when WIELD slot is occupied should fail."""
        sword1 = _make_weapon("Iron Longsword", self.char1)
        _make_weapon("Steel Longsword", self.char1)
        self.char1.wear(sword1)
        self.call(CmdWield(), "Steel Longsword", "Your Wield slot is already occupied.")

    def test_wield_no_args(self):
        """Wield with no arguments should show error."""
        self.call(CmdWield(), "", "Wield what?")


# ================================================================== #
#  Hold Command Tests
# ================================================================== #

class TestCmdHold(EvenniaCommandTest):
    """Test the hold command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_hold_holdable_success(self):
        """Holding a holdable item should succeed."""
        _make_holdable("Iron Shield", self.char1)
        self.call(CmdHold(), "Iron Shield", "You wear Iron Shield")

    def test_hold_non_holdable_rejected(self):
        """Holding a non-holdable should fail."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.call(CmdHold(), "Iron Helmet", "That's not something you can hold.")

    def test_hold_slot_occupied(self):
        """Holding when HOLD slot is occupied should fail."""
        shield1 = _make_holdable("Iron Shield", self.char1)
        _make_holdable("Wooden Shield", self.char1)
        self.char1.wear(shield1)
        self.call(CmdHold(), "Wooden Shield", "Your Hold slot is already occupied.")

    def test_hold_no_args(self):
        """Hold with no arguments should show error."""
        self.call(CmdHold(), "", "Hold what?")


# ================================================================== #
#  Remove Command Tests
# ================================================================== #

class TestCmdRemove(EvenniaCommandTest):
    """Test the remove command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_remove_worn_item(self):
        """Removing a worn item should succeed."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.wear(helmet)
        self.call(CmdRemove(), "Iron Helmet", "You remove Iron Helmet")

    def test_remove_not_worn(self):
        """Removing an item that isn't worn should fail."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.call(CmdRemove(), "Iron Helmet", "You are not wearing that.")

    def test_remove_weapon(self):
        """Removing a wielded weapon should work."""
        sword = _make_weapon("Iron Longsword", self.char1)
        self.char1.wear(sword)
        self.call(CmdRemove(), "Iron Longsword", "You remove Iron Longsword")

    def test_remove_by_partial_name(self):
        """Removing by partial name should work via substring matching."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.wear(helmet)
        self.call(CmdRemove(), "helmet", "You remove Iron Helmet")

    def test_remove_only_matches_worn_items(self):
        """With two identical items, one worn, 'remove earring' should find the worn one."""
        ear1 = _make_wearable("Copper Earring", HumanoidWearSlot.LEFT_EAR.value, self.char1)
        _make_wearable("Copper Earring", HumanoidWearSlot.RIGHT_EAR.value, self.char1)
        self.char1.wear(ear1)
        # Should not get ambiguity error — only worn earring matches
        self.call(CmdRemove(), "earring", "You remove Copper Earring")

    def test_remove_no_worn_match(self):
        """Removing an item when no worn match exists should fail."""
        _make_wearable("Copper Earring", HumanoidWearSlot.LEFT_EAR.value, self.char1)
        self.call(CmdRemove(), "earring", "You are not wearing that.")

    def test_remove_no_args(self):
        """Remove with no arguments should show error."""
        self.call(CmdRemove(), "", "Remove what?")


# ================================================================== #
#  Equipment Command Tests
# ================================================================== #

class TestCmdEquipment(EvenniaCommandTest):
    """Test the equipment display command."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_equipment_shows_header(self):
        """Equipment output should start with the header."""
        result = self.call(CmdEquipment(), "")
        self.assertIn("Equipped Items", result)

    def test_equipment_with_item_shows_header(self):
        """Equipment with worn item should still start with header."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.wear(helmet)
        result = self.call(CmdEquipment(), "")
        self.assertIn("Equipped Items", result)

    def test_equipment_with_item_in_slot(self):
        """Verify worn item appears in the character's wearslots."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.wear(helmet)
        self.assertTrue(self.char1.is_worn(helmet))
        self.assertEqual(self.char1.get_slot("HEAD"), helmet)
