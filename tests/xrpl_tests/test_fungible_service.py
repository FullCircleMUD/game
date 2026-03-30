"""
Tests for XRPL FungibleService, GoldService, ResourceService,
and verify_fungible_payment.

Uses real database rows (no mocks) for service tests. Django TestCase
auto-rolls back after each test.
"""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from blockchain.xrpl.models import (
    FungibleGameState,
    FungibleTransferLog,
    XRPLTransactionLog,
)
from blockchain.xrpl.services.fungible import FungibleService
from blockchain.xrpl.services.gold import GoldService
from blockchain.xrpl.services.resource import ResourceService
from blockchain.xrpl.xrpl_tx import verify_fungible_payment, XRPLTransactionError


# Test constants
ISSUER = "rISSUER_ADDRESS_TEST"
PLAYER = "rPLAYER_ADDRESS_TEST"
PLAYER2 = "rPLAYER2_ADDRESS_TEST"
CHAR_KEY = "char#1234"
CHAR_KEY2 = "char#5678"
GOLD = "FCMGold"
WHEAT = "FCMWheat"

# Polygon compat params (ignored by XRPL services)
CHAIN_ID = 137
CONTRACT = "0xDEAD"
VAULT = ISSUER


def _seed(currency_code, wallet, location, balance, character_key=None):
    """Create a FungibleGameState row for testing."""
    return FungibleGameState.objects.create(
        currency_code=currency_code,
        wallet_address=wallet,
        location=location,
        character_key=character_key,
        balance=balance,
    )


class TestFungibleServiceCore(TestCase):
    """Test FungibleService._credit, _debit, and queries."""

    databases = {"default", "xrpl"}

    def test_credit_creates_new_row(self):
        FungibleService._credit(
            GOLD, Decimal(100),
            wallet_address=ISSUER,
            location=FungibleGameState.LOCATION_RESERVE,
        )
        row = FungibleGameState.objects.get(
            currency_code=GOLD, wallet_address=ISSUER,
        )
        self.assertEqual(row.balance, Decimal(100))
        self.assertEqual(row.currency_code, GOLD)

    def test_credit_increments_existing(self):
        _seed(GOLD, ISSUER, "RESERVE", Decimal(100))
        FungibleService._credit(
            GOLD, Decimal(50),
            wallet_address=ISSUER,
            location=FungibleGameState.LOCATION_RESERVE,
        )
        row = FungibleGameState.objects.get(
            currency_code=GOLD, wallet_address=ISSUER,
        )
        self.assertEqual(row.balance, Decimal(150))

    def test_debit_subtracts(self):
        _seed(GOLD, ISSUER, "RESERVE", Decimal(100))
        FungibleService._debit(
            GOLD, Decimal(30),
            wallet_address=ISSUER,
            location=FungibleGameState.LOCATION_RESERVE,
        )
        row = FungibleGameState.objects.get(
            currency_code=GOLD, wallet_address=ISSUER,
        )
        self.assertEqual(row.balance, Decimal(70))

    def test_debit_deletes_at_zero(self):
        _seed(GOLD, ISSUER, "RESERVE", Decimal(100))
        FungibleService._debit(
            GOLD, Decimal(100),
            wallet_address=ISSUER,
            location=FungibleGameState.LOCATION_RESERVE,
        )
        self.assertFalse(
            FungibleGameState.objects.filter(
                currency_code=GOLD, wallet_address=ISSUER,
            ).exists()
        )

    def test_debit_insufficient_raises(self):
        _seed(GOLD, ISSUER, "RESERVE", Decimal(50))
        with self.assertRaises(ValueError):
            FungibleService._debit(
                GOLD, Decimal(100),
                wallet_address=ISSUER,
                location=FungibleGameState.LOCATION_RESERVE,
            )

    def test_debit_missing_row_raises(self):
        with self.assertRaises(ValueError):
            FungibleService._debit(
                GOLD, Decimal(100),
                wallet_address=ISSUER,
                location=FungibleGameState.LOCATION_RESERVE,
            )

    def test_get_balance(self):
        _seed(GOLD, PLAYER, "CHARACTER", Decimal(42), CHAR_KEY)
        bal = FungibleService.get_balance(GOLD, PLAYER, "CHARACTER", CHAR_KEY)
        self.assertEqual(bal, Decimal(42))

    def test_get_balance_missing_returns_zero(self):
        bal = FungibleService.get_balance(GOLD, PLAYER, "CHARACTER", CHAR_KEY)
        self.assertEqual(bal, Decimal(0))


