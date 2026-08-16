"""
Tests for blockchain/xrpl/services/chain_sync.py.

This file grows one section per chain_sync function as its test gap
closes (see ops/DEVELOPMENT/ADMIN_COMMAND_SHARD_AUDIT.md's Test gaps
table) — reconcile_fungibles() first, sync_reserves()/sync_nfts() next.

reconcile_fungibles() reads every FungibleGameState/CurrencyType row in
the xrpl database, and both tables are pre-seeded by a data migration
(all 36 resources plus FCMGold, see
blockchain/xrpl/migrations/0001_initial.py — each starts with a 100000
RESERVE balance). That seed data is present in every test run and
can't be cleared without breaking the migration, so tests use
synthetic currency codes (never colliding with real ones) and locate
their own row in the returned list by code, rather than asserting on
the list's length or exact contents.

evennia test --settings settings tests.xrpl_tests.test_chain_sync
"""

from decimal import Decimal
from unittest import TestCase as PlainTestCase
from unittest.mock import AsyncMock, patch

from django.conf import settings
from django.test import TestCase

from blockchain.xrpl.models import CurrencyType, FungibleGameState, NFTGameState
from blockchain.xrpl.services.chain_sync import (
    _extract_game_id,
    _hex_to_string,
    reconcile_fungibles,
    sync_nfts,
    sync_reserves,
)

VAULT = "rVAULT_TEST_ADDRESS"


def _hex_uri(uri):
    """Hex-encode a URI string the way an XRPL NFT's URI field stores it."""
    return uri.encode("ascii").hex()


def _seed_balance(currency_code, location, balance, wallet=VAULT, character_key=None):
    """Create a FungibleGameState row.

    character_key must be set iff location is CHARACTER — a DB check
    constraint (xrpl_fungible_character_key_iff_character) enforces it.
    """
    if character_key is None and location == FungibleGameState.LOCATION_CHARACTER:
        character_key = "char#test"
    return FungibleGameState.objects.create(
        currency_code=currency_code,
        wallet_address=wallet,
        location=location,
        character_key=character_key,
        balance=balance,
    )


def _row_for(rows, currency_code):
    """Find the row for one currency_code among the full (seed-data-padded) result."""
    for row in rows:
        if row["currency_code"] == currency_code:
            return row
    return None


# ══════════════════════════════════════════════════════════════════════════
#  reconcile_fungibles
# ══════════════════════════════════════════════════════════════════════════

