"""
Tests for CmdImport — verifies kill-switch, wallet checks, balance
validation, Xaman payload creation, and correct service calls for
fungible and NFT imports.

Import is an account-level (OOC) command. Assets go into the account bank.
XRPL queries, Xaman API calls, and vault transactions are mocked.

The import command uses deferToThread for async XRPL/Xaman queries.  In tests
we patch deferToThread to execute synchronously so callbacks fire within the
same call() invocation and self.call() can capture all output.

evennia test --settings settings tests.command_tests.test_cmd_import
"""

from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.test import override_settings
from twisted.internet import defer

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.account_cmds.cmd_import import CmdImport


VAULT = settings.XRPL_VAULT_ADDRESS
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


class ImportTestBase(EvenniaCommandTest):
    """Base class for import command tests."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Create bank for the account
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key=f"bank-{self.account.key}",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        self.account.db.bank = self.bank
        self.bank.db.gold = 0
        self.bank.db.resources = {}


# ================================================================== #
#  Kill-switch & validation tests (synchronous — no deferToThread)
# ================================================================== #

class TestImportGuards(ImportTestBase):
    """Test kill-switch, wallet, and parse validation."""

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=False)
    def test_kill_switch_blocks_import(self):
        """Import should be blocked when kill-switch is off."""
        self.call(
            CmdImport(), "gold 10",
            "Import/export is currently disabled.",
            caller=self.account,
        )

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    def test_no_wallet_shows_error(self):
        """Import without a linked wallet should show error."""
        self.account.attributes.add("wallet_address", None)
        self.call(
            CmdImport(), "gold 10",
            "No wallet linked",
            caller=self.account,
        )

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    def test_no_args_shows_usage(self):
        """Import with no arguments should show usage."""
        self.call(
            CmdImport(), "",
            "Usage:",
            caller=self.account,
        )

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    def test_bad_args_shows_error(self):
        """Import with unrecognised arguments should show error."""
        self.call(
            CmdImport(), "blargfish",
            "Import what?",
            caller=self.account,
        )

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    def test_numeric_token_id_shows_nft_hint(self):
        """import #42 should show hint to use 'import nft' instead."""
        self.call(
            CmdImport(), "#42",
            "Use import nft",
            caller=self.account,
        )


# ================================================================== #
#  Gold import tests
# ================================================================== #

@patch("commands.account_cmds.cmd_import.threads.deferToThread", _sync_defer)
class TestImportGold(ImportTestBase):
    """Test gold import flow."""

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances",
           return_value={})
    def test_no_gold_in_wallet(self, mock_bal):
        """Importing gold when wallet has none should show error."""
        result = self.call(CmdImport(), "gold", caller=self.account)
        self.assertIn("Your wallet has no gold", result)

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances",
           return_value={"FCMGold": Decimal("10")})
    def test_insufficient_gold(self, mock_bal):
        """Importing more gold than in wallet should show error."""
        result = self.call(CmdImport(), "gold 50", caller=self.account)
        self.assertIn("Your wallet only has 10", result)

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances",
           return_value={"FCMGold": Decimal("100")})
    @patch("blockchain.xrpl.xaman.create_payment_payload",
           return_value={"uuid": "U1", "deeplink": "https://x", "qr_url": ""})
    def test_gold_import_creates_payment_payload(self, mock_payload, mock_bal):
        """Successful gold import should create Xaman Payment payload."""
        result = self.call(
            CmdImport(), "gold 50", caller=self.account, inputs=["y"],
        )
        self.assertIn("Sign Payment", result)
        mock_payload.assert_called_once()

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances",
           return_value={"FCMGold": Decimal("100")})
    def test_gold_import_confirm_no_cancels(self, mock_bal):
        """Answering 'n' to confirmation should cancel import."""
        result = self.call(
            CmdImport(), "gold 50", caller=self.account, inputs=["n"],
        )
        self.assertIn("Import cancelled.", result)

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances",
           return_value={"FCMGold": Decimal("200")})
    @patch("blockchain.xrpl.xaman.create_payment_payload",
           return_value={"uuid": "U1", "deeplink": "https://x", "qr_url": ""})
    def test_gold_import_all(self, mock_payload, mock_bal):
        """import gold all should use full wallet balance."""
        result = self.call(
            CmdImport(), "gold all", caller=self.account, inputs=["y"],
        )
        self.assertIn("Sign Payment", result)
        # Amount should be 200 (all gold in wallet)
        args = mock_payload.call_args
        self.assertEqual(args[0][2], 200)  # amount parameter

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances",
           side_effect=Exception("Network error"))
    def test_gold_network_error(self, mock_bal):
        """Network error should show graceful message."""
        result = self.call(CmdImport(), "gold 10", caller=self.account)
        self.assertIn("Could not query XRPL", result)