class TestFungibleServiceOperations(TestCase):
    """Test FungibleService spawn/despawn/pickup/drop/bank/etc."""

    databases = {"default", "xrpl"}

    def setUp(self):
        _seed(GOLD, ISSUER, "RESERVE", Decimal(10000))

    def test_spawn_and_despawn(self):
        FungibleService.spawn(GOLD, Decimal(500), ISSUER)
        self.assertEqual(
            FungibleService.get_balance(GOLD, ISSUER, "RESERVE"),
            Decimal(9500),
        )
        self.assertEqual(
            FungibleService.get_balance(GOLD, ISSUER, "SPAWNED"),
            Decimal(500),
        )

        FungibleService.despawn(GOLD, Decimal(200), ISSUER)
        self.assertEqual(
            FungibleService.get_balance(GOLD, ISSUER, "SPAWNED"),
            Decimal(300),
        )
        self.assertEqual(
            FungibleService.get_balance(GOLD, ISSUER, "RESERVE"),
            Decimal(9700),
        )

    def test_pickup_and_drop(self):
        FungibleService.spawn(GOLD, Decimal(100), ISSUER)
        FungibleService.pickup(GOLD, PLAYER, Decimal(50), ISSUER, CHAR_KEY)

        self.assertEqual(
            FungibleService.get_balance(GOLD, ISSUER, "SPAWNED"),
            Decimal(50),
        )
        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "CHARACTER", CHAR_KEY),
            Decimal(50),
        )
        self.assertEqual(FungibleTransferLog.objects.count(), 1)

        FungibleService.drop(GOLD, PLAYER, Decimal(20), ISSUER, CHAR_KEY)
        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "CHARACTER", CHAR_KEY),
            Decimal(30),
        )
        self.assertEqual(FungibleTransferLog.objects.count(), 2)

    def test_bank_and_unbank(self):
        FungibleService.spawn(GOLD, Decimal(100), ISSUER)
        FungibleService.pickup(GOLD, PLAYER, Decimal(100), ISSUER, CHAR_KEY)
        FungibleService.bank(GOLD, PLAYER, Decimal(60), CHAR_KEY)

        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "CHARACTER", CHAR_KEY),
            Decimal(40),
        )
        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "ACCOUNT"),
            Decimal(60),
        )

        FungibleService.unbank(GOLD, PLAYER, Decimal(20), CHAR_KEY)
        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "CHARACTER", CHAR_KEY),
            Decimal(60),
        )
        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "ACCOUNT"),
            Decimal(40),
        )

    def test_transfer(self):
        FungibleService.spawn(GOLD, Decimal(100), ISSUER)
        FungibleService.pickup(GOLD, PLAYER, Decimal(100), ISSUER, CHAR_KEY)
        FungibleService.transfer(
            GOLD, PLAYER, CHAR_KEY, PLAYER2, CHAR_KEY2, Decimal(30),
        )

        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "CHARACTER", CHAR_KEY),
            Decimal(70),
        )
        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER2, "CHARACTER", CHAR_KEY2),
            Decimal(30),
        )

    def test_craft_input_and_output(self):
        FungibleService.spawn(GOLD, Decimal(100), ISSUER)
        FungibleService.pickup(GOLD, PLAYER, Decimal(100), ISSUER, CHAR_KEY)

        FungibleService.craft_input(GOLD, PLAYER, Decimal(40), ISSUER, CHAR_KEY)
        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "CHARACTER", CHAR_KEY),
            Decimal(60),
        )
        self.assertEqual(
            FungibleService.get_balance(GOLD, ISSUER, "RESERVE"),
            Decimal(9940),
        )

        FungibleService.craft_output(GOLD, PLAYER, Decimal(10), ISSUER, CHAR_KEY)
        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "CHARACTER", CHAR_KEY),
            Decimal(70),
        )

    def test_deposit_and_withdraw(self):
        FungibleService.deposit_from_chain(
            GOLD, PLAYER, Decimal(500), ISSUER, "TX_HASH_1",
        )
        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "ACCOUNT"),
            Decimal(500),
        )
        self.assertEqual(
            FungibleService.get_balance(GOLD, ISSUER, "RESERVE"),
            Decimal(9500),
        )
        self.assertEqual(XRPLTransactionLog.objects.count(), 1)
        tx = XRPLTransactionLog.objects.get()
        self.assertEqual(tx.status, "confirmed")
        self.assertEqual(tx.tx_type, "import")

        FungibleService.withdraw_to_chain(
            GOLD, PLAYER, Decimal(200), ISSUER, "TX_HASH_2",
        )
        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "ACCOUNT"),
            Decimal(300),
        )
        self.assertEqual(XRPLTransactionLog.objects.count(), 2)

    def test_deposit_duplicate_tx_hash_rejected(self):
        """Same tx_hash should not credit the bank twice."""
        FungibleService.deposit_from_chain(
            GOLD, PLAYER, Decimal(500), ISSUER, "TX_DUPE",
        )
        with self.assertRaises(ValueError) as ctx:
            FungibleService.deposit_from_chain(
                GOLD, PLAYER, Decimal(500), ISSUER, "TX_DUPE",
            )
        self.assertIn("already processed", str(ctx.exception))
        # Balance should still be 500, not 1000
        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "ACCOUNT"),
            Decimal(500),
        )

    def test_withdraw_duplicate_tx_hash_rejected(self):
        """Same tx_hash should not debit the bank twice."""
        FungibleService.deposit_from_chain(
            GOLD, PLAYER, Decimal(500), ISSUER, "TX_DEP",
        )
        FungibleService.withdraw_to_chain(
            GOLD, PLAYER, Decimal(200), ISSUER, "TX_WD",
        )
        with self.assertRaises(ValueError) as ctx:
            FungibleService.withdraw_to_chain(
                GOLD, PLAYER, Decimal(200), ISSUER, "TX_WD",
            )
        self.assertIn("already processed", str(ctx.exception))
        # Balance should still be 300, not 100
        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "ACCOUNT"),
            Decimal(300),
        )

    def test_reserve_to_account_and_back(self):
        FungibleService.reserve_to_account(GOLD, PLAYER, Decimal(100), ISSUER)
        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "ACCOUNT"),
            Decimal(100),
        )

        FungibleService.account_to_reserve(GOLD, PLAYER, Decimal(100), ISSUER)
        self.assertEqual(
            FungibleService.get_balance(GOLD, PLAYER, "ACCOUNT"),
            Decimal(0),
        )


