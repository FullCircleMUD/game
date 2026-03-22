"""
Tests for shopkeeper commands — list, quote, accept, buy, sell.

Uses EvenniaCommandTest with mocked AMM calls (no live XRPL).
deferToThread is patched to run synchronously (no reactor in tests).
_session_check is patched because test characters lack real sessions.

Because commands now send immediate feedback ("Checking market price...")
before the deferred callback, self.call() assertions match the feedback
message (startswith). Callback results are verified via state assertions.
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.npc_cmds.cmdset_shopkeeper import (
    CmdShopList,
    CmdShopQuote,
    CmdShopAccept,
    CmdShopBuy,
    CmdShopSell,
    _find_resource_by_name,
)
from tests.test_utils.sync_defer import patch_deferToThread


MOCK_RESOURCE_TYPE_WHEAT = {
    "name": "Wheat",
    "unit": "bushels",
    "currency_code": "FCMWheat",
    "description": "Golden wheat.",
    "weight_per_unit_kg": 1.0,
    "is_gold": False,
    "resource_id": 1,
}

MOCK_RESOURCE_TYPE_FLOUR = {
    "name": "Flour",
    "unit": "sacks",
    "currency_code": "FCMFlour",
    "description": "Fine flour.",
    "weight_per_unit_kg": 0.5,
    "is_gold": False,
    "resource_id": 2,
}

# Patch deferToThread for all shopkeeper tests
_patch_threads = patch_deferToThread("commands.npc_cmds.cmdset_shopkeeper")
# Test characters don't have real sessions — bypass the disconnect guard
_patch_sessions = patch(
    "commands.npc_cmds.cmdset_shopkeeper._session_check", return_value=True
)


class TestShopkeeperHelpers(EvenniaCommandTest):
    """Test module-level helper functions."""

    def create_script(self):
        pass

    @patch("commands.npc_cmds.cmdset_shopkeeper.get_resource_type")
    def test_find_resource_by_name(self, mock_rt):
        """Finds resource by case-insensitive name match."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
            2: MOCK_RESOURCE_TYPE_FLOUR,
        }.get(rid)

        rid, rt = _find_resource_by_name("wheat", [1, 2])
        self.assertEqual(rid, 1)
        self.assertEqual(rt["name"], "Wheat")

    @patch("commands.npc_cmds.cmdset_shopkeeper.get_resource_type")
    def test_find_resource_not_in_shop(self, mock_rt):
        """Returns None for resources not in the shop."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)

        rid, rt = _find_resource_by_name("flour", [1])
        self.assertIsNone(rid)

    @patch("commands.npc_cmds.cmdset_shopkeeper.get_resource_type")
    def test_find_resource_case_insensitive(self, mock_rt):
        """Name matching is case-insensitive."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)

        rid, rt = _find_resource_by_name("WHEAT", [1])
        self.assertEqual(rid, 1)


class TestCmdShopList(EvenniaCommandTest):
    """Test the list/browse command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.shopkeeper = create.create_object(
            "typeclasses.actors.npcs.shopkeeper.ShopkeeperNPC",
            key="baker",
            location=self.room1,
        )
        self.shopkeeper.db.tradeable_resources = [1, 2]
        self.shopkeeper.db.shop_name = "Baker's Shop"

    @patch("commands.npc_cmds.cmdset_shopkeeper.get_resource_type")
    def test_list_shows_items(self, mock_rt):
        """List shows tradeable resource names."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
            2: MOCK_RESOURCE_TYPE_FLOUR,
        }.get(rid)

        self.call(
            CmdShopList(), "",
            "=== Baker's Shop ===",
            obj=self.shopkeeper,
        )

    def test_list_empty_shop(self):
        """List shows empty message when shop has no resources."""
        self.shopkeeper.db.tradeable_resources = []
        self.call(
            CmdShopList(), "",
            "=== Baker's Shop ===",
            obj=self.shopkeeper,
        )


