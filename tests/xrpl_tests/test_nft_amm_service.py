"""
Tests for NFTAMMService — proxy token AMM buy/sell operations
with mocked XRPL calls.
"""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from blockchain.xrpl.models import (
    FungibleGameState,
    FungibleTransferLog,
    XRPLTransactionLog,
)


# Test constants
VAULT = "rVAULT_ADDRESS_TEST"
PLAYER = "rPLAYER_ADDRESS_TEST"
CHAR_KEY = "char#1234"
GOLD = "FCMGold"
PGOLD = "PGold"
PTOKEN = "PTrainDagger"


def _seed(currency_code, wallet, location, balance, character_key=None):
    """Create a FungibleGameState row for testing."""
    return FungibleGameState.objects.create(
        currency_code=currency_code,
        wallet_address=wallet,
        location=location,
        character_key=character_key,
        balance=balance,
    )


def _balance(currency_code, wallet, location, character_key=None):
    """Get a FungibleGameState balance."""
    try:
        row = FungibleGameState.objects.get(
            currency_code=currency_code,
            wallet_address=wallet,
            location=location,
            character_key=character_key,
        )
        return row.balance
    except FungibleGameState.DoesNotExist:
        return Decimal(0)


# ═══════════════════════════════════════════════════════════════════════
#  Price query tests
# ═══════════════════════════════════════════════════════════════════════

