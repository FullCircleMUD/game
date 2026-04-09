"""Tests for blockchain.xrpl.memo — FCM transaction memo utilities.

Tests cover:
  - build_memo() hex encoding and compact JSON
  - memo_to_xaman() Xaman txjson format
  - Xaman payload functions include Memos when provided
  - AMMService passes correct swap memos to execute_swap()
"""

import json
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch, MagicMock

from django.test import TestCase as DjangoTestCase, override_settings

from blockchain.xrpl.memo import (
    MEMO_EXPORT,
    MEMO_IMPORT,
    MEMO_NFT_EXPORT,
    MEMO_NFT_IMPORT,
    MEMO_SUBSCRIBE,
    MEMO_SWAP,
    MEMO_TRUST,
    build_memo,
    memo_to_xaman,
)


# ═══════════════════════════════════════════════════════════════════════
#  build_memo() tests
# ═══════════════════════════════════════════════════════════════════════

class TestBuildMemo(TestCase):
    """Test build_memo() produces correct hex-encoded Memo objects."""

    def test_memo_type_hex(self):
        memo = build_memo("fcm/swap", {"a": 1})
        self.assertEqual(
            bytes.fromhex(memo.memo_type).decode("utf-8"),
            "fcm/swap",
        )

    def test_memo_data_compact_json(self):
        memo = build_memo("fcm/swap", {"sell": "FCMGold", "buy": "FCMWheat"})
        decoded = bytes.fromhex(memo.memo_data).decode("utf-8")
        self.assertEqual(
            json.loads(decoded),
            {"sell": "FCMGold", "buy": "FCMWheat"},
        )
        # Compact JSON — no spaces after separators
        self.assertNotIn(": ", decoded)
        self.assertNotIn(", ", decoded)

    def test_memo_format_hex(self):
        memo = build_memo("fcm/swap", {})
        self.assertEqual(
            bytes.fromhex(memo.memo_format).decode("utf-8"),
            "application/json",
        )

    def test_roundtrip_all_types(self):
        """Every memo type constant roundtrips through hex correctly."""
        for memo_type in (MEMO_SWAP, MEMO_SUBSCRIBE, MEMO_EXPORT,
                          MEMO_IMPORT, MEMO_NFT_EXPORT, MEMO_NFT_IMPORT,
                          MEMO_TRUST):
            memo = build_memo(memo_type, {"test": True})
            decoded_type = bytes.fromhex(memo.memo_type).decode("utf-8")
            self.assertEqual(decoded_type, memo_type)

    def test_empty_data(self):
        memo = build_memo("fcm/trust", {})
        decoded = bytes.fromhex(memo.memo_data).decode("utf-8")
        self.assertEqual(json.loads(decoded), {})

    def test_numeric_values_in_data(self):
        """Numeric values survive JSON roundtrip."""
        memo = build_memo(MEMO_SWAP, {
            "sellAmt": "100", "buyAmt": "50", "intVal": 42,
        })
        decoded = json.loads(bytes.fromhex(memo.memo_data).decode("utf-8"))
        self.assertEqual(decoded["sellAmt"], "100")
        self.assertEqual(decoded["intVal"], 42)

    def test_memo_is_valid_xrpl_model(self):
        """build_memo returns a valid xrpl-py Memo model."""
        from xrpl.models import Memo
        memo = build_memo(MEMO_SWAP, {"test": True})
        self.assertIsInstance(memo, Memo)
        self.assertTrue(memo.is_valid())


# ═══════════════════════════════════════════════════════════════════════
#  memo_to_xaman() tests
# ═══════════════════════════════════════════════════════════════════════