class TestReconcileFungibles(TestCase):
    databases = {"default", "xrpl"}

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_delta_zero_when_balanced(self, mock_balances):
        code = "ZZZFAKE_BALANCED"
        mock_balances.return_value = {code: Decimal("100")}
        _seed_balance(code, FungibleGameState.LOCATION_RESERVE, Decimal("100"))

        row = _row_for(reconcile_fungibles(), code)

        self.assertIsNotNone(row)
        self.assertEqual(row["delta"], Decimal("0"))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_positive_delta_when_vault_has_uncounted_assets(self, mock_balances):
        code = "ZZZFAKE_POSITIVE"
        mock_balances.return_value = {code: Decimal("150")}
        _seed_balance(code, FungibleGameState.LOCATION_RESERVE, Decimal("100"))

        row = _row_for(reconcile_fungibles(), code)

        self.assertEqual(row["delta"], Decimal("50"))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_negative_delta_when_game_overcounts(self, mock_balances):
        code = "ZZZFAKE_NEGATIVE"
        mock_balances.return_value = {code: Decimal("100")}
        _seed_balance(code, FungibleGameState.LOCATION_RESERVE, Decimal("150"))

        row = _row_for(reconcile_fungibles(), code)

        self.assertEqual(row["delta"], Decimal("-50"))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_distributed_locations_summed_together(self, mock_balances):
        code = "ZZZFAKE_DISTRIBUTED"
        mock_balances.return_value = {code: Decimal("300")}
        _seed_balance(code, FungibleGameState.LOCATION_CHARACTER, Decimal("100"))
        _seed_balance(code, FungibleGameState.LOCATION_ACCOUNT, Decimal("100"))
        _seed_balance(code, FungibleGameState.LOCATION_SPAWNED, Decimal("100"))

        row = _row_for(reconcile_fungibles(), code)

        self.assertEqual(row["game_distributed"], Decimal("300"))
        self.assertEqual(row["delta"], Decimal("0"))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_sink_tracked_separately_from_reserve_and_distributed(self, mock_balances):
        code = "ZZZFAKE_SINK"
        mock_balances.return_value = {code: Decimal("50")}
        _seed_balance(code, FungibleGameState.LOCATION_SINK, Decimal("50"))

        row = _row_for(reconcile_fungibles(), code)

        self.assertEqual(row["game_sink"], Decimal("50"))
        self.assertEqual(row["game_reserve"], Decimal("0"))
        self.assertEqual(row["game_distributed"], Decimal("0"))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_currency_with_no_game_rows_still_reported(self, mock_balances):
        """On-chain balance with zero DB rows — full delta = on_chain."""
        code = "ZZZFAKE_CHAINONLY"
        mock_balances.return_value = {code: Decimal("75")}

        row = _row_for(reconcile_fungibles(), code)

        self.assertIsNotNone(row)
        self.assertEqual(row["delta"], Decimal("75"))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_currency_with_no_chain_balance_still_reported(self, mock_balances):
        """DB rows exist but chain shows nothing — negative delta."""
        code = "ZZZFAKE_DBONLY"
        mock_balances.return_value = {}
        _seed_balance(code, FungibleGameState.LOCATION_RESERVE, Decimal("20"))

        row = _row_for(reconcile_fungibles(), code)

        self.assertIsNotNone(row)
        self.assertEqual(row["delta"], Decimal("-20"))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_name_lookup_uses_currency_type(self, mock_balances):
        code = "ZZZFAKE_NAMED"
        CurrencyType.objects.create(
            currency_code=code, resource_id=None, name="Fake Currency",
            unit="units",
        )
        mock_balances.return_value = {code: Decimal("10")}
        _seed_balance(code, FungibleGameState.LOCATION_RESERVE, Decimal("10"))

        row = _row_for(reconcile_fungibles(), code)

        self.assertEqual(row["name"], "Fake Currency")

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_unknown_currency_falls_back_to_code_as_name(self, mock_balances):
        code = "ZZZFAKE_UNKNOWN"
        mock_balances.return_value = {code: Decimal("10")}
        _seed_balance(code, FungibleGameState.LOCATION_RESERVE, Decimal("10"))

        row = _row_for(reconcile_fungibles(), code)

        self.assertEqual(row["name"], code)

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_results_sorted_by_currency_code(self, mock_balances):
        mock_balances.return_value = {"ZZZFAKE": Decimal("1"), "AAAFAKE": Decimal("1")}
        _seed_balance("ZZZFAKE", FungibleGameState.LOCATION_RESERVE, Decimal("1"))
        _seed_balance("AAAFAKE", FungibleGameState.LOCATION_RESERVE, Decimal("1"))

        rows = reconcile_fungibles()

        codes = [r["currency_code"] for r in rows]
        self.assertEqual(codes, sorted(codes))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_currency_absent_from_both_chain_and_db_is_not_reported(self, mock_balances):
        mock_balances.return_value = {}

        row = _row_for(reconcile_fungibles(), "ZZZFAKE_NEVER_SEEN")

        self.assertIsNone(row)


# ══════════════════════════════════════════════════════════════════════════
#  sync_reserves
# ══════════════════════════════════════════════════════════════════════════

