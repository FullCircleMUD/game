"""
Tests for database-level constraints on XRPL models.

Verifies that CheckConstraints and UniqueConstraints on
NFTGameState and FungibleGameState are enforced by the database.
"""

from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from blockchain.xrpl.models import FungibleGameState, NFTGameState


# ═══════════════════════════════════════════════════════════════════════
#  NFTGameState constraints
# ═══════════════════════════════════════════════════════════════════════

class TestNFTGameStateConstraints(TestCase):
    databases = {"default", "xrpl"}

    def test_valid_location_enum(self):
        """Location must be one of the 6 defined values."""
        with self.assertRaises(IntegrityError):
            NFTGameState.objects.create(
                nftoken_id="CONSTRAINT_LOC" + "0" * 50,
                taxon=1,
                owner_in_game="rOWNER",
                location="INVALID",
            )

    def test_character_key_required_when_character(self):
        """CHARACTER location must have character_key populated."""
        with self.assertRaises(IntegrityError):
            NFTGameState.objects.create(
                nftoken_id="CONSTRAINT_CK1" + "0" * 50,
                taxon=1,
                owner_in_game="rOWNER",
                location="CHARACTER",
                character_key=None,
            )

    def test_character_key_forbidden_when_not_character(self):
        """Non-CHARACTER location must have character_key=None."""
        with self.assertRaises(IntegrityError):
            NFTGameState.objects.create(
                nftoken_id="CONSTRAINT_CK2" + "0" * 50,
                taxon=1,
                owner_in_game="rOWNER",
                location="ACCOUNT",
                character_key="char#9999",
            )

    def test_owner_null_when_onchain(self):
        """ONCHAIN location must have owner_in_game=None."""
        with self.assertRaises(IntegrityError):
            NFTGameState.objects.create(
                nftoken_id="CONSTRAINT_OW1" + "0" * 50,
                taxon=1,
                owner_in_game="rOWNER",
                location="ONCHAIN",
            )

    def test_owner_required_when_not_onchain(self):
        """Non-ONCHAIN location must have owner_in_game populated."""
        with self.assertRaises(IntegrityError):
            NFTGameState.objects.create(
                nftoken_id="CONSTRAINT_OW2" + "0" * 50,
                taxon=1,
                owner_in_game=None,
                location="RESERVE",
            )

    def test_valid_character_row_accepted(self):
        """A correctly formed CHARACTER row should save without error."""
        nft = NFTGameState.objects.create(
            nftoken_id="CONSTRAINT_OK1" + "0" * 50,
            taxon=1,
            owner_in_game="rOWNER",
            location="CHARACTER",
            character_key="char#1",
        )
        self.assertEqual(nft.location, "CHARACTER")

    def test_valid_onchain_row_accepted(self):
        """A correctly formed ONCHAIN row should save without error."""
        nft = NFTGameState.objects.create(
            nftoken_id="CONSTRAINT_OK2" + "0" * 50,
            taxon=1,
            owner_in_game=None,
            location="ONCHAIN",
        )
        self.assertEqual(nft.location, "ONCHAIN")


# ═══════════════════════════════════════════════════════════════════════
#  FungibleGameState constraints
# ═══════════════════════════════════════════════════════════════════════

class TestFungibleGameStateConstraints(TestCase):
    databases = {"default", "xrpl"}

    def test_valid_location_enum(self):
        """Location must be one of the 5 defined values."""
        with self.assertRaises(IntegrityError):
            FungibleGameState.objects.create(
                currency_code="FCMGold",
                wallet_address="rOWNER",
                location="INVALID",
                balance=Decimal(100),
            )

    def test_character_key_required_when_character(self):
        """CHARACTER location must have character_key populated."""
        with self.assertRaises(IntegrityError):
            FungibleGameState.objects.create(
                currency_code="FCMGold",
                wallet_address="rOWNER",
                location="CHARACTER",
                character_key=None,
                balance=Decimal(100),
            )

    def test_character_key_forbidden_when_not_character(self):
        """Non-CHARACTER location must have character_key=None."""
        with self.assertRaises(IntegrityError):
            FungibleGameState.objects.create(
                currency_code="FCMGold",
                wallet_address="rOWNER",
                location="ACCOUNT",
                character_key="char#9999",
                balance=Decimal(100),
            )

    def test_balance_must_be_positive(self):
        """Balance must be > 0 (zero-balance rows are deleted, not kept)."""
        with self.assertRaises(IntegrityError):
            FungibleGameState.objects.create(
                currency_code="FCMGold",
                wallet_address="rOWNER",
                location="RESERVE",
                balance=Decimal(0),
            )

    def test_negative_balance_rejected(self):
        """Negative balance must be rejected."""
        with self.assertRaises(IntegrityError):
            FungibleGameState.objects.create(
                currency_code="FCMGold",
                wallet_address="rOWNER",
                location="RESERVE",
                balance=Decimal(-10),
            )

    def test_unique_plain_location(self):
        """Only one row per (currency, wallet, non-CHARACTER location)."""
        FungibleGameState.objects.create(
            currency_code="FCMGold",
            wallet_address="rOWNER",
            location="RESERVE",
            balance=Decimal(100),
        )
        with self.assertRaises(IntegrityError):
            FungibleGameState.objects.create(
                currency_code="FCMGold",
                wallet_address="rOWNER",
                location="RESERVE",
                balance=Decimal(50),
            )

    def test_unique_character_location(self):
        """Only one row per (currency, wallet, CHARACTER, character_key)."""
        FungibleGameState.objects.create(
            currency_code="FCMGold",
            wallet_address="rOWNER",
            location="CHARACTER",
            character_key="char#1",
            balance=Decimal(100),
        )
        with self.assertRaises(IntegrityError):
            FungibleGameState.objects.create(
                currency_code="FCMGold",
                wallet_address="rOWNER",
                location="CHARACTER",
                character_key="char#1",
                balance=Decimal(50),
            )

    def test_different_characters_allowed(self):
        """Different character_keys for same wallet+currency should work."""
        FungibleGameState.objects.create(
            currency_code="FCMGold",
            wallet_address="rOWNER",
            location="CHARACTER",
            character_key="char#1",
            balance=Decimal(100),
        )
        row2 = FungibleGameState.objects.create(
            currency_code="FCMGold",
            wallet_address="rOWNER",
            location="CHARACTER",
            character_key="char#2",
            balance=Decimal(50),
        )
        self.assertEqual(row2.balance, Decimal(50))
