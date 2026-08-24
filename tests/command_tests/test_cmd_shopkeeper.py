"""
Tests for resource shopkeeper commands — list, quote, accept, buy, sell.

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

from commands.npc_cmds.cmdset_resource_shop import (
    CmdResourceQuote,
    CmdResourceBuy,
    CmdResourceSell,
)
from commands.npc_cmds.cmdset_shop_base import CmdShopList, CmdShopAccept
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


# The cmdset dispatches worker-thread tasks from two modules — the cmdset
# itself (for price quotes) and the NPC's execute_buy/execute_sell (for
# trade execution). Both need the sync patch applied in these tests.
_patch_threads_cmdset = patch_deferToThread("commands.npc_cmds.cmdset_resource_shop")
_patch_threads_npc = patch_deferToThread(
    "typeclasses.actors.npcs.resource_shopkeeper"
)
_patch_sessions_cmdset = patch(
    "commands.npc_cmds.cmdset_resource_shop._session_check", return_value=True
)
_patch_sessions_npc = patch(
    "typeclasses.actors.npcs.resource_shopkeeper._session_check", return_value=True
)


def _make_shopkeeper(test, inventory, shop_name="Baker's Shop"):
    """Spawn a ResourceShopkeeperNPC in test.room1 with the given inventory."""
    shopkeeper = create.create_object(
        "typeclasses.actors.npcs.resource_shopkeeper.ResourceShopkeeperNPC",
        key="baker",
        location=test.room1,
    )
    shopkeeper.inventory = inventory
    shopkeeper.shop_name = shop_name
    return shopkeeper


class TestCmdShopList(EvenniaCommandTest):
    """Test the list/browse command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.shopkeeper = _make_shopkeeper(self, [1, 2])

    @patch("typeclasses.actors.npcs.resource_shopkeeper.get_resource_type")
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
        self.shopkeeper.inventory = []
        self.call(
            CmdShopList(), "",
            "=== Baker's Shop ===",
            obj=self.shopkeeper,
        )


