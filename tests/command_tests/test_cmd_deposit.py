"""
Tests for CmdDeposit — verifies depositing gold, resources, and NFT items
from character inventory into the AccountBank.
"""

from unittest.mock import patch

from django.conf import settings

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.room_specific_cmds.bank.cmd_deposit import CmdDeposit


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdDepositGold(EvenniaCommandTest):
    """Test depositing gold into the bank."""

    room_typeclass = "typeclasses.terrain.rooms.room_bank.RoomBank"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 100
        self.char1.db.resources = {}
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key=f"bank-{self.account.key}",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        self.bank.db.gold = 0
        self.bank.db.resources = {}
        self.account.db.bank = self.bank

    def test_deposit_no_args(self):
        """deposit with no args should show usage."""
        self.call(CmdDeposit(), "", "Usage:")

    @patch("blockchain.xrpl.services.gold.GoldService.bank")
    def test_deposit_gold_default_one(self, mock_bank):
        """deposit gold should deposit 1 by default."""
        self.call(CmdDeposit(), "gold", "You deposit 1")
        self.assertEqual(self.char1.get_gold(), 99)
        self.assertEqual(self.bank.get_gold(), 1)

    @patch("blockchain.xrpl.services.gold.GoldService.bank")
    def test_deposit_gold_amount(self, mock_bank):
        """deposit gold 50 should deposit 50."""
        self.call(CmdDeposit(), "50 gold", "You deposit 50")
        self.assertEqual(self.char1.get_gold(), 50)
        self.assertEqual(self.bank.get_gold(), 50)

    @patch("blockchain.xrpl.services.gold.GoldService.bank")
    def test_deposit_gold_all(self, mock_bank):
        """deposit gold all should deposit everything."""
        self.call(CmdDeposit(), "all gold", "You deposit 100")
        self.assertEqual(self.char1.get_gold(), 0)
        self.assertEqual(self.bank.get_gold(), 100)

    def test_deposit_gold_insufficient(self):
        """deposit more gold than you have should show error."""
        self.char1.db.gold = 10
        self.call(CmdDeposit(), "50 gold", "You only have 10")

    def test_deposit_gold_none(self):
        """deposit gold when you have none should show error."""
        self.char1.db.gold = 0
        self.call(CmdDeposit(), "gold", "You aren't carrying 'gold'")


class TestCmdDepositResource(EvenniaCommandTest):
    """Test depositing resources into the bank."""

    room_typeclass = "typeclasses.terrain.rooms.room_bank.RoomBank"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {1: 20}  # 20 wheat
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key=f"bank-{self.account.key}",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        self.bank.db.gold = 0
        self.bank.db.resources = {}
        self.account.db.bank = self.bank

    @patch("blockchain.xrpl.services.resource.ResourceService.bank")
    def test_deposit_resource_amount(self, mock_bank):
        """deposit wheat 5 should deposit 5 wheat."""
        self.call(CmdDeposit(), "5 wheat", "You deposit 5")
        self.assertEqual(self.char1.get_resource(1), 15)
        self.assertEqual(self.bank.get_resource(1), 5)

    @patch("blockchain.xrpl.services.resource.ResourceService.bank")
    def test_deposit_resource_all(self, mock_bank):
        """deposit wheat all should deposit all wheat."""
        self.call(CmdDeposit(), "all wheat", "You deposit 20")
        self.assertEqual(self.char1.get_resource(1), 0)
        self.assertEqual(self.bank.get_resource(1), 20)

    def test_deposit_resource_insufficient(self):
        """deposit more resource than you have should show error."""
        self.char1.db.resources = {1: 2}
        self.call(CmdDeposit(), "10 wheat", "You only have 2")