class TestNFTAMMServicePriceQueries(TestCase):
    """Test get_buy_price and get_sell_price."""

    databases = {"default", "xrpl"}

    @patch("blockchain.xrpl.xrpl_amm.get_swap_quote")
    def test_get_buy_price_ceil_rounded(self, mock_quote):
        """Buy price is ceil-rounded."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService
        mock_quote.return_value = {
            "gold_cost_rounded": 15,
            "gold_received_rounded": None,
        }
        price = NFTAMMService.get_buy_price(PTOKEN)
        self.assertEqual(price, 15)
        mock_quote.assert_called_once_with(
            PTOKEN, 1, direction="buy", gold_currency=PGOLD,
        )

    @patch("blockchain.xrpl.xrpl_amm.get_swap_quote")
    def test_get_sell_price_floor_rounded(self, mock_quote):
        """Sell price is floor-rounded."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService
        mock_quote.return_value = {
            "gold_cost_rounded": None,
            "gold_received_rounded": 12,
        }
        price = NFTAMMService.get_sell_price(PTOKEN)
        self.assertEqual(price, 12)
        mock_quote.assert_called_once_with(
            PTOKEN, 1, direction="sell", gold_currency=PGOLD,
        )

    @patch("blockchain.xrpl.xrpl_amm.get_multi_pool_prices")
    def test_get_pool_prices_batch(self, mock_multi):
        """Batch price query passes PGold as gold currency."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService
        mock_multi.return_value = {
            PTOKEN: {"buy_1": 15, "sell_1": 12},
        }
        result = NFTAMMService.get_pool_prices([PTOKEN])
        self.assertIn(PTOKEN, result)
        mock_multi.assert_called_once_with([PTOKEN], gold_currency=PGOLD)


# ═══════════════════════════════════════════════════════════════════════
#  Buy item tests
# ═══════════════════════════════════════════════════════════════════════

class TestNFTAMMServiceBuyItem(TestCase):
    """Test buy_item accounting — FCMGold + PGold RESERVE movements."""

    databases = {"default", "xrpl"}

    def setUp(self):
        # Player has gold
        _seed(GOLD, PLAYER, "CHARACTER", Decimal("100"), CHAR_KEY)
        # Vault has FCMGold reserve (to absorb player's payment)
        _seed(GOLD, VAULT, "RESERVE", Decimal("10000"))
        # Vault has PGold reserve (to spend to AMM)
        _seed(PGOLD, VAULT, "RESERVE", Decimal("5000"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    def test_buy_item_basic_accounting(self, mock_swap):
        """Buy deducts player FCMGold, credits vault FCMGold, debits vault PGold."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService

        mock_swap.return_value = {
            "tx_hash": "ABCD1234",
            "actual_input": Decimal("14.5"),   # actual PGold spent
            "actual_output": Decimal("1"),
        }

        result = NFTAMMService.buy_item(
            PLAYER, CHAR_KEY, PTOKEN, 15, VAULT,
        )

        self.assertEqual(result["gold_cost"], 15)
        self.assertEqual(result["tx_hash"], "ABCD1234")

        # Player FCMGold: 100 - 15 = 85
        self.assertEqual(
            _balance(GOLD, PLAYER, "CHARACTER", CHAR_KEY),
            Decimal("85"),
        )
        # Vault FCMGold RESERVE: 10000 + 15 - 0.5 (dust to sink) = 10014.5
        vault_gold = _balance(GOLD, VAULT, "RESERVE")
        self.assertEqual(vault_gold, Decimal("10014.5"))

        # Vault PGold RESERVE: 5000 - 14.5 = 4985.5
        vault_pgold = _balance(PGOLD, VAULT, "RESERVE")
        self.assertEqual(vault_pgold, Decimal("4985.5"))

        # Gold dust (margin) went to SINK: 15 - 14.5 = 0.5
        sink_gold = _balance(GOLD, VAULT, "SINK")
        self.assertEqual(sink_gold, Decimal("0.5"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    def test_buy_item_no_dust(self, mock_swap):
        """When ceil equals actual, no dust goes to sink."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService

        mock_swap.return_value = {
            "tx_hash": "ABCD5678",
            "actual_input": Decimal("15"),
            "actual_output": Decimal("1"),
        }

        result = NFTAMMService.buy_item(
            PLAYER, CHAR_KEY, PTOKEN, 15, VAULT,
        )

        self.assertEqual(result["gold_dust"], Decimal("0"))
        # No SINK row should exist for gold
        self.assertEqual(_balance(GOLD, VAULT, "SINK"), Decimal(0))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    def test_buy_item_creates_transfer_logs(self, mock_swap):
        """Buy creates transfer logs for player and AMM sides."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService

        mock_swap.return_value = {
            "tx_hash": "LOG_TEST",
            "actual_input": Decimal("14"),
            "actual_output": Decimal("1"),
        }

        NFTAMMService.buy_item(PLAYER, CHAR_KEY, PTOKEN, 15, VAULT)

        # Player-side log (FCMGold)
        player_log = FungibleTransferLog.objects.filter(
            transfer_type="nft_amm_buy",
        )
        self.assertEqual(player_log.count(), 1)
        self.assertEqual(player_log.first().currency_code, GOLD)

        # AMM-side logs (PGold out + proxy token in)
        amm_logs = FungibleTransferLog.objects.filter(
            transfer_type="nft_amm_swap",
        )
        self.assertEqual(amm_logs.count(), 2)

        # Transaction log
        tx_log = XRPLTransactionLog.objects.get(tx_hash="LOG_TEST")
        self.assertEqual(tx_log.tx_type, "nft_amm_buy")
        self.assertEqual(tx_log.currency_code, PTOKEN)


# ═══════════════════════════════════════════════════════════════════════
#  Sell item tests
# ═══════════════════════════════════════════════════════════════════════

class TestNFTAMMServiceSellItem(TestCase):
    """Test sell_item accounting — PGold RESERVE credit, FCMGold to player."""

    databases = {"default", "xrpl"}

    def setUp(self):
        # Player has some gold already
        _seed(GOLD, PLAYER, "CHARACTER", Decimal("50"), CHAR_KEY)
        # Vault has FCMGold reserve (to pay player)
        _seed(GOLD, VAULT, "RESERVE", Decimal("10000"))
        # Vault has PGold reserve
        _seed(PGOLD, VAULT, "RESERVE", Decimal("5000"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    def test_sell_item_basic_accounting(self, mock_swap):
        """Sell credits vault PGold, debits vault FCMGold, credits player."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService

        mock_swap.return_value = {
            "tx_hash": "SELL1234",
            "actual_input": Decimal("1"),
            "actual_output": Decimal("12.7"),  # actual PGold received
        }

        result = NFTAMMService.sell_item(
            PLAYER, CHAR_KEY, PTOKEN, 12, VAULT,
        )

        self.assertEqual(result["gold_received"], 12)

        # Player FCMGold: 50 + 12 = 62
        self.assertEqual(
            _balance(GOLD, PLAYER, "CHARACTER", CHAR_KEY),
            Decimal("62"),
        )
        # Vault FCMGold RESERVE: 10000 - 12 = 9988
        self.assertEqual(
            _balance(GOLD, VAULT, "RESERVE"),
            Decimal("9988"),
        )
        # Vault PGold RESERVE: 5000 + 12.7 - 0.7 (dust) = 5012
        self.assertEqual(
            _balance(PGOLD, VAULT, "RESERVE"),
            Decimal("5012"),
        )
        # PGold dust to SINK: 12.7 - 12 = 0.7
        self.assertEqual(
            _balance(PGOLD, VAULT, "SINK"),
            Decimal("0.7"),
        )

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    def test_sell_item_no_dust(self, mock_swap):
        """When floor equals actual, no PGold dust goes to sink."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService

        mock_swap.return_value = {
            "tx_hash": "SELL_EXACT",
            "actual_input": Decimal("1"),
            "actual_output": Decimal("12"),
        }

        result = NFTAMMService.sell_item(
            PLAYER, CHAR_KEY, PTOKEN, 12, VAULT,
        )

        self.assertEqual(result["pgold_dust"], Decimal("0"))
        self.assertEqual(_balance(PGOLD, VAULT, "SINK"), Decimal(0))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    def test_sell_item_creates_transfer_logs(self, mock_swap):
        """Sell creates transfer logs for AMM and player sides."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService

        mock_swap.return_value = {
            "tx_hash": "SELL_LOG",
            "actual_input": Decimal("1"),
            "actual_output": Decimal("12.3"),
        }

        NFTAMMService.sell_item(PLAYER, CHAR_KEY, PTOKEN, 12, VAULT)

        # AMM-side logs (proxy token out + PGold in)
        amm_logs = FungibleTransferLog.objects.filter(
            transfer_type="nft_amm_swap",
        )
        self.assertEqual(amm_logs.count(), 2)

        # Player-side log (FCMGold)
        player_log = FungibleTransferLog.objects.filter(
            transfer_type="nft_amm_sell",
        )
        self.assertEqual(player_log.count(), 1)
        self.assertEqual(player_log.first().currency_code, GOLD)

        # Transaction log
        tx_log = XRPLTransactionLog.objects.get(tx_hash="SELL_LOG")
        self.assertEqual(tx_log.tx_type, "nft_amm_sell")


# ═══════════════════════════════════════════════════════════════════════
#  PGold reserve balance tracking
# ═══════════════════════════════════════════════════════════════════════

class TestNFTAMMServiceBuyErrors(TestCase):
    """Test buy_item error paths."""

    databases = {"default", "xrpl"}

    def setUp(self):
        _seed(GOLD, PLAYER, "CHARACTER", Decimal("10"), CHAR_KEY)
        _seed(GOLD, VAULT, "RESERVE", Decimal("10000"))
        _seed(PGOLD, VAULT, "RESERVE", Decimal("5000"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    def test_buy_insufficient_player_gold_raises(self, mock_swap):
        """Player doesn't have enough FCMGold to cover the cost."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService

        mock_swap.return_value = {
            "tx_hash": "BUY_FAIL",
            "actual_input": Decimal("20"),
            "actual_output": Decimal("1"),
        }

        with self.assertRaises(ValueError):
            NFTAMMService.buy_item(PLAYER, CHAR_KEY, PTOKEN, 20, VAULT)

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    def test_buy_insufficient_vault_pgold_raises(self, mock_swap):
        """Vault doesn't have enough PGold to fund the swap."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService

        # Give player plenty of gold
        _seed(GOLD, PLAYER, "CHARACTER", Decimal("100000"), "char#rich")
        # Drain vault PGold
        FungibleGameState.objects.filter(
            currency_code=PGOLD, wallet_address=VAULT, location="RESERVE",
        ).delete()
        _seed(PGOLD, VAULT, "RESERVE", Decimal("1"))

        mock_swap.return_value = {
            "tx_hash": "BUY_NOPGOLD",
            "actual_input": Decimal("50"),
            "actual_output": Decimal("1"),
        }

        with self.assertRaises(ValueError):
            NFTAMMService.buy_item(PLAYER, "char#rich", PTOKEN, 50, VAULT)

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    def test_buy_swap_failure_no_state_change(self, mock_swap):
        """If execute_swap raises, no game state should change."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService

        mock_swap.side_effect = Exception("AMM pool unavailable")

        with self.assertRaises(Exception):
            NFTAMMService.buy_item(PLAYER, CHAR_KEY, PTOKEN, 5, VAULT)

        # Player gold unchanged
        self.assertEqual(
            _balance(GOLD, PLAYER, "CHARACTER", CHAR_KEY),
            Decimal("10"),
        )
        # Vault PGold unchanged
        self.assertEqual(
            _balance(PGOLD, VAULT, "RESERVE"),
            Decimal("5000"),
        )


class TestNFTAMMServiceSellErrors(TestCase):
    """Test sell_item error paths."""

    databases = {"default", "xrpl"}

    def setUp(self):
        _seed(GOLD, PLAYER, "CHARACTER", Decimal("50"), CHAR_KEY)
        _seed(GOLD, VAULT, "RESERVE", Decimal("10000"))
        _seed(PGOLD, VAULT, "RESERVE", Decimal("5000"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    def test_sell_insufficient_vault_gold_raises(self, mock_swap):
        """Vault doesn't have enough FCMGold to pay the player."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService

        # Drain vault gold
        FungibleGameState.objects.filter(
            currency_code=GOLD, wallet_address=VAULT, location="RESERVE",
        ).delete()
        _seed(GOLD, VAULT, "RESERVE", Decimal("5"))

        mock_swap.return_value = {
            "tx_hash": "SELL_FAIL",
            "actual_input": Decimal("1"),
            "actual_output": Decimal("12"),
        }

        with self.assertRaises(ValueError):
            NFTAMMService.sell_item(PLAYER, CHAR_KEY, PTOKEN, 12, VAULT)

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    def test_sell_swap_failure_no_state_change(self, mock_swap):
        """If execute_swap raises, no game state should change."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService

        mock_swap.side_effect = Exception("AMM pool unavailable")

        with self.assertRaises(Exception):
            NFTAMMService.sell_item(PLAYER, CHAR_KEY, PTOKEN, 12, VAULT)

        # Player gold unchanged
        self.assertEqual(
            _balance(GOLD, PLAYER, "CHARACTER", CHAR_KEY),
            Decimal("50"),
        )
        # Vault gold unchanged
        self.assertEqual(
            _balance(GOLD, VAULT, "RESERVE"),
            Decimal("10000"),
        )


class TestPGoldReserveTracking(TestCase):
    """Verify PGold RESERVE goes up on sells, down on buys."""

    databases = {"default", "xrpl"}

    def setUp(self):
        _seed(GOLD, PLAYER, "CHARACTER", Decimal("500"), CHAR_KEY)
        _seed(GOLD, VAULT, "RESERVE", Decimal("10000"))
        _seed(PGOLD, VAULT, "RESERVE", Decimal("5000"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    def test_buy_decreases_pgold_reserve(self, mock_swap):
        """Buying an item decreases PGold RESERVE."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService

        mock_swap.return_value = {
            "tx_hash": "BUY_PGOLD",
            "actual_input": Decimal("20"),
            "actual_output": Decimal("1"),
        }

        NFTAMMService.buy_item(PLAYER, CHAR_KEY, PTOKEN, 20, VAULT)

        self.assertEqual(
            _balance(PGOLD, VAULT, "RESERVE"),
            Decimal("4980"),
        )

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    def test_sell_increases_pgold_reserve(self, mock_swap):
        """Selling an item increases PGold RESERVE."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService

        mock_swap.return_value = {
            "tx_hash": "SELL_PGOLD",
            "actual_input": Decimal("1"),
            "actual_output": Decimal("18"),
        }

        NFTAMMService.sell_item(PLAYER, CHAR_KEY, PTOKEN, 18, VAULT)

        self.assertEqual(
            _balance(PGOLD, VAULT, "RESERVE"),
            Decimal("5018"),
        )

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    def test_buy_sell_round_trip_reserve_balanced(self, mock_swap):
        """Buy then sell at same price: PGold RESERVE returns to original."""
        from blockchain.xrpl.services.nft_amm import NFTAMMService

        # Buy: vault spends 15 PGold
        mock_swap.return_value = {
            "tx_hash": "RT_BUY",
            "actual_input": Decimal("15"),
            "actual_output": Decimal("1"),
        }
        NFTAMMService.buy_item(PLAYER, CHAR_KEY, PTOKEN, 15, VAULT)

        # Sell: vault receives 15 PGold
        mock_swap.return_value = {
            "tx_hash": "RT_SELL",
            "actual_input": Decimal("1"),
            "actual_output": Decimal("15"),
        }
        NFTAMMService.sell_item(PLAYER, CHAR_KEY, PTOKEN, 15, VAULT)

        self.assertEqual(
            _balance(PGOLD, VAULT, "RESERVE"),
            Decimal("5000"),
        )