# ================================================================== #
#  Resource import tests
# ================================================================== #

@patch("commands.account_cmds.cmd_import.threads.deferToThread", _sync_defer)
class TestImportResource(ImportTestBase):
    """Test resource import flow."""

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances",
           return_value={})
    def test_no_resource_in_wallet(self, mock_bal):
        """Importing resource when wallet has none should show error."""
        result = self.call(CmdImport(), "wheat", caller=self.account)
        self.assertIn("Your wallet has no Wheat", result)

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances",
           return_value={"FCMWheat": Decimal("20")})
    @patch("blockchain.xrpl.xaman.create_payment_payload",
           return_value={"uuid": "U1", "deeplink": "https://x", "qr_url": ""})
    def test_resource_import_creates_payload(self, mock_payload, mock_bal):
        """Successful resource import should create Xaman Payment payload."""
        result = self.call(
            CmdImport(), "wheat 5", caller=self.account, inputs=["y"],
        )
        self.assertIn("Sign Payment", result)
        mock_payload.assert_called_once()


# ================================================================== #
#  NFT import tests
# ================================================================== #

@patch("commands.account_cmds.cmd_import.threads.deferToThread", _sync_defer)
class TestImportNFT(ImportTestBase):
    """Test NFT import flow."""

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts", return_value=[])
    def test_no_nfts_in_wallet(self, mock_nfts):
        """import nft with no wallet NFTs should show error."""
        result = self.call(CmdImport(), "nft", caller=self.account)
        self.assertIn("Your wallet has no NFTs", result)

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts",
           return_value=[
               {"nftoken_id": "000800AA", "name": "Iron Longsword"},
               {"nftoken_id": "000800BB", "name": "Leather Shield"},
           ])
    def test_nft_list_shows_numbered(self, mock_nfts):
        """import nft should show numbered list of wallet NFTs."""
        result = self.call(CmdImport(), "nft", caller=self.account)
        self.assertIn("1. Iron Longsword", result)
        self.assertIn("2. Leather Shield", result)

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts",
           return_value=[
               {"nftoken_id": "000800AA", "name": "Iron Longsword"},
           ])
    def test_nft_out_of_range(self, mock_nfts):
        """import nft 5 with only 1 NFT should show error."""
        result = self.call(CmdImport(), "nft 5", caller=self.account)
        self.assertIn("Invalid selection", result)

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts",
           return_value=[
               {"nftoken_id": "000800AA", "name": "Iron Longsword"},
           ])
    @patch("blockchain.xrpl.models.NFTGameState.objects")
    def test_nft_unknown_shows_error(self, mock_qs, mock_nfts):
        """import nft 1 for unknown NFT should show error."""
        from blockchain.xrpl.models import NFTGameState
        mock_qs.select_related.return_value.get.side_effect = (
            NFTGameState.DoesNotExist
        )
        result = self.call(CmdImport(), "nft 1", caller=self.account)
        self.assertIn("Iron Longsword is not a recognised", result)

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts",
           return_value=[
               {"nftoken_id": "000800AA", "name": "Iron Longsword"},
           ])
    @patch("blockchain.xrpl.models.NFTGameState.objects")
    @patch("blockchain.xrpl.xaman.create_nft_sell_offer_payload",
           return_value={"uuid": "U2", "deeplink": "https://x", "qr_url": ""})
    def test_nft_import_creates_sell_offer_payload(self, mock_payload,
                                                    mock_qs, mock_nfts):
        """NFT import should create Xaman NFTokenCreateOffer payload."""
        mock_game_nft = MagicMock()
        mock_game_nft.item_type = MagicMock()
        mock_qs.select_related.return_value.get.return_value = mock_game_nft
        result = self.call(
            CmdImport(), "nft 1", caller=self.account, inputs=["y"],
        )
        self.assertIn("Create Sell Offer", result)
        mock_payload.assert_called_once_with(
            "000800AA", VAULT,
        )

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts",
           return_value=[
               {"nftoken_id": "000800AA", "name": "Iron Longsword"},
           ])
    @patch("blockchain.xrpl.models.NFTGameState.objects")
    def test_nft_import_confirm_no_cancels(self, mock_qs, mock_nfts):
        """Answering 'n' to NFT confirmation should cancel."""
        mock_game_nft = MagicMock()
        mock_game_nft.item_type = MagicMock()
        mock_qs.select_related.return_value.get.return_value = mock_game_nft
        result = self.call(
            CmdImport(), "nft 1", caller=self.account, inputs=["n"],
        )
        self.assertIn("Import cancelled.", result)

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.get_wallet_nfts",
           side_effect=Exception("Network error"))
    def test_nft_network_error(self, mock_nfts):
        """Network error querying NFTs should show graceful message."""
        result = self.call(CmdImport(), "nft", caller=self.account)
        self.assertIn("Could not query XRPL", result)