class TestCmdDepositNFT(EvenniaCommandTest):
    """Test depositing NFT items into the bank."""

    room_typeclass = "typeclasses.terrain.rooms.room_bank.RoomBank"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key=f"bank-{self.account.key}",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        self.account.db.bank = self.bank

        # Create a takeable NFT in character inventory (bypass hooks)
        self.sword = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Iron Sword",
            nohome=True,
        )
        self.sword.token_id = 42
        self.sword.db_location = self.char1
        self.sword.save(update_fields=["db_location"])
        self.char1.contents_cache.init()  # the direct write bypasses the cache

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    def test_deposit_nft(self, mock_bank):
        """deposit by dbref should move NFT to bank."""
        self.call(CmdDeposit(), str(self.sword.id), "You deposit Iron Sword")
        self.assertEqual(self.sword.location, self.bank)

    def test_deposit_nft_not_found(self):
        """deposit nonexistent token ID should show error."""
        self.call(CmdDeposit(), "999", "You aren't carrying an item with ID #999")

    def test_deposit_unknown_arg(self):
        """deposit with unrecognized argument tries item search."""
        self.call(CmdDeposit(), "banana", "You aren't carrying")


class TestCmdDepositDuplicates(EvenniaCommandTest):
    """Depositing by name when several items answer to that name.

    Identical copies are not an ambiguous request — deposit one. Worn
    gear is not a candidate at all, and must not turn a deposit of the
    spare in your pack into a question.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_bank.RoomBank"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key=f"bank-{self.account.key}",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        self.account.db.bank = self.bank
        self._next_token = 500

    def _make_item(self, key, worn=False):
        """Put an NFT in char1's inventory without firing the mirror hooks."""
        self._next_token += 1
        item = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key=key,
            nohome=True,
        )
        item.token_id = self._next_token
        item.db_location = self.char1
        item.save(update_fields=["db_location"])
        self.char1.contents_cache.init()

        if worn:
            slots = self.char1.db.wearslots
            free = next(s for s, occupant in slots.items() if occupant is None)
            slots[free] = item
            self.char1.db.wearslots = slots

        return item

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    def test_two_identical_copies_deposit_one(self, _mock_bank):
        """Two of the same thing is not a question — bank one of them."""
        first = self._make_item("Brown Corduroy Pants")
        second = self._make_item("Brown Corduroy Pants")

        self.call(
            CmdDeposit(), "brown corduroy pants",
            "You deposit Brown Corduroy Pants",
        )
        banked = [o for o in (first, second) if o.location == self.bank]
        self.assertEqual(len(banked), 1)

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    def test_worn_copy_does_not_block_depositing_a_spare(self, _mock_bank):
        """The reported shape: wearing one pair, carrying two spares."""
        worn = self._make_item("Brown Corduroy Pants", worn=True)
        spare_a = self._make_item("Brown Corduroy Pants")
        spare_b = self._make_item("Brown Corduroy Pants")

        self.call(
            CmdDeposit(), "brown corduroy pants",
            "You deposit Brown Corduroy Pants",
        )
        self.assertEqual(worn.location, self.char1)
        banked = [o for o in (spare_a, spare_b) if o.location == self.bank]
        self.assertEqual(len(banked), 1)

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    def test_only_copy_worn_asks_for_removal(self, _mock_bank):
        worn = self._make_item("Brown Corduroy Pants", worn=True)

        self.call(CmdDeposit(), "brown corduroy pants", "You must remove")
        self.assertEqual(worn.location, self.char1)

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    def test_different_names_still_ask_which(self, _mock_bank):
        """Two distinct items sharing a word is a real ambiguity."""
        corduroy = self._make_item("Brown Corduroy Pants")
        leather = self._make_item("Black Leather Pants")

        self.call(CmdDeposit(), "pants", "More than one match")
        self.assertEqual(corduroy.location, self.char1)
        self.assertEqual(leather.location, self.char1)

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    def test_worn_exact_match_does_not_shadow_a_carried_item(self, _mock_bank):
        """An exact-named worn item must not hide a carried longer name."""
        worn = self._make_item("Brown Corduroy Pants", worn=True)
        deluxe = self._make_item("Brown Corduroy Pants Deluxe")

        self.call(
            CmdDeposit(), "brown corduroy pants",
            "You deposit Brown Corduroy Pants Deluxe",
        )
        self.assertEqual(worn.location, self.char1)
        self.assertEqual(deluxe.location, self.bank)