class TestCmdResourceQuote(EvenniaCommandTest):
    """Test the quote command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.shopkeeper = _make_shopkeeper(self, [1, 2])
        self.char1.db.gold = 500
        self.char1.db.resources = {1: 50, 2: 20}

    @_patch_sessions_cmdset
    @_patch_threads_cmdset
    @patch("typeclasses.actors.npcs.resource_shopkeeper.get_resource_type")
    @patch("blockchain.xrpl.services.amm.AMMService.get_buy_price")
    def test_quote_buy(self, mock_price, mock_rt, _mock_threads, _mock_sessions):
        """Quote buy stores pending quote and shows price."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)
        mock_price.return_value = 11

        self.call(
            CmdResourceQuote(), "buy 10 wheat",
            "Checking market price...",
            obj=self.shopkeeper,
        )

        quote = self.char1.ndb.pending_quote
        self.assertIsNotNone(quote)
        self.assertEqual(quote["direction"], "buy")
        self.assertEqual(quote["qty"], 10)
        self.assertEqual(quote["gold_price"], 11)
        self.assertEqual(quote["item_key"], 1)

    @_patch_sessions_cmdset
    @_patch_threads_cmdset
    @patch("typeclasses.actors.npcs.resource_shopkeeper.get_resource_type")
    @patch("blockchain.xrpl.services.amm.AMMService.get_sell_price")
    def test_quote_sell(self, mock_price, mock_rt, _mock_threads, _mock_sessions):
        """Quote sell stores pending quote."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)
        mock_price.return_value = 47

        self.call(
            CmdResourceQuote(), "sell 50 wheat",
            "Checking market price...",
            obj=self.shopkeeper,
        )

        quote = self.char1.ndb.pending_quote
        self.assertIsNotNone(quote)
        self.assertEqual(quote["direction"], "sell")
        self.assertEqual(quote["gold_price"], 47)

    @patch("typeclasses.actors.npcs.resource_shopkeeper.get_resource_type")
    def test_quote_bad_item(self, mock_rt):
        """Quote rejects items not in the shop."""
        mock_rt.return_value = None

        self.call(
            CmdResourceQuote(), "buy 10 diamonds",
            "This shop doesn't deal in",
            obj=self.shopkeeper,
        )

    @_patch_sessions_cmdset
    @_patch_threads_cmdset
    @patch("typeclasses.actors.npcs.resource_shopkeeper.get_resource_type")
    @patch("blockchain.xrpl.services.amm.AMMService.get_buy_price")
    def test_quote_buy_insufficient_gold(self, mock_price, mock_rt,
                                          _mock_threads, _mock_sessions):
        """Quote buy rejects if player can't afford it."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)
        mock_price.return_value = 600

        self.call(
            CmdResourceQuote(), "buy 100 wheat",
            "Checking market price...",
            obj=self.shopkeeper,
        )
        self.assertIsNone(getattr(self.char1.ndb, "pending_quote", None))

    def test_quote_no_args(self):
        """Quote with no args shows usage."""
        self.call(
            CmdResourceQuote(), "",
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
        self.shopkeeper = _make_shopkeeper(self, [1])
        self.char1.db.gold = 500
        self.char1.db.resources = {1: 50}

    def test_accept_no_quote(self):
        """Accept with no pending quote shows error."""
        self.call(
            CmdShopAccept(), "",
            "You don't have a pending quote",
            obj=self.shopkeeper,
        )

    @_patch_sessions_npc
    @_patch_threads_npc
    @patch("blockchain.xrpl.services.amm.AMMService.buy_resource_record")
    @patch("blockchain.xrpl.services.amm.AMMService.buy_resource_swap")
    def test_accept_buy_executes(self, mock_buy, _mock_record,
                                 _mock_threads, _mock_sessions):
        """Accept executes a pending buy quote via execute_buy()."""
        mock_buy.return_value = {
            "gold_cost": 11,
            "resource_amount": 10,
            "tx_hash": "TX123",
        }

        self.char1._get_wallet = MagicMock(return_value="rTestWallet123")
        self.char1._get_character_key = MagicMock(return_value="TestChar")

        self.char1.ndb.pending_quote = {
            "direction": "buy",
            "shopkeeper_dbref": self.shopkeeper.dbref,
            "gold_price": 11,
            "item_key": 1,
            "qty": 10,
            "display": "10 Wheat",
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


class TestCmdResourceBuy(EvenniaCommandTest):
    """Test the instant buy command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.shopkeeper = _make_shopkeeper(self, [1])
        self.char1.db.gold = 500
        self.char1.db.resources = {}

    @_patch_sessions_cmdset
    @_patch_sessions_npc
    @_patch_threads_cmdset
    @_patch_threads_npc
    @patch("typeclasses.actors.npcs.resource_shopkeeper.get_resource_type")
    @patch("blockchain.xrpl.services.amm.AMMService.buy_resource_record")
    @patch("blockchain.xrpl.services.amm.AMMService.buy_resource_swap")
    @patch("blockchain.xrpl.services.amm.AMMService.get_buy_price")
    def test_buy_instant(self, mock_price, mock_buy, _mock_record, mock_rt,
                          _t_cmdset, _t_npc, _s_cmdset, _s_npc):
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
            CmdResourceBuy(), "10 wheat",
            "Checking market price...",
            obj=self.shopkeeper,
        )

        self.assertEqual(self.char1.db.gold, 489)
        self.assertEqual(self.char1.db.resources.get(1, 0), 10)

    @_patch_sessions_cmdset
    @_patch_threads_cmdset
    @patch("typeclasses.actors.npcs.resource_shopkeeper.get_resource_type")
    @patch("blockchain.xrpl.services.amm.AMMService.get_buy_price")
    def test_buy_insufficient_gold(self, mock_price, mock_rt,
                                    _mock_threads, _mock_sessions):
        """Buy rejects when player doesn't have enough gold."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)
        mock_price.return_value = 600

        self.char1._get_wallet = MagicMock(return_value="rTestWallet123")
        self.char1._get_character_key = MagicMock(return_value="TestChar")

        self.call(
            CmdResourceBuy(), "100 wheat",
            "Checking market price...",
            obj=self.shopkeeper,
        )

        self.assertEqual(self.char1.db.gold, 500)

    def test_buy_no_args(self):
        """Buy with no args shows usage."""
        self.call(
            CmdResourceBuy(), "",
            "Buy what?",
            obj=self.shopkeeper,
        )


class TestCmdResourceSell(EvenniaCommandTest):
    """Test the instant sell command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.shopkeeper = _make_shopkeeper(self, [1])
        self.char1.db.gold = 100
        self.char1.db.resources = {1: 50}

    @_patch_sessions_cmdset
    @_patch_sessions_npc
    @_patch_threads_cmdset
    @_patch_threads_npc
    @patch("typeclasses.actors.npcs.resource_shopkeeper.get_resource_type")
    @patch("blockchain.xrpl.services.amm.AMMService.sell_resource_record")
    @patch("blockchain.xrpl.services.amm.AMMService.sell_resource_swap")
    @patch("blockchain.xrpl.services.amm.AMMService.get_sell_price")
    def test_sell_instant(self, mock_price, mock_sell, _mock_record, mock_rt,
                           _t_cmdset, _t_npc, _s_cmdset, _s_npc):
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
            CmdResourceSell(), "10 wheat",
            "Checking market price...",
            obj=self.shopkeeper,
        )

        self.assertEqual(self.char1.db.gold, 109)
        self.assertEqual(self.char1.db.resources[1], 40)

    @patch("typeclasses.actors.npcs.resource_shopkeeper.get_resource_type")
    def test_sell_insufficient_resource(self, mock_rt):
        """Sell rejects when player doesn't have enough resource."""
        mock_rt.side_effect = lambda rid: {
            1: MOCK_RESOURCE_TYPE_WHEAT,
        }.get(rid)

        self.call(
            CmdResourceSell(), "100 wheat",
            "You only have",
            obj=self.shopkeeper,
        )

    @_patch_sessions_cmdset
    @_patch_sessions_npc
    @_patch_threads_cmdset
    @_patch_threads_npc
    @patch("typeclasses.actors.npcs.resource_shopkeeper.get_resource_type")
    @patch("blockchain.xrpl.services.amm.AMMService.sell_resource_record")
    @patch("blockchain.xrpl.services.amm.AMMService.sell_resource_swap")
    @patch("blockchain.xrpl.services.amm.AMMService.get_sell_price")
    def test_sell_all(self, mock_price, mock_sell, _mock_record, mock_rt,
                       _t_cmdset, _t_npc, _s_cmdset, _s_npc):
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
            CmdResourceSell(), "all wheat",
            "Checking market price...",
            obj=self.shopkeeper,
        )

        self.assertEqual(self.char1.db.gold, 147)
        self.assertEqual(self.char1.db.resources.get(1, 0), 0)

    def test_sell_no_args(self):
        """Sell with no args shows usage."""
        self.call(
            CmdResourceSell(), "",
            "Sell what?",
            obj=self.shopkeeper,
        )


class TestShopTradeRollback(EvenniaCommandTest):
    """
    Test that a failed ownership write leaves the player's balances alone.

    The swap has already happened by the time _record_trade() runs, so what
    is being protected here is the pair that must agree: the game's view of
    the player's holdings and the xrpl database's.
    """

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.shopkeeper = _make_shopkeeper(self, [1])
        self.char1._get_wallet = MagicMock(return_value="rTestWallet123")
        self.char1._get_character_key = MagicMock(return_value="TestChar")
        self.swap_result = {
            "tx_hash": "TX999", "actual_input": 1, "actual_output": 1,
        }

    @patch("blockchain.xrpl.services.amm.AMMService.buy_resource_record")
    def test_buy_record_failure_rolls_back(self, mock_record):
        """A failed buy recording keeps gold and resources unchanged."""
        mock_record.side_effect = RuntimeError("xrpl write failed")
        self.char1.db.gold = 500
        self.char1.db.resources = {}

        with self.assertRaises(RuntimeError):
            self.shopkeeper._record_trade(
                self.char1, "buy", 1, 10, 11, self.swap_result,
            )

        self.assertEqual(self.char1.get_gold(), 500)
        self.assertEqual(self.char1.get_resource(1), 0)

    @patch("blockchain.xrpl.services.amm.AMMService.sell_resource_record")
    def test_sell_record_failure_rolls_back(self, mock_record):
        """A failed sell recording keeps gold and resources unchanged."""
        mock_record.side_effect = RuntimeError("xrpl write failed")
        self.char1.db.gold = 100
        self.char1.db.resources = {1: 10}

        with self.assertRaises(RuntimeError):
            self.shopkeeper._record_trade(
                self.char1, "sell", 1, 10, 9, self.swap_result,
            )

        self.assertEqual(self.char1.get_gold(), 100)
        self.assertEqual(self.char1.get_resource(1), 10)

    @patch("blockchain.xrpl.services.amm.AMMService.buy_resource_record")
    @patch("typeclasses.actors.npcs.resource_shopkeeper.get_resource_type")
    def test_disconnected_player_still_gets_the_trade(self, mock_rt,
                                                      mock_record):
        """A trade books even when the player has no live session."""
        mock_rt.side_effect = lambda rid: MOCK_RESOURCE_TYPE_WHEAT
        self.char1.db.gold = 500
        self.char1.db.resources = {}

        with patch(
            "typeclasses.actors.npcs.resource_shopkeeper._session_check",
            return_value=False,
        ):
            self.shopkeeper._on_buy_complete(
                self.char1, 1, "10 Wheat", 10, 11, self.swap_result,
            )

        mock_record.assert_called_once()
        self.assertEqual(self.char1.get_gold(), 489)
        self.assertEqual(self.char1.get_resource(1), 10)