class TestGoldServiceWrapper(TestCase):
    """Test GoldService delegates correctly to FungibleService."""

    databases = {"default", "xrpl"}

    def setUp(self):
        _seed(GOLD, VAULT, "RESERVE", Decimal(10000))

    def test_spawn(self):
        GoldService.spawn(Decimal(500), CHAIN_ID, CONTRACT, VAULT)
        self.assertEqual(
            FungibleService.get_balance(GOLD, VAULT, "SPAWNED"),
            Decimal(500),
        )

    def test_pickup(self):
        GoldService.spawn(Decimal(100), CHAIN_ID, CONTRACT, VAULT)
        GoldService.pickup(PLAYER, Decimal(50), CHAIN_ID, CONTRACT, VAULT, CHAR_KEY)
        self.assertEqual(
            GoldService.get_character_gold(PLAYER, CHAIN_ID, CONTRACT, CHAR_KEY),
            Decimal(50),
        )

    def test_bank(self):
        GoldService.spawn(Decimal(100), CHAIN_ID, CONTRACT, VAULT)
        GoldService.pickup(PLAYER, Decimal(100), CHAIN_ID, CONTRACT, VAULT, CHAR_KEY)
        GoldService.bank(PLAYER, Decimal(60), CHAIN_ID, CONTRACT, CHAR_KEY)
        self.assertEqual(
            GoldService.get_account_gold(PLAYER, CHAIN_ID, CONTRACT),
            Decimal(60),
        )

    def test_get_reserve_balance(self):
        self.assertEqual(
            GoldService.get_reserve_balance(VAULT, CHAIN_ID, CONTRACT),
            Decimal(10000),
        )

    def test_transfer(self):
        GoldService.spawn(Decimal(100), CHAIN_ID, CONTRACT, VAULT)
        GoldService.pickup(PLAYER, Decimal(100), CHAIN_ID, CONTRACT, VAULT, CHAR_KEY)
        GoldService.transfer(
            PLAYER, CHAR_KEY, PLAYER2, CHAR_KEY2,
            Decimal(30), CHAIN_ID, CONTRACT,
        )
        self.assertEqual(
            GoldService.get_character_gold(PLAYER2, CHAIN_ID, CONTRACT, CHAR_KEY2),
            Decimal(30),
        )


