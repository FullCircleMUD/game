"""
Tests for worn item guards — drop, give, deposit, and junk should all
reject worn/equipped items with "You must remove <item> first."

evennia test --settings settings tests.command_tests.test_worn_item_guards
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from enums.wearslot import HumanoidWearSlot
from commands.all_char_cmds.cmd_override_drop import CmdDrop
from commands.all_char_cmds.cmd_override_give import CmdGive
from commands.all_char_cmds.cmd_junk import CmdJunk
from commands.room_specific_cmds.bank.cmd_deposit import CmdDeposit


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
WALLET_B = "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"


def _make_wearable(key, wearslot_value, location=None, token_id=None):
    """Create a test WearableNFTItem."""
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
    """Create a test WeaponNFTItem."""
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


# ================================================================== #
#  Drop guards
# ================================================================== #

class TestDropWornGuard(EvenniaCommandTest):
    """Drop command should reject worn items."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True

    def test_drop_worn_by_name_rejected(self):
        """Dropping a worn item by name should give a 'remove first' message.

        Name-based inventory lookup excludes worn items, so a secondary
        lookup against equipped items provides the useful error.
        """
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.wear(helmet)
        result = self.call(CmdDrop(), "Iron Helmet")
        self.assertIn("You'll have to remove Iron Helmet first", result)
        # Item should still be on the character
        self.assertIn(helmet, self.char1.contents)
        self.assertTrue(self.char1.is_worn(helmet))

    def test_drop_worn_by_token_id_rejected(self):
        """Dropping a worn item by dbref should be rejected."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1, token_id=100)
        self.char1.wear(helmet)
        result = self.call(CmdDrop(), f"#{helmet.id}")
        self.assertIn("You must remove Iron Helmet first", result)

    def test_drop_unworn_item_succeeds(self):
        """Dropping an unworn item should work normally."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1, token_id=101)
        result = self.call(CmdDrop(), "Iron Helmet")
        self.assertNotIn("must remove", result)

    def test_drop_wielded_weapon_rejected(self):
        """Dropping a wielded weapon should give a 'remove first' message."""
        sword = _make_weapon("Iron Longsword", self.char1)
        self.char1.wear(sword)
        result = self.call(CmdDrop(), "Iron Longsword")
        self.assertIn("You'll have to remove Iron Longsword first", result)
        self.assertIn(sword, self.char1.contents)
        self.assertTrue(self.char1.is_worn(sword))

    def test_drop_duplicate_name_skips_worn(self):
        """Two items with same name — worn one excluded, unworn one dropped."""
        wielded = _make_weapon("Training Longsword", self.char1, token_id=150)
        unworn = _make_weapon("Training Longsword", self.char1, token_id=151)
        self.char1.wear(wielded)
        # Should drop the unworn one without disambiguation
        result = self.call(CmdDrop(), "Training Longsword")
        self.assertNotIn("must remove", result)
        self.assertNotIn("more than one", result)
        # Wielded stays, unworn dropped
        self.assertIn(wielded, self.char1.contents)
        self.assertTrue(self.char1.is_worn(wielded))
        self.assertNotIn(unworn, self.char1.contents)

    @patch("commands.all_char_cmds.cmd_override_drop.CmdDrop.msg")
    def test_drop_all_skips_worn_items(self, mock_msg):
        """Drop all should skip worn items and report them."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1, token_id=102)
        unworn = _make_wearable("Leather Belt", HumanoidWearSlot.WAIST.value, self.char1, token_id=103)
        self.char1.wear(helmet)
        # Use yield-based call with "y" confirmation
        result = self.call(CmdDrop(), "all", inputs=["y"])
        # Helmet should still be on character (worn, skipped)
        self.assertIn(helmet, self.char1.contents)
        self.assertTrue(self.char1.is_worn(helmet))
        # Belt should have been dropped
        self.assertNotIn(unworn, self.char1.contents)


# ================================================================== #
#  Give guards
# ================================================================== #

class TestGiveWornGuard(EvenniaCommandTest):
    """Give command should reject worn items."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account2.attributes.add("wallet_address", WALLET_B)
        self.room1.always_lit = True
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        self.char2.db.gold = 0
        self.char2.db.resources = {}

    def test_give_worn_by_name_rejected(self):
        """Giving a worn item by name should give a 'remove first' message."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.wear(helmet)
        result = self.call(CmdGive(), f"Iron Helmet to {self.char2.key}")
        self.assertIn("You'll have to remove Iron Helmet first", result)
        self.assertIn(helmet, self.char1.contents)
        self.assertTrue(self.char1.is_worn(helmet))

    def test_give_worn_by_token_id_rejected(self):
        """Giving a worn item by dbref should be rejected."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1, token_id=104)
        self.char1.wear(helmet)
        result = self.call(CmdGive(), f"#{helmet.id} to {self.char2.key}")
        self.assertIn("You must remove Iron Helmet first", result)

    def test_give_unworn_item_succeeds(self):
        """Giving an unworn item should work normally."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1, token_id=105)
        result = self.call(CmdGive(), f"Iron Helmet to {self.char2.key}")
        self.assertNotIn("must remove", result)


# ================================================================== #
#  Junk guards
# ================================================================== #

class TestJunkWornGuard(EvenniaCommandTest):
    """Junk command should reject worn items."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_junk_worn_nft_rejected(self):
        """Junking a worn NFT should be rejected."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1, token_id=106)
        self.char1.wear(helmet)
        result = self.call(CmdJunk(), f"#{helmet.id}")
        self.assertIn("You must remove Iron Helmet first", result)
        self.assertIn(helmet, self.char1.contents)

    def test_junk_unworn_nft_prompts_confirmation(self):
        """Junking an unworn NFT should proceed past worn guard to confirmation."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1, token_id=107)
        result = self.call(CmdJunk(), f"#{helmet.id}", inputs=["n"])
        # Should get past the worn guard to the Y/N prompt (answered "n")
        self.assertNotIn("must remove", result)
        self.assertIn("Junk cancelled", result)


# ================================================================== #
#  Deposit guards
# ================================================================== #

class TestDepositWornGuard(EvenniaCommandTest):
    """Deposit command should reject worn items."""

    room_typeclass = "typeclasses.terrain.rooms.room_bank.RoomBank"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_deposit_worn_by_token_id_rejected(self):
        """Depositing a worn item by dbref should be rejected."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1, token_id=108)
        self.char1.wear(helmet)
        result = self.call(CmdDeposit(), f"#{helmet.id}")
        self.assertIn("You must remove Iron Helmet first", result)
        self.assertIn(helmet, self.char1.contents)

    def test_deposit_worn_by_name_rejected(self):
        """Depositing a worn item by name should be rejected."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1, token_id=109)
        self.char1.wear(helmet)
        result = self.call(CmdDeposit(), "Iron Helmet")
        self.assertIn("You must remove Iron Helmet first", result)

    def test_deposit_unworn_item_succeeds(self):
        """Depositing an unworn item should work normally."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1, token_id=110)
        result = self.call(CmdDeposit(), "Iron Helmet")
        self.assertNotIn("must remove", result)