class TestMemoToXaman(TestCase):
    """Test memo_to_xaman() produces correct Xaman txjson format."""

    def test_xaman_structure(self):
        memo = build_memo("fcm/export", {"type": "gold", "amount": "100"})
        result = memo_to_xaman(memo)

        self.assertIn("Memo", result)
        inner = result["Memo"]
        self.assertIn("MemoType", inner)
        self.assertIn("MemoData", inner)
        self.assertIn("MemoFormat", inner)

    def test_xaman_values_match_build(self):
        memo = build_memo("fcm/import", {"type": "resource", "amount": "50"})
        result = memo_to_xaman(memo)
        inner = result["Memo"]

        self.assertEqual(inner["MemoType"], memo.memo_type)
        self.assertEqual(inner["MemoData"], memo.memo_data)
        self.assertEqual(inner["MemoFormat"], memo.memo_format)

    def test_xaman_memo_data_decodable(self):
        """Xaman memo data can be decoded back to the original dict."""
        memo = build_memo(MEMO_NFT_EXPORT, {"nftId": "000AAABBB"})
        result = memo_to_xaman(memo)
        hex_data = result["Memo"]["MemoData"]
        decoded = json.loads(bytes.fromhex(hex_data).decode("utf-8"))
        self.assertEqual(decoded, {"nftId": "000AAABBB"})


# ═══════════════════════════════════════════════════════════════════════
#  Xaman payload function tests (memos integration)
# ═══════════════════════════════════════════════════════════════════════

class TestXamanPayloadMemos(TestCase):
    """Test that Xaman payload functions include Memos in txjson."""

    @patch("blockchain.xrpl.xaman._create_payload")
    def test_payment_payload_includes_memos(self, mock_create):
        mock_create.return_value = {"uuid": "test", "deeplink": "", "qr_url": ""}
        from blockchain.xrpl.xaman import create_payment_payload

        memos = [build_memo(MEMO_IMPORT, {"type": "gold", "amount": "100"})]
        create_payment_payload("rDEST", "FCMGold00000000000000000000000000000000",
                               100, "rISSUER", memos=memos)

        txjson = mock_create.call_args[0][0]
        self.assertIn("Memos", txjson)
        self.assertEqual(len(txjson["Memos"]), 1)
        self.assertIn("MemoType", txjson["Memos"][0]["Memo"])

    @patch("blockchain.xrpl.xaman._create_payload")
    def test_payment_payload_no_memos_when_none(self, mock_create):
        mock_create.return_value = {"uuid": "test", "deeplink": "", "qr_url": ""}
        from blockchain.xrpl.xaman import create_payment_payload

        create_payment_payload("rDEST", "FCMGold00000000000000000000000000000000",
                               100, "rISSUER")

        txjson = mock_create.call_args[0][0]
        self.assertNotIn("Memos", txjson)

    @patch("blockchain.xrpl.xaman._create_payload")
    def test_trustline_payload_includes_memos(self, mock_create):
        mock_create.return_value = {"uuid": "test", "deeplink": "", "qr_url": ""}
        from blockchain.xrpl.xaman import create_trustline_payload

        memos = [build_memo(MEMO_TRUST, {"currency": "FCMGold"})]
        create_trustline_payload("HEXCODE", "rISSUER", memos=memos)

        txjson = mock_create.call_args[0][0]
        self.assertIn("Memos", txjson)
        self.assertEqual(txjson["Memos"][0]["Memo"]["MemoType"],
                         memos[0].memo_type)

    @patch("blockchain.xrpl.xaman._create_payload")
    def test_nft_sell_offer_payload_includes_memos(self, mock_create):
        mock_create.return_value = {"uuid": "test", "deeplink": "", "qr_url": ""}
        from blockchain.xrpl.xaman import create_nft_sell_offer_payload

        memos = [build_memo(MEMO_NFT_IMPORT, {"nftId": "000AAA"})]
        create_nft_sell_offer_payload("000AAA", "rVAULT", memos=memos)

        txjson = mock_create.call_args[0][0]
        self.assertIn("Memos", txjson)

    @patch("blockchain.xrpl.xaman._create_payload")
    def test_nft_accept_payload_includes_memos(self, mock_create):
        mock_create.return_value = {"uuid": "test", "deeplink": "", "qr_url": ""}
        from blockchain.xrpl.xaman import create_nft_accept_payload

        memos = [build_memo(MEMO_NFT_EXPORT, {"nftId": "000BBB"})]
        create_nft_accept_payload("OFFER_ID_HEX", memos=memos)

        txjson = mock_create.call_args[0][0]
        self.assertIn("Memos", txjson)