class TestResourceServiceWrapper(TestCase):
    """Test ResourceService delegates correctly via currency_code mapping."""

    databases = {"default", "xrpl"}

    def setUp(self):
        # Seed reserve for wheat (resource_id=1 -> FCMWheat)
        _seed(WHEAT, VAULT, "RESERVE", Decimal(5000))

    def test_spawn(self):
        ResourceService.spawn(1, Decimal(200), CHAIN_ID, CONTRACT, VAULT)
        self.assertEqual(
            FungibleService.get_balance(WHEAT, VAULT, "SPAWNED"),
            Decimal(200),
        )

    def test_pickup(self):
        ResourceService.spawn(1, Decimal(200), CHAIN_ID, CONTRACT, VAULT)
        ResourceService.pickup(PLAYER, 1, Decimal(100), CHAIN_ID, CONTRACT, VAULT, CHAR_KEY)
        self.assertEqual(
            ResourceService.get_character_resource(PLAYER, 1, CHAIN_ID, CONTRACT, CHAR_KEY),
            Decimal(100),
        )

    def test_bank(self):
        ResourceService.spawn(1, Decimal(200), CHAIN_ID, CONTRACT, VAULT)
        ResourceService.pickup(PLAYER, 1, Decimal(200), CHAIN_ID, CONTRACT, VAULT, CHAR_KEY)
        ResourceService.bank(PLAYER, 1, Decimal(100), CHAIN_ID, CONTRACT, CHAR_KEY)
        self.assertEqual(
            ResourceService.get_account_resource(PLAYER, 1, CHAIN_ID, CONTRACT),
            Decimal(100),
        )

    def test_transfer(self):
        ResourceService.spawn(1, Decimal(200), CHAIN_ID, CONTRACT, VAULT)
        ResourceService.pickup(PLAYER, 1, Decimal(200), CHAIN_ID, CONTRACT, VAULT, CHAR_KEY)
        ResourceService.transfer(
            PLAYER, CHAR_KEY, PLAYER2, CHAR_KEY2,
            1, Decimal(50), CHAIN_ID, CONTRACT,
        )
        self.assertEqual(
            ResourceService.get_character_resource(PLAYER2, 1, CHAIN_ID, CONTRACT, CHAR_KEY2),
            Decimal(50),
        )


# ================================================================== #
#  On-chain verification tests
# ================================================================== #

VAULT_ADDR = "rVAULT_ADDRESS"
ISSUER_ADDR = "rISSUER_ADDR"
CURRENCY_HEX = "46434D476F6C64000000000000000000000000000000000000000000"  # FCMGold

# A valid on-chain Payment result
VALID_TX_RESULT = {
    "validated": True,
    "TransactionType": "Payment",
    "Destination": VAULT_ADDR,
    "Amount": {
        "currency": CURRENCY_HEX,
        "value": "50",
        "issuer": ISSUER_ADDR,
    },
    "meta": {"TransactionResult": "tesSUCCESS"},
}


