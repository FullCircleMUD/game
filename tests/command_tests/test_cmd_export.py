"""
Tests for CmdExport — verifies kill-switch, wallet checks, balance
validation, trust line checking, and correct service calls for
fungible and NFT exports.

Export is an account-level (OOC) command operating on the account bank.
XRPL transaction functions and Xaman API calls are mocked.

NOTE: EvenniaCommandTest.call() uses startswith matching for message
assertions. Multi-msg commands concat with |, so assertions must match
the FIRST msg sent after the last yield/input.
"""

from unittest.mock import patch, MagicMock

from django.conf import settings
from django.test import override_settings

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.account_cmds.cmd_export import CmdExport


VAULT = settings.XRPL_VAULT_ADDRESS
WALLET_A = "rTestPlayerWalletAddress123456"
TOKEN_ID = 101  # high ID to avoid seed data collisions


class ExportTestBase(EvenniaCommandTest):
    """Base class for export command tests."""

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
#  Kill-switch & validation tests
# ================================================================== #

class TestExportGuards(ExportTestBase):
    """Test kill-switch, wallet, and parse validation."""

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=False)
    def test_kill_switch_blocks_export(self):
        """Export should be blocked when kill-switch is off."""
        self.call(
            CmdExport(), "gold 10",
            "Import/export is currently disabled.",
            caller=self.account,
        )

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    def test_no_wallet_shows_error(self):
        """Export without a linked wallet should show error."""
        self.account.attributes.add("wallet_address", None)
        self.call(
            CmdExport(), "gold 10",
            "No wallet linked",
            caller=self.account,
        )

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    def test_no_args_shows_usage(self):
        """Export with no arguments should show usage."""
        self.call(
            CmdExport(), "",
            "Usage:",
            caller=self.account,
        )

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    def test_bad_args_shows_error(self):
        """Export with unrecognised arguments should show error."""
        self.call(
            CmdExport(), "blargfish",
            "Export what?",
            caller=self.account,
        )


# ================================================================== #
#  Gold export tests
# ================================================================== #

class TestExportGold(ExportTestBase):
    """Test gold export flow."""

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    def test_insufficient_gold(self):
        """Exporting more gold than in bank should show error."""
        self.bank.db.gold = 5
        self.call(
            CmdExport(), "gold 50",
            "Your bank only has 5 gold.",
            caller=self.account,
        )

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("commands.account_cmds.cmd_export._check_trust_line",
           return_value=True)
    @patch("blockchain.xrpl.xrpl_tx.send_payment", return_value="TX_HASH_1")
    @patch("blockchain.xrpl.services.gold.GoldService.withdraw_to_chain")
    def test_gold_export_calls_send_payment(self, mock_withdraw, mock_send,
                                            mock_trust):
        """Successful gold export should call send_payment."""
        self.bank.db.gold = 100
        self.call(
            CmdExport(), "gold 50",
            "Sending gold",
            caller=self.account,
            inputs=["y"],
        )
        mock_send.assert_called_once_with(
            WALLET_A, settings.XRPL_GOLD_CURRENCY_CODE, 50,
        )

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("commands.account_cmds.cmd_export._check_trust_line",
           return_value=True)
    @patch("blockchain.xrpl.xrpl_tx.send_payment", return_value="TX_HASH_1")
    @patch("blockchain.xrpl.services.gold.GoldService.withdraw_to_chain")
    def test_gold_export_calls_withdraw(self, mock_withdraw, mock_send,
                                        mock_trust):
        """Successful gold export should call GoldService.withdraw_to_chain."""
        self.bank.db.gold = 100
        self.call(
            CmdExport(), "gold 50",
            caller=self.account,
            inputs=["y"],
        )
        mock_withdraw.assert_called_once_with(
            WALLET_A, 50, VAULT, "TX_HASH_1",
        )

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("commands.account_cmds.cmd_export._check_trust_line",
           return_value=True)
    @patch("blockchain.xrpl.xrpl_tx.send_payment", return_value="TX_HASH_1")
    @patch("blockchain.xrpl.services.gold.GoldService.withdraw_to_chain")
    def test_gold_export_confirm_no_cancels(self, mock_withdraw, mock_send,
                                            mock_trust):
        """Answering 'n' to confirmation should cancel export."""
        self.bank.db.gold = 100
        self.call(
            CmdExport(), "gold 50",
            "Export cancelled.",
            caller=self.account,
            inputs=["n"],
        )
        mock_send.assert_not_called()

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("commands.account_cmds.cmd_export._check_trust_line",
           return_value=True)
    @patch("blockchain.xrpl.xrpl_tx.send_payment", return_value="TX_HASH_ALL")
    @patch("blockchain.xrpl.services.gold.GoldService.withdraw_to_chain")
    def test_gold_export_all(self, mock_withdraw, mock_send, mock_trust):
        """export gold all should export all gold in the bank."""
        self.bank.db.gold = 200
        self.call(
            CmdExport(), "gold all",
            "Sending gold",
            caller=self.account,
            inputs=["y"],
        )
        mock_send.assert_called_once_with(
            WALLET_A, settings.XRPL_GOLD_CURRENCY_CODE, 200,
        )

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("commands.account_cmds.cmd_export._check_trust_line",
           return_value=False)
    @patch("blockchain.xrpl.xaman.create_trustline_payload",
           return_value={"uuid": "U1", "deeplink": "https://x", "qr_url": ""})
    def test_gold_no_trust_line_prompts_setup(self, mock_trustline,
                                              mock_trust_check):
        """Missing trust line should prompt Xaman TrustSet."""
        self.bank.db.gold = 100
        self.call(
            CmdExport(), "gold 50",
            "Trust Line Required",
            caller=self.account,
        )
        mock_trustline.assert_called_once()

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("commands.account_cmds.cmd_export._check_trust_line",
           return_value=True)
    @patch("blockchain.xrpl.xrpl_tx.send_payment",
           side_effect=Exception("Network error"))
    def test_gold_export_tx_failure_preserves_gold(self, mock_send,
                                                   mock_trust):
        """Transaction failure should not call withdraw."""
        self.bank.db.gold = 100
        self.call(
            CmdExport(), "gold 50",
            "Sending gold",
            caller=self.account,
            inputs=["y"],
        )
        # Gold should still be in bank (withdraw never called)
        self.assertEqual(self.bank.db.gold, 100)


