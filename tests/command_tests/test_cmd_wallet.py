"""
Tests for CmdWallet — verifies wallet display for on-chain game assets.

Mocks get_wallet_balances and get_wallet_nfts so no real XRPL calls are made.

The wallet command uses deferToThread for async XRPL queries.  In tests we
patch deferToThread to execute synchronously so callbacks fire within the
same call() invocation and self.call() can capture all output.

evennia test --settings settings tests.command_tests.test_cmd_wallet
"""

from decimal import Decimal
from unittest.mock import patch

from twisted.internet import defer

from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_wallet import CmdWallet


WALLET_A = "rTestPlayerWalletAddress123456"


def _sync_defer(func, *args, **kwargs):
    """Run *func* synchronously and return an already-fired Deferred."""
    d = defer.Deferred()
    try:
        result = func(*args, **kwargs)
        d.callback(result)
    except Exception as e:
        d.errback(e)
    return d


class WalletTestBase(EvenniaCommandTest):
    """Base class for wallet command tests."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)


class TestWalletGuards(WalletTestBase):
    """Test wallet validation checks."""

    def test_no_wallet_shows_error(self):
        """wallet without a linked wallet should show error."""
        self.account.attributes.add("wallet_address", None)
        self.call(
            CmdWallet(), "",
            "No wallet linked",
            caller=self.account,
        )


@patch("commands.account_cmds.cmd_wallet.threads.deferToThread", _sync_defer)
class TestWalletDisplay(WalletTestBase):
    """Test wallet display output."""

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts", return_value=[])
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances", return_value={})
    def test_empty_wallet(self, mock_bal, mock_nfts):
        """Empty wallet should show 'no game assets'."""
        result = self.call(CmdWallet(), "", caller=self.account)
        self.assertIn("no game assets", result)

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts", return_value=[])
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances",
           return_value={"FCMGold": Decimal("500")})
    def test_gold_only(self, mock_bal, mock_nfts):
        """Wallet with only gold should show gold balance."""
        result = self.call(CmdWallet(), "", caller=self.account)
        self.assertIn("Gold", result)
        self.assertIn("500", result)

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts", return_value=[])
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances",
           return_value={
               "FCMGold": Decimal("100"),
               "FCMWheat": Decimal("25"),
           })
    def test_gold_and_resources(self, mock_bal, mock_nfts):
        """Wallet with gold and resources should show both."""
        result = self.call(CmdWallet(), "", caller=self.account)
        self.assertIn("Gold", result)
        self.assertIn("100", result)
        self.assertIn("Wheat", result)
        self.assertIn("25", result)

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts",
           return_value=[
               {"nftoken_id": "000800AA", "name": "Iron Longsword"},
               {"nftoken_id": "000800BB", "name": "Leather Shield"},
           ])
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances", return_value={})
    def test_nfts_only(self, mock_bal, mock_nfts):
        """Wallet with only NFTs should show numbered list."""
        result = self.call(CmdWallet(), "", caller=self.account)
        self.assertIn("1. Iron Longsword", result)
        self.assertIn("2. Leather Shield", result)

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts",
           return_value=[
               {"nftoken_id": "000800CC", "name": "Unknown NFT"},
           ])
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances",
           return_value={"FCMGold": Decimal("50")})
    def test_gold_and_nfts(self, mock_bal, mock_nfts):
        """Wallet with gold and NFTs should show both sections."""
        result = self.call(CmdWallet(), "", caller=self.account)
        self.assertIn("Gold", result)
        self.assertIn("50", result)
        self.assertIn("1. Unknown NFT", result)

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts", return_value=[])
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances",
           side_effect=Exception("Network error"))
    def test_balance_error_shows_message(self, mock_bal, mock_nfts):
        """Network error on balances should show graceful message."""
        result = self.call(CmdWallet(), "", caller=self.account)
        self.assertIn("Could not query XRPL", result)

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts",
           side_effect=Exception("Network error"))
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances", return_value={})
    def test_nft_error_shows_message(self, mock_bal, mock_nfts):
        """Network error on NFTs should show graceful message."""
        result = self.call(CmdWallet(), "", caller=self.account)
        self.assertIn("Could not query XRPL", result)

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts", return_value=[])
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances", return_value={})
    def test_shows_wallet_address(self, mock_bal, mock_nfts):
        """Wallet output should include the player's address."""
        result = self.call(CmdWallet(), "", caller=self.account)
        self.assertIn(WALLET_A, result)

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts", return_value=[])
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances",
           return_value={"UNKNOWNCURR": Decimal("10")})
    def test_unknown_currency_shows_raw_code(self, mock_bal, mock_nfts):
        """Unknown currency codes should show the raw code."""
        result = self.call(CmdWallet(), "", caller=self.account)
        self.assertIn("UNKNOWNCURR", result)
        self.assertIn("10", result)