class TestVerifyFungiblePayment(TestCase):
    """Test verify_fungible_payment on-chain verification."""

    @patch("blockchain.xrpl.xrpl_tx.get_transaction",
           return_value=VALID_TX_RESULT)
    def test_valid_payment_returns_amount(self, mock_tx):
        result = verify_fungible_payment(
            "TX_HASH_1", VAULT_ADDR, CURRENCY_HEX, 50, ISSUER_ADDR,
        )
        self.assertEqual(result, Decimal("50"))

    @patch("blockchain.xrpl.xrpl_tx.get_transaction",
           return_value=VALID_TX_RESULT)
    def test_valid_payment_amount_exceeds_expected(self, mock_tx):
        """On-chain amount > expected is fine (player overpaid)."""
        result = verify_fungible_payment(
            "TX_HASH_1", VAULT_ADDR, CURRENCY_HEX, 30, ISSUER_ADDR,
        )
        self.assertEqual(result, Decimal("50"))

    @patch("blockchain.xrpl.xrpl_tx.get_transaction",
           return_value={
               **VALID_TX_RESULT,
               "meta": {"TransactionResult": "tecPATH_DRY"},
           })
    def test_failed_transaction_raises(self, mock_tx):
        with self.assertRaises(XRPLTransactionError) as ctx:
            verify_fungible_payment(
                "TX1", VAULT_ADDR, CURRENCY_HEX, 50, ISSUER_ADDR,
            )
        self.assertIn("not successful", str(ctx.exception))

    @patch("blockchain.xrpl.xrpl_tx.get_transaction",
           return_value={**VALID_TX_RESULT, "TransactionType": "TrustSet"})
    def test_wrong_transaction_type_raises(self, mock_tx):
        with self.assertRaises(XRPLTransactionError) as ctx:
            verify_fungible_payment(
                "TX1", VAULT_ADDR, CURRENCY_HEX, 50, ISSUER_ADDR,
            )
        self.assertIn("not a Payment", str(ctx.exception))

    @patch("blockchain.xrpl.xrpl_tx.get_transaction",
           return_value={
               **VALID_TX_RESULT,
               "Destination": "rWRONG_ADDRESS",
           })
    def test_wrong_destination_raises(self, mock_tx):
        with self.assertRaises(XRPLTransactionError) as ctx:
            verify_fungible_payment(
                "TX1", VAULT_ADDR, CURRENCY_HEX, 50, ISSUER_ADDR,
            )
        self.assertIn("destination mismatch", str(ctx.exception).lower())

    @patch("blockchain.xrpl.xrpl_tx.get_transaction",
           return_value={**VALID_TX_RESULT, "Amount": "1000000"})
    def test_xrp_amount_raises(self, mock_tx):
        """Payment in XRP (not issued currency) should be rejected."""
        with self.assertRaises(XRPLTransactionError) as ctx:
            verify_fungible_payment(
                "TX1", VAULT_ADDR, CURRENCY_HEX, 50, ISSUER_ADDR,
            )
        self.assertIn("not an issued currency", str(ctx.exception))

    @patch("blockchain.xrpl.xrpl_tx.get_transaction",
           return_value={
               **VALID_TX_RESULT,
               "Amount": {
                   "currency": "WRONG_CURRENCY_HEX",
                   "value": "50",
                   "issuer": ISSUER_ADDR,
               },
           })
    def test_wrong_currency_raises(self, mock_tx):
        with self.assertRaises(XRPLTransactionError) as ctx:
            verify_fungible_payment(
                "TX1", VAULT_ADDR, CURRENCY_HEX, 50, ISSUER_ADDR,
            )
        self.assertIn("Currency mismatch", str(ctx.exception))

    @patch("blockchain.xrpl.xrpl_tx.get_transaction",
           return_value={
               **VALID_TX_RESULT,
               "Amount": {
                   "currency": CURRENCY_HEX,
                   "value": "50",
                   "issuer": "rWRONG_ISSUER",
               },
           })
    def test_wrong_issuer_raises(self, mock_tx):
        with self.assertRaises(XRPLTransactionError) as ctx:
            verify_fungible_payment(
                "TX1", VAULT_ADDR, CURRENCY_HEX, 50, ISSUER_ADDR,
            )
        self.assertIn("Issuer mismatch", str(ctx.exception))

    @patch("blockchain.xrpl.xrpl_tx.get_transaction",
           return_value={
               **VALID_TX_RESULT,
               "Amount": {
                   "currency": CURRENCY_HEX,
                   "value": "10",
                   "issuer": ISSUER_ADDR,
               },
           })
    def test_insufficient_amount_raises(self, mock_tx):
        """On-chain amount < expected should be rejected."""
        with self.assertRaises(XRPLTransactionError) as ctx:
            verify_fungible_payment(
                "TX1", VAULT_ADDR, CURRENCY_HEX, 50, ISSUER_ADDR,
            )
        self.assertIn("Amount mismatch", str(ctx.exception))

    @patch("blockchain.xrpl.xrpl_tx.get_transaction",
           side_effect=Exception("Network error"))
    def test_network_error_raises(self, mock_tx):
        with self.assertRaises(XRPLTransactionError) as ctx:
            verify_fungible_payment(
                "TX1", VAULT_ADDR, CURRENCY_HEX, 50, ISSUER_ADDR,
            )
        self.assertIn("Could not query", str(ctx.exception))