class TestDepositFungibleVersusItem(EvenniaCommandTest):
    """Choosing between a resource and an item named after it.

    "leather" is a resource, and plenty of gear is named for it. Reading
    the first word against the resource table and discarding the rest
    answers "you don't have any Leather" and leaves a leather cap
    unreachable by the only name it has.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_bank.RoomBank"
    databases = "__all__"

    LEATHER = 9

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key=f"bank-{self.account.key}",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        self.bank.db.gold = 0
        self.bank.db.resources = {}
        self.account.db.bank = self.bank
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        self._next_token = 700

    def _carry(self, key):
        self._next_token += 1
        item = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key=key,
            nohome=True,
        )
        item.token_id = self._next_token
        item.db_location = self.char1
        item.save(update_fields=["db_location"])
        self.char1.contents_cache.init()
        return item

    @patch("blockchain.xrpl.services.resource.ResourceService.bank")
    def test_the_resource_name_banks_the_resource_when_held(self, _mock):
        self.char1.db.resources = {self.LEATHER: 10}
        self.call(CmdDeposit(), "leather")
        self.assertEqual(self.char1.get_resource(self.LEATHER), 9)

    @patch("blockchain.xrpl.services.resource.ResourceService.bank")
    def test_a_partial_resource_name_banks_the_resource(self, _mock):
        self.char1.db.resources = {self.LEATHER: 10}
        self.call(CmdDeposit(), "leat")
        self.assertEqual(self.char1.get_resource(self.LEATHER), 9)

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    def test_the_resource_name_finds_the_item_when_none_is_held(self, _mock):
        cap = self._carry("leather cap")
        self.call(CmdDeposit(), "leather")
        self.assertEqual(cap.location, self.bank)

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    def test_a_longer_name_takes_the_item_over_the_held_resource(self, _mock):
        self.char1.db.resources = {self.LEATHER: 10}
        cap = self._carry("leather cap")
        self.call(CmdDeposit(), "leather cap")
        self.assertEqual(cap.location, self.bank)
        self.assertEqual(self.char1.get_resource(self.LEATHER), 10)

    def test_a_longer_name_does_not_fall_back_to_the_resource(self):
        """No cap to bank — say so, don't quietly bank leather instead."""
        self.char1.db.resources = {self.LEATHER: 10}
        self.call(CmdDeposit(), "leather cap")
        self.assertEqual(self.char1.get_resource(self.LEATHER), 10)

    @patch("blockchain.xrpl.services.resource.ResourceService.bank")
    def test_a_leading_count_banks_that_many(self, _mock):
        """Counts lead — `deposit 5 wheat`, not `deposit wheat 5`."""
        self.char1.db.resources = {1: 20}
        self.call(CmdDeposit(), "5 wheat")
        self.assertEqual(self.char1.get_resource(1), 15)

    @patch("blockchain.xrpl.services.resource.ResourceService.bank")
    def test_all_of_a_resource(self, _mock):
        self.char1.db.resources = {1: 20}
        self.call(CmdDeposit(), "all wheat")
        self.assertEqual(self.char1.get_resource(1), 0)

    def test_a_count_on_an_item_is_refused(self):
        cap = self._carry("faded cap")
        self.call(CmdDeposit(), "2 faded cap")
        self.assertEqual(cap.location, self.char1)

    def test_holding_two_matching_resources_asks_which(self):
        self.char1.db.resources = {4: 5, 5: 5}  # Iron Ore, Iron Ingot
        self.call(CmdDeposit(), "iron", "Did you mean")
        self.assertEqual(self.char1.get_resource(4), 5)
        self.assertEqual(self.char1.get_resource(5), 5)