class TestSyncReserves(TestCase):
    """
    RESERVE = on_chain - (SPAWNED + ACCOUNT + CHARACTER + SINK).

    sync_reserves() writes its updated RESERVE row keyed to
    settings.XRPL_VAULT_ADDRESS specifically (get_or_create on that
    wallet), so RESERVE fixtures use that address — not the arbitrary
    VAULT constant the other tests use, which would leave the write
    creating a second row instead of updating the seeded one.
    """

    databases = {"default", "xrpl"}

    def setUp(self):
        self.vault = settings.XRPL_VAULT_ADDRESS

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_new_reserve_is_chain_minus_non_reserve(self, mock_balances):
        code = "ZZZFAKE_SR_BASIC"
        mock_balances.return_value = {code: Decimal("1000")}
        _seed_balance(code, FungibleGameState.LOCATION_CHARACTER,
                      Decimal("200"), wallet=self.vault)
        _seed_balance(code, FungibleGameState.LOCATION_SINK,
                      Decimal("100"), wallet=self.vault)

        row = _row_for(sync_reserves(), code)

        self.assertEqual(row["new_reserve"], Decimal("700"))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_old_reserve_reflects_existing_row(self, mock_balances):
        code = "ZZZFAKE_SR_OLD"
        mock_balances.return_value = {code: Decimal("500")}
        _seed_balance(code, FungibleGameState.LOCATION_RESERVE,
                      Decimal("300"), wallet=self.vault)

        row = _row_for(sync_reserves(), code)

        self.assertEqual(row["old_reserve"], Decimal("300"))
        self.assertEqual(row["new_reserve"], Decimal("500"))
        self.assertEqual(row["delta"], Decimal("200"))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_zero_delta_leaves_reserve_row_unchanged(self, mock_balances):
        code = "ZZZFAKE_SR_NOCHANGE"
        mock_balances.return_value = {code: Decimal("400")}
        _seed_balance(code, FungibleGameState.LOCATION_RESERVE,
                      Decimal("400"), wallet=self.vault)

        row = _row_for(sync_reserves(), code)

        self.assertEqual(row["delta"], Decimal("0"))
        db_row = FungibleGameState.objects.get(
            currency_code=code, wallet_address=self.vault,
            location=FungibleGameState.LOCATION_RESERVE,
        )
        self.assertEqual(db_row.balance, Decimal("400"))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_positive_new_reserve_updates_existing_row(self, mock_balances):
        code = "ZZZFAKE_SR_UPDATE"
        mock_balances.return_value = {code: Decimal("900")}
        _seed_balance(code, FungibleGameState.LOCATION_RESERVE,
                      Decimal("300"), wallet=self.vault)

        sync_reserves()

        db_row = FungibleGameState.objects.get(
            currency_code=code, wallet_address=self.vault,
            location=FungibleGameState.LOCATION_RESERVE,
        )
        self.assertEqual(db_row.balance, Decimal("900"))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_positive_new_reserve_creates_row_when_missing(self, mock_balances):
        code = "ZZZFAKE_SR_CREATE"
        mock_balances.return_value = {code: Decimal("250")}

        sync_reserves()

        db_row = FungibleGameState.objects.get(
            currency_code=code, wallet_address=self.vault,
            location=FungibleGameState.LOCATION_RESERVE,
        )
        self.assertEqual(db_row.balance, Decimal("250"))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_negative_new_reserve_deletes_existing_row(self, mock_balances):
        """Non-reserve holdings exceed on-chain balance — reserve goes negative,
        so the row is deleted rather than left with a negative balance."""
        code = "ZZZFAKE_SR_DELETE"
        mock_balances.return_value = {code: Decimal("50")}
        _seed_balance(code, FungibleGameState.LOCATION_RESERVE,
                      Decimal("300"), wallet=self.vault)
        _seed_balance(code, FungibleGameState.LOCATION_SINK,
                      Decimal("200"), wallet=self.vault)

        row = _row_for(sync_reserves(), code)

        self.assertEqual(row["new_reserve"], Decimal("0"))
        self.assertFalse(
            FungibleGameState.objects.filter(
                currency_code=code, wallet_address=self.vault,
                location=FungibleGameState.LOCATION_RESERVE,
            ).exists()
        )

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_result_new_reserve_never_reported_negative(self, mock_balances):
        code = "ZZZFAKE_SR_FLOOR"
        mock_balances.return_value = {code: Decimal("0")}
        _seed_balance(code, FungibleGameState.LOCATION_SINK,
                      Decimal("100"), wallet=self.vault)

        row = _row_for(sync_reserves(), code)

        self.assertEqual(row["new_reserve"], Decimal("0"))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_currency_only_on_chain_creates_full_reserve(self, mock_balances):
        code = "ZZZFAKE_SR_CHAINONLY"
        mock_balances.return_value = {code: Decimal("60")}

        row = _row_for(sync_reserves(), code)

        self.assertEqual(row["old_reserve"], Decimal("0"))
        self.assertEqual(row["new_reserve"], Decimal("60"))
        self.assertEqual(row["delta"], Decimal("60"))

    @patch("blockchain.xrpl.xrpl_tx.get_wallet_balances")
    def test_results_sorted_by_currency_code(self, mock_balances):
        mock_balances.return_value = {"ZZZFAKE_SR_Z": Decimal("1"), "AAAFAKE_SR_A": Decimal("1")}

        rows = sync_reserves()

        codes = [r["currency_code"] for r in rows]
        self.assertEqual(codes, sorted(codes))