class TestCmdShopQuote(EvenniaCommandTest):
    """Test the quote command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.shopkeeper = create.create_object(
            "typeclasses.actors.npcs.shopkeeper.ShopkeeperNPC",
            key="baker",
            location=self.room1,
        )
        self.shopkeeper.db.tradeable_resources = [1, 2]
        self.shopkeeper.db.shop_name = "Baker's Shop"

        self.char1.db.gold = 500
        self.char1.db.resources = {1: 50, 2: 20}

    @_patch_sessions
    @_patch_threads
    @patch("commands.npc_cmds.cmdset_shopkeeper.get_resource_type")
    @patch("blockchain.xrpl.services.amm.AMMService.get_buy_price")
    def test_quote_buy(self, mock_price, mock_rt, _mock_threads,
                       _mock_sessions):
        """Quote buy stores pending quote and shows price."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)
        mock_price.return_value = 11

        self.call(
            CmdShopQuote(), "buy 10 wheat",
            "Checking market price...",
            obj=self.shopkeeper,
        )

        quote = self.char1.ndb.pending_quote
        self.assertIsNotNone(quote)
        self.assertEqual(quote["type"], "buy")
        self.assertEqual(quote["amount"], 10)
        self.assertEqual(quote["gold_price"], 11)

    @_patch_sessions
    @_patch_threads
    @patch("commands.npc_cmds.cmdset_shopkeeper.get_resource_type")
    @patch("blockchain.xrpl.services.amm.AMMService.get_sell_price")
    def test_quote_sell(self, mock_price, mock_rt, _mock_threads,
                        _mock_sessions):
        """Quote sell stores pending quote."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)
        mock_price.return_value = 47

        self.call(
            CmdShopQuote(), "sell 50 wheat",
            "Checking market price...",
            obj=self.shopkeeper,
        )

        quote = self.char1.ndb.pending_quote
        self.assertIsNotNone(quote)
        self.assertEqual(quote["type"], "sell")
        self.assertEqual(quote["gold_price"], 47)

    @patch("commands.npc_cmds.cmdset_shopkeeper.get_resource_type")
    def test_quote_bad_item(self, mock_rt):
        """Quote rejects items not in the shop."""
        mock_rt.return_value = None

        self.call(
            CmdShopQuote(), "buy 10 diamonds",
            "This shop doesn't deal in",
            obj=self.shopkeeper,
        )

    @_patch_sessions
    @_patch_threads
    @patch("commands.npc_cmds.cmdset_shopkeeper.get_resource_type")
    @patch("blockchain.xrpl.services.amm.AMMService.get_buy_price")
    def test_quote_buy_insufficient_gold(self, mock_price, mock_rt,
                                         _mock_threads, _mock_sessions):
        """Quote buy rejects if player can't afford it."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)
        mock_price.return_value = 600

        self.call(
            CmdShopQuote(), "buy 100 wheat",
            "Checking market price...",
            obj=self.shopkeeper,
        )
        # Verify no quote was stored
        self.assertIsNone(getattr(self.char1.ndb, "pending_quote", None))

    def test_quote_no_args(self):
        """Quote with no args shows usage."""
        self.call(
            CmdShopQuote(), "",
            "Usage:",
            obj=self.shopkeeper,
        )


class TestCmdShopAccept(EvenniaCommandTest):
    """Test the accept command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.shopkeeper = create.create_object(
            "typeclasses.actors.npcs.shopkeeper.ShopkeeperNPC",
            key="baker",
            location=self.room1,
        )
        self.shopkeeper.db.tradeable_resources = [1]
        self.shopkeeper.db.shop_name = "Baker's Shop"

        self.char1.db.gold = 500
        self.char1.db.resources = {1: 50}

    def test_accept_no_quote(self):
        """Accept with no pending quote shows error."""
        self.call(
            CmdShopAccept(), "",
            "You don't have a pending quote",
            obj=self.shopkeeper,
        )

    @_patch_sessions
    @_patch_threads
    @patch("blockchain.xrpl.services.amm.AMMService.buy_resource")
    def test_accept_buy_executes(self, mock_buy, _mock_threads,
                                 _mock_sessions):
        """Accept executes a pending buy quote."""
        mock_buy.return_value = {
            "gold_cost": 11,
            "resource_amount": 10,
            "tx_hash": "TX123",
        }

        self.char1._get_wallet = MagicMock(return_value="rTestWallet123")
        self.char1._get_character_key = MagicMock(return_value="TestChar")

        self.char1.ndb.pending_quote = {
            "type": "buy",
            "resource_id": 1,
            "resource_name": "Wheat",
            "amount": 10,
            "gold_price": 11,
            "shopkeeper_dbref": self.shopkeeper.dbref,
        }

        self.call(
            CmdShopAccept(), "",
            "Processing trade...",
            obj=self.shopkeeper,
        )

        # Quote cleared, gold deducted, resource added
        self.assertIsNone(self.char1.ndb.pending_quote)
        self.assertEqual(self.char1.db.gold, 489)
        self.assertEqual(self.char1.db.resources[1], 60)


class TestCmdShopBuy(EvenniaCommandTest):
    """Test the instant buy command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.shopkeeper = create.create_object(
            "typeclasses.actors.npcs.shopkeeper.ShopkeeperNPC",
            key="baker",
            location=self.room1,
        )
        self.shopkeeper.db.tradeable_resources = [1]
        self.shopkeeper.db.shop_name = "Baker's Shop"

        self.char1.db.gold = 500
        self.char1.db.resources = {}

    @_patch_sessions
    @_patch_threads
    @patch("commands.npc_cmds.cmdset_shopkeeper.get_resource_type")
    @patch("blockchain.xrpl.services.amm.AMMService.buy_resource")
    @patch("blockchain.xrpl.services.amm.AMMService.get_buy_price")
    def test_buy_instant(self, mock_price, mock_buy, mock_rt, _mock_threads,
                         _mock_sessions):
        """Instant buy gets price and executes."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)
        mock_price.return_value = 11
        mock_buy.return_value = {
            "gold_cost": 11,
            "resource_amount": 10,
            "tx_hash": "TX123",
        }

        self.char1._get_wallet = MagicMock(return_value="rTestWallet123")
        self.char1._get_character_key = MagicMock(return_value="TestChar")

        self.call(
            CmdShopBuy(), "10 wheat",
            "Processing purchase...",
            obj=self.shopkeeper,
        )

        # Gold deducted, resource added
        self.assertEqual(self.char1.db.gold, 489)
        self.assertEqual(self.char1.db.resources.get(1, 0), 10)

    @_patch_sessions
    @_patch_threads
    @patch("commands.npc_cmds.cmdset_shopkeeper.get_resource_type")
    @patch("blockchain.xrpl.services.amm.AMMService.get_buy_price")
    def test_buy_insufficient_gold(self, mock_price, mock_rt, _mock_threads,
                                   _mock_sessions):
        """Buy rejects when player doesn't have enough gold."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)
        mock_price.return_value = 600

        self.char1._get_wallet = MagicMock(return_value="rTestWallet123")
        self.char1._get_character_key = MagicMock(return_value="TestChar")

        self.call(
            CmdShopBuy(), "100 wheat",
            "Processing purchase...",
            obj=self.shopkeeper,
        )

        # Gold unchanged
        self.assertEqual(self.char1.db.gold, 500)

    def test_buy_no_args(self):
        """Buy with no args shows usage."""
        self.call(
            CmdShopBuy(), "",
            "Buy what?",
            obj=self.shopkeeper,
        )


