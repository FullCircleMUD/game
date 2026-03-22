"""
Tests for the chardelete command override.

The command uses get_input() callback for confirmation, which is async and
can't be fully tested via EvenniaCommandTest.call(). We test:
  1. Early-return paths (no args, wrong name) via call()
  2. Asset transfer logic directly on character/bank objects

evennia test --settings settings tests.command_tests.test_cmd_chardelete
"""

from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaCommandTest, EvenniaTest
from evennia.utils import create

from commands.account_cmds.cmd_override_chardelete import CmdCharDelete
from commands.room_specific_cmds.bank.cmd_balance import ensure_bank
from enums.wearslot import HumanoidWearSlot
from typeclasses.items.base_nft_item import BaseNFTItem


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _make_nft(key, location=None, token_id=None):
    """Create a test BaseNFTItem."""
    obj = create.create_object(
        "typeclasses.items.base_nft_item.BaseNFTItem",
        key=key,
        nohome=True,
    )
    if token_id is not None:
        obj.token_id = token_id
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _make_wearable(key, wearslot_value, location=None):
    """Create a test WearableNFTItem with mocked hooks."""
    obj = create.create_object(
        "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
        key=key,
        nohome=True,
    )
    obj.db.wearslot = wearslot_value
    obj.at_wear = MagicMock()
    obj.at_remove = MagicMock()
    if location:
        obj.move_to(location, quiet=True)
    return obj


# ================================================================== #
#  Command early-return tests (via EvenniaCommandTest.call())
# ================================================================== #

class TestCmdCharDeleteEarlyReturns(EvenniaCommandTest):
    """Test chardelete early-return paths before get_input callback."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_no_args(self):
        """chardelete with no args shows usage."""
        self.call(
            CmdCharDelete(), "", "Usage: chardelete <charactername>",
            caller=self.account,
        )

    def test_wrong_name(self):
        """chardelete with nonexistent name shows error."""
        self.call(
            CmdCharDelete(), "NoSuchChar",
            "You have no such character to delete.",
            caller=self.account,
        )


# ================================================================== #
#  Asset transfer logic tests (direct, no command)
# ================================================================== #

class TestCharDeleteAssetTransfer(EvenniaTest):
    """
    Test that the transfer logic used by chardelete correctly moves
    all assets from a character to the account bank.
    """

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.bank = ensure_bank(self.account)

    def test_nfts_move_to_bank(self):
        """NFT items should move from character to account bank."""
        item1 = _make_nft("Sword", self.char1, token_id=1)
        item2 = _make_nft("Shield", self.char1, token_id=2)

        # Move all NFTs to bank (same logic as chardelete callback)
        for obj in list(self.char1.contents):
            if isinstance(obj, BaseNFTItem):
                obj.move_to(self.bank, quiet=True, move_type="give")

        self.assertEqual(item1.location, self.bank)
        self.assertEqual(item2.location, self.bank)
        nfts_in_char = [
            o for o in self.char1.contents if isinstance(o, BaseNFTItem)
        ]
        self.assertEqual(len(nfts_in_char), 0)

    def test_gold_transfers_to_bank(self):
        """Gold should transfer from character to account bank."""
        self.char1.receive_gold_from_reserve(500)

        gold_amt = self.char1.get_gold()
        self.char1.transfer_gold_to(self.bank, gold_amt)

        self.assertEqual(self.char1.get_gold(), 0)
        self.assertEqual(self.bank.get_gold(), 500)

    def test_resources_transfer_to_bank(self):
        """Resources should transfer from character to account bank."""
        self.char1.receive_resource_from_reserve(1, 100)  # wheat
        self.char1.receive_resource_from_reserve(4, 50)   # iron ore

        for rid, amt in list(self.char1.get_all_resources().items()):
            if amt > 0:
                self.char1.transfer_resource_to(self.bank, rid, amt)

        self.assertEqual(self.char1.get_resource(1), 0)
        self.assertEqual(self.char1.get_resource(4), 0)
        self.assertEqual(self.bank.get_resource(1), 100)
        self.assertEqual(self.bank.get_resource(4), 50)

    def test_worn_equipment_removed_before_transfer(self):
        """Worn equipment should be unequipped before moving to bank."""
        helmet = _make_wearable(
            "Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        self.assertTrue(self.char1.is_worn(helmet))

        # Remove all worn (same logic as chardelete callback)
        for slot, item in list(self.char1.get_all_worn().items()):
            self.char1.remove(item)

        self.assertFalse(self.char1.is_worn(helmet))

        # Now move to bank
        for obj in list(self.char1.contents):
            if isinstance(obj, BaseNFTItem):
                obj.move_to(self.bank, quiet=True, move_type="give")

        self.assertEqual(helmet.location, self.bank)

    def test_empty_character_passes_delete_check(self):
        """Character with no assets should pass at_object_delete check."""
        self.assertTrue(self.char1.at_object_delete())

    def test_character_with_assets_blocks_delete(self):
        """Character with assets should block at_object_delete."""
        _make_nft("Sword", self.char1, token_id=1)
        self.assertFalse(self.char1.at_object_delete())

    def test_full_transfer_then_delete_check(self):
        """After full transfer, character should pass delete check."""
        _make_nft("Sword", self.char1, token_id=1)
        self.char1.receive_gold_from_reserve(100)
        self.char1.receive_resource_from_reserve(1, 50)

        # Should block before transfer
        self.assertFalse(self.char1.at_object_delete())

        # Transfer everything
        for obj in list(self.char1.contents):
            if isinstance(obj, BaseNFTItem):
                obj.move_to(self.bank, quiet=True, move_type="give")
        self.char1.transfer_gold_to(self.bank, self.char1.get_gold())
        for rid, amt in list(self.char1.get_all_resources().items()):
            if amt > 0:
                self.char1.transfer_resource_to(self.bank, rid, amt)

        # Should pass after transfer
        self.assertTrue(self.char1.at_object_delete())