# ══════════════════════════════════════════════════════════════════════════
#  _hex_to_string / _extract_game_id — pure helper functions
# ══════════════════════════════════════════════════════════════════════════

class TestHexToString(PlainTestCase):

    def test_decodes_ascii_hex(self):
        self.assertEqual(_hex_to_string(_hex_uri("hello")), "hello")

    def test_stops_at_null_terminator(self):
        # "hi" + 0x00 + "junk" — decoding must stop at the null byte.
        hex_str = "hi".encode().hex() + "00" + "junk".encode().hex()
        self.assertEqual(_hex_to_string(hex_str), "hi")

    def test_full_uri_round_trips(self):
        uri = "https://nft.fcmud.world/42"
        self.assertEqual(_hex_to_string(_hex_uri(uri)), uri)


class TestExtractGameId(PlainTestCase):

    def test_extracts_trailing_number(self):
        self.assertEqual(
            _extract_game_id(_hex_uri("https://nft.fcmud.world/42")), 42
        )

    def test_no_trailing_number_returns_none(self):
        self.assertIsNone(_extract_game_id(_hex_uri("https://nft.fcmud.world/")))

    def test_none_uri_returns_none(self):
        self.assertIsNone(_extract_game_id(None))

    def test_empty_uri_returns_none(self):
        self.assertIsNone(_extract_game_id(""))


# ══════════════════════════════════════════════════════════════════════════
#  sync_nfts
# ══════════════════════════════════════════════════════════════════════════

def _chain_nft(nftoken_id, uri=None, taxon=0):
    return {
        "NFTokenID": nftoken_id,
        "nft_taxon": taxon,
        "URI": _hex_uri(uri) if uri else None,
    }