class TestCmdShopSell(EvenniaCommandTest):
    """Test the instant sell command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.shopkeeper = create.create_object(
            "typeclasses.actors.npcs.shopkeeper.ShopkeeperNPC",
            key="baker",
            location=self.room1,
        )
        self.shopkeeper.db.tradeable_resources = [1]
        self.shopkeeper.db.shop_name = "Baker's Shop"

        self.char1.db.gold = 100
        self.char1.db.resources = {1: 50}

    @_patch_sessions
    @_patch_threads
    @patch("commands.npc_cmds.cmdset_shopkeeper.get_resource_type")
    @patch("blockchain.xrpl.services.amm.AMMService.sell_resource")
    @patch("blockchain.xrpl.services.amm.AMMService.get_sell_price")
    def test_sell_instant(self, mock_price, mock_sell, mock_rt, _mock_threads,
                          _mock_sessions):
        """Instant sell gets price and executes."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)
        mock_price.return_value = 9
        mock_sell.return_value = {
            "gold_received": 9,
            "resource_amount": 10,
            "tx_hash": "TX456",
        }

        self.char1._get_wallet = MagicMock(return_value="rTestWallet123")
        self.char1._get_character_key = MagicMock(return_value="TestChar")

        self.call(
            CmdShopSell(), "10 wheat",
            "Processing sale...",
            obj=self.shopkeeper,
        )

        # Gold increased, resource removed
        self.assertEqual(self.char1.db.gold, 109)
        self.assertEqual(self.char1.db.resources[1], 40)

    @patch("commands.npc_cmds.cmdset_shopkeeper.get_resource_type")
    def test_sell_insufficient_resource(self, mock_rt):
        """Sell rejects when player doesn't have enough resource."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)

        self.call(
            CmdShopSell(), "100 wheat",
            "You only have",
            obj=self.shopkeeper,
        )

    @_patch_sessions
    @_patch_threads
    @patch("commands.npc_cmds.cmdset_shopkeeper.get_resource_type")
    @patch("blockchain.xrpl.services.amm.AMMService.sell_resource")
    @patch("blockchain.xrpl.services.amm.AMMService.get_sell_price")
    def test_sell_all(self, mock_price, mock_sell, mock_rt, _mock_threads,
                      _mock_sessions):
        """'sell all wheat' sells the player's entire stock."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)
        mock_price.return_value = 47
        mock_sell.return_value = {
            "gold_received": 47,
            "resource_amount": 50,
            "tx_hash": "TX789",
        }

        self.char1._get_wallet = MagicMock(return_value="rTestWallet123")
        self.char1._get_character_key = MagicMock(return_value="TestChar")

        self.call(
            CmdShopSell(), "all wheat",
            "Processing sale...",
            obj=self.shopkeeper,
        )

        # Gold increased, all resource sold
        self.assertEqual(self.char1.db.gold, 147)
        self.assertEqual(self.char1.db.resources.get(1, 0), 0)

    def test_sell_no_args(self):
        """Sell with no args shows usage."""
        self.call(
            CmdShopSell(), "",
            "Sell what?",
            obj=self.shopkeeper,
        )