# ================================================================== #
#  Resource export tests
# ================================================================== #

class TestExportResource(ExportTestBase):
    """Test resource export flow."""

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    def test_insufficient_resource(self):
        """Exporting more resource than in bank should show error."""
        self.bank.db.resources = {1: 3}
        self.call(
            CmdExport(), "wheat 10",
            "Your bank only has 3",
            caller=self.account,
        )

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("commands.account_cmds.cmd_export._check_trust_line",
           return_value=True)
    @patch("blockchain.xrpl.xrpl_tx.send_payment", return_value="TX_RES_1")
    @patch("blockchain.xrpl.services.resource.ResourceService.withdraw_to_chain")
    def test_resource_export_calls_services(self, mock_withdraw, mock_send,
                                            mock_trust):
        """Successful resource export should call send_payment and withdraw."""
        self.bank.db.resources = {1: 20}
        self.call(
            CmdExport(), "wheat 5",
            "Sending",
            caller=self.account,
            inputs=["y"],
        )
        mock_send.assert_called_once()
        mock_withdraw.assert_called_once()


# ================================================================== #
#  NFT export tests
# ================================================================== #

class TestExportNFT(ExportTestBase):
    """Test NFT export flow."""

    def setUp(self):
        super().setUp()
        # Create an NFT in the account bank
        self.sword = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Iron Sword",
            nohome=True,
        )
        self.sword.token_id = TOKEN_ID
        self.sword.chain_id = None
        self.sword.contract_address = None
        self.sword.db_location = self.bank
        self.sword.save(update_fields=["db_location"])

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    def test_nft_not_in_bank(self):
        """Exporting a token ID not in the bank should show error."""
        self.call(
            CmdExport(), "#999",
            "No item with ID #999",
            caller=self.account,
        )

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.create_nft_sell_offer",
           return_value=("TX_NFT_1", "OFFER_ID_1"))
    @patch("blockchain.xrpl.xaman.create_nft_accept_payload",
           return_value={"uuid": "U2", "deeplink": "https://x", "qr_url": ""})
    def test_nft_export_creates_sell_offer(self, mock_accept, mock_sell):
        """NFT export should create a sell offer from the vault."""
        self.call(
            CmdExport(), f"#{TOKEN_ID}",
            "Creating NFT sell offer",
            caller=self.account,
            inputs=["y"],
        )
        mock_sell.assert_called_once_with(str(TOKEN_ID), WALLET_A)
        mock_accept.assert_called_once_with("OFFER_ID_1")

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.create_nft_sell_offer",
           return_value=("TX_NFT_1", "OFFER_ID_1"))
    @patch("blockchain.xrpl.xaman.create_nft_accept_payload",
           return_value={"uuid": "U2", "deeplink": "https://x", "qr_url": ""})
    def test_nft_export_confirm_no_cancels(self, mock_accept, mock_sell):
        """Answering 'n' to confirmation should cancel NFT export."""
        self.call(
            CmdExport(), f"#{TOKEN_ID}",
            "Export cancelled.",
            caller=self.account,
            inputs=["n"],
        )
        mock_sell.assert_not_called()

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    @patch("blockchain.xrpl.xrpl_tx.create_nft_sell_offer",
           side_effect=Exception("XRPL error"))
    def test_nft_sell_offer_failure_preserves_item(self, mock_sell):
        """Sell offer failure should preserve the item in bank."""
        self.call(
            CmdExport(), f"#{TOKEN_ID}",
            "Creating NFT sell offer",
            caller=self.account,
            inputs=["y"],
        )
        self.assertIn(self.sword, self.bank.contents)