# ═══════════════════════════════════════════════════════════════════════
#  AMMService memo passthrough tests
# ═══════════════════════════════════════════════════════════════════════

MOCK_SWAP_RESULT = {
    "tx_hash": "ABC123TXHASH",
    "actual_input": Decimal("10.5"),
    "actual_output": Decimal("10"),
}

VAULT = "rVAULT_ADDRESS_TEST"
PLAYER = "rPLAYER_ADDRESS_TEST"
CHAR_KEY = "char#1234"
GOLD = "FCMGold"
WHEAT = "FCMWheat"


def _seed(currency_code, wallet, location, balance, character_key=None):
    from blockchain.xrpl.models import FungibleGameState
    return FungibleGameState.objects.create(
        currency_code=currency_code,
        wallet_address=wallet,
        location=location,
        character_key=character_key,
        balance=balance,
    )


@override_settings(XRPL_GOLD_CURRENCY_CODE=GOLD)
class TestAMMServiceSwapMemos(DjangoTestCase):
    """Verify AMMService passes fcm/swap memos to execute_swap."""

    databases = {"default", "xrpl"}

    def setUp(self):
        _seed(GOLD, PLAYER, "CHARACTER", Decimal("500"), CHAR_KEY)
        _seed(WHEAT, VAULT, "RESERVE", Decimal("10000"))
        _seed(GOLD, VAULT, "RESERVE", Decimal("10000"))
        _seed(WHEAT, PLAYER, "CHARACTER", Decimal("50"), CHAR_KEY)

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_buy_passes_swap_memo(self, mock_get_code, mock_swap):
        """buy_resource passes fcm/swap memo with sell/buy currencies."""
        mock_get_code.return_value = WHEAT
        mock_swap.return_value = MOCK_SWAP_RESULT

        from blockchain.xrpl.services.amm import AMMService
        AMMService.buy_resource(PLAYER, CHAR_KEY, 1, 10, 11, VAULT)

        # Verify execute_swap was called with memos kwarg
        call_kwargs = mock_swap.call_args
        memos = call_kwargs.kwargs.get("memos") or call_kwargs[1].get("memos")
        self.assertIsNotNone(memos)
        self.assertEqual(len(memos), 1)

        memo = memos[0]
        decoded_type = bytes.fromhex(memo.memo_type).decode("utf-8")
        self.assertEqual(decoded_type, "fcm/swap")

        decoded_data = json.loads(
            bytes.fromhex(memo.memo_data).decode("utf-8")
        )
        self.assertEqual(decoded_data["sell"], GOLD)
        self.assertEqual(decoded_data["buy"], WHEAT)

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_sell_passes_swap_memo(self, mock_get_code, mock_swap):
        """sell_resource passes fcm/swap memo with sell/buy currencies."""
        mock_get_code.return_value = WHEAT
        mock_swap.return_value = {
            "tx_hash": "SELL_TX_HASH",
            "actual_input": Decimal("10"),
            "actual_output": Decimal("9.5"),
        }

        from blockchain.xrpl.services.amm import AMMService
        AMMService.sell_resource(PLAYER, CHAR_KEY, 1, 10, 9, VAULT)

        call_kwargs = mock_swap.call_args
        memos = call_kwargs.kwargs.get("memos") or call_kwargs[1].get("memos")
        self.assertIsNotNone(memos)

        decoded_data = json.loads(
            bytes.fromhex(memos[0].memo_data).decode("utf-8")
        )
        # sell_resource sells resource for gold
        self.assertEqual(decoded_data["sell"], WHEAT)
        self.assertEqual(decoded_data["buy"], GOLD)