class TestSyncNfts(TestCase):
    databases = {"default", "xrpl"}

    def setUp(self):
        self.vault = settings.XRPL_VAULT_ADDRESS

    @patch("blockchain.xrpl.services.nft_token_patch.dispatch_patch_sweep")
    @patch("blockchain.xrpl.services.chain_sync._fetch_vault_nfts", new_callable=AsyncMock)
    def test_already_tracked_nft_is_unchanged(self, mock_fetch, mock_dispatch):
        nftoken_id = "A" * 64
        NFTGameState.objects.create(
            nftoken_id=nftoken_id, uri_id=1001, taxon=0,
            owner_in_game=self.vault, location="RESERVE",
            item_type=None, metadata={},
        )
        mock_fetch.return_value = [_chain_nft(nftoken_id)]
        mock_dispatch.return_value = 0

        result = sync_nfts()

        self.assertEqual(result["unchanged"], 1)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["skipped"], 0)

    @patch("blockchain.xrpl.services.nft_token_patch.dispatch_patch_sweep")
    @patch("blockchain.xrpl.services.chain_sync._fetch_vault_nfts", new_callable=AsyncMock)
    def test_placeholder_row_updated_with_real_id(self, mock_fetch, mock_dispatch):
        game_id = 1002
        placeholder_id = str(game_id)
        NFTGameState.objects.create(
            nftoken_id=placeholder_id, uri_id=game_id, taxon=0,
            owner_in_game=self.vault, location="RESERVE",
            item_type=None, metadata={},
        )
        real_id = "B" * 64
        mock_fetch.return_value = [
            _chain_nft(real_id, uri=f"https://nft.fcmud.world/{game_id}", taxon=7)
        ]
        mock_dispatch.return_value = 0

        result = sync_nfts()

        self.assertEqual(result["updated"], 1)
        row = NFTGameState.objects.get(uri_id=game_id)
        self.assertEqual(row.nftoken_id, real_id)
        self.assertEqual(row.taxon, 7)

    @patch("blockchain.xrpl.services.nft_token_patch.dispatch_patch_sweep")
    @patch("blockchain.xrpl.services.chain_sync._fetch_vault_nfts", new_callable=AsyncMock)
    def test_no_game_id_and_no_existing_row_is_skipped(self, mock_fetch, mock_dispatch):
        mock_fetch.return_value = [_chain_nft("C" * 64, uri=None)]
        mock_dispatch.return_value = 0

        result = sync_nfts()

        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 0)

    @patch("blockchain.xrpl.services.nft_token_patch.dispatch_patch_sweep")
    @patch("blockchain.xrpl.services.chain_sync._fetch_vault_nfts", new_callable=AsyncMock)
    def test_new_nft_with_game_id_creates_reserve_row(self, mock_fetch, mock_dispatch):
        game_id = 1003
        nftoken_id = "D" * 64
        mock_fetch.return_value = [
            _chain_nft(nftoken_id, uri=f"https://nft.fcmud.world/{game_id}", taxon=2)
        ]
        mock_dispatch.return_value = 0

        result = sync_nfts()

        self.assertEqual(result["created"], 1)
        row = NFTGameState.objects.get(nftoken_id=nftoken_id)
        self.assertEqual(row.uri_id, game_id)
        self.assertEqual(row.location, "RESERVE")
        self.assertEqual(row.owner_in_game, self.vault)

    @patch("blockchain.xrpl.services.nft_token_patch.dispatch_patch_sweep")
    @patch("blockchain.xrpl.services.chain_sync._fetch_vault_nfts", new_callable=AsyncMock)
    def test_on_chain_count_matches_fetched_count(self, mock_fetch, mock_dispatch):
        mock_fetch.return_value = [
            _chain_nft("E" * 64, uri="https://nft.fcmud.world/1004"),
            _chain_nft("F" * 64, uri=None),
        ]
        mock_dispatch.return_value = 0

        result = sync_nfts()

        self.assertEqual(result["on_chain_count"], 2)

    @patch("blockchain.xrpl.services.nft_token_patch.dispatch_patch_sweep")
    @patch("blockchain.xrpl.services.chain_sync._fetch_vault_nfts", new_callable=AsyncMock)
    def test_objects_patched_passed_through_from_dispatch(self, mock_fetch, mock_dispatch):
        mock_fetch.return_value = []
        mock_dispatch.return_value = 7

        result = sync_nfts()

        self.assertEqual(result["objects_patched"], 7)
        mock_dispatch.assert_called_once()

    @patch("blockchain.xrpl.services.nft_token_patch.dispatch_patch_sweep")
    @patch("blockchain.xrpl.services.chain_sync._fetch_vault_nfts", new_callable=AsyncMock)
    def test_no_chain_nfts_returns_zeroed_counts(self, mock_fetch, mock_dispatch):
        mock_fetch.return_value = []
        mock_dispatch.return_value = None

        result = sync_nfts()

        self.assertEqual(result["on_chain_count"], 0)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["unchanged"], 0)
        self.assertEqual(result["skipped"], 0)
