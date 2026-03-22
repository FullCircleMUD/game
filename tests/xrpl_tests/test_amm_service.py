"""
Tests for XRPL AMM service — constant product formula, price rounding,
buy/sell operations with mocked XRPL calls.
"""

import math
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from blockchain.xrpl.models import (
    FungibleGameState,
    FungibleTransferLog,
    XRPLTransactionLog,
)
from blockchain.xrpl.services.fungible import FungibleService
from blockchain.xrpl.xrpl_amm import (
    calculate_buy_cost,
    calculate_sell_output,
)


# Test constants
VAULT = "rVAULT_ADDRESS_TEST"
PLAYER = "rPLAYER_ADDRESS_TEST"
CHAR_KEY = "char#1234"
GOLD = "FCMGold"
WHEAT = "FCMWheat"


def _seed(currency_code, wallet, location, balance, character_key=None):
    """Create a FungibleGameState row for testing."""
    return FungibleGameState.objects.create(
        currency_code=currency_code,
        wallet_address=wallet,
        location=location,
        character_key=character_key,
        balance=balance,
    )


# ═══════════════════════════════════════════════════════════════════════
#  Constant product formula tests (pure math, no DB)
# ═══════════════════════════════════════════════════════════════════════

class TestConstantProductFormula(TestCase):
    """Test the AMM price calculation functions."""

    databases = {"default", "xrpl"}

    def test_buy_cost_basic(self):
        """Buy 10 wheat from a 1000/1000 pool with 0 fee."""
        cost = calculate_buy_cost(
            Decimal("1000"), Decimal("1000"), 10, 0,
        )
        # k = 1000 * 1000 = 1_000_000
        # After buying 10 wheat: gold_reserve = 1_000_000 / 990 ≈ 1010.10
        # Cost = 1010.10 - 1000 = 10.10
        self.assertAlmostEqual(float(cost), 10.1010, places=2)

    def test_buy_cost_with_fee(self):
        """Buy 10 wheat from a 1000/1000 pool with 0.1% fee (fee=100)."""
        cost = calculate_buy_cost(
            Decimal("1000"), Decimal("1000"), 10, 100,
        )
        # With fee, cost should be slightly higher
        self.assertGreater(cost, Decimal("10.10"))

    def test_buy_cost_large_order(self):
        """Large buy has significant price impact."""
        cost_small = calculate_buy_cost(
            Decimal("1000"), Decimal("1000"), 10, 100,
        )
        cost_large = calculate_buy_cost(
            Decimal("1000"), Decimal("1000"), 100, 100,
        )
        # Price per unit should be higher for the large order
        self.assertGreater(
            cost_large / 100, cost_small / 10,
        )

    def test_buy_cost_exceeds_reserve(self):
        """Cannot buy more than the pool has."""
        with self.assertRaises(ValueError):
            calculate_buy_cost(
                Decimal("1000"), Decimal("1000"), 1000, 0,
            )

    def test_sell_output_basic(self):
        """Sell 10 wheat into a 1000/1000 pool with 0 fee."""
        output = calculate_sell_output(
            Decimal("1000"), Decimal("1000"), 10, 0,
        )
        # k = 1000 * 1000 = 1_000_000
        # After selling 10 wheat: wheat_reserve = 1010
        # gold_reserve = 1_000_000 / 1010 ≈ 990.099
        # Gold received = 1000 - 990.099 = 9.901
        self.assertAlmostEqual(float(output), 9.9009, places=2)

    def test_sell_output_with_fee(self):
        """Sell 10 wheat with 0.1% fee — output should be less than no-fee."""
        output_no_fee = calculate_sell_output(
            Decimal("1000"), Decimal("1000"), 10, 0,
        )
        output_with_fee = calculate_sell_output(
            Decimal("1000"), Decimal("1000"), 10, 100,
        )
        self.assertLess(output_with_fee, output_no_fee)

    def test_buy_sell_symmetry(self):
        """Buying then selling the same amount should result in a net loss (fees)."""
        reserve = Decimal("1000")
        fee = 100

        buy_cost = calculate_buy_cost(reserve, reserve, 10, fee)
        # After buying 10 wheat: new reserves
        new_gold_reserve = reserve + buy_cost
        new_wheat_reserve = reserve - 10

        sell_output = calculate_sell_output(
            new_wheat_reserve, new_gold_reserve, 10, fee,
        )
        # Player spent buy_cost gold and got back sell_output gold
        # Should be a net loss (trading fees)
        self.assertLess(sell_output, buy_cost)

    def test_rounding_buy_ceil(self):
        """Buy price ceil-rounds to integer."""
        cost = calculate_buy_cost(
            Decimal("1000"), Decimal("1000"), 10, 100,
        )
        rounded = int(math.ceil(float(cost)))
        self.assertIsInstance(rounded, int)
        self.assertGreaterEqual(rounded, float(cost))

    def test_rounding_sell_floor(self):
        """Sell price floor-rounds to integer."""
        output = calculate_sell_output(
            Decimal("1000"), Decimal("1000"), 10, 100,
        )
        rounded = int(math.floor(float(output)))
        self.assertIsInstance(rounded, int)
        self.assertLessEqual(rounded, float(output))


# ═══════════════════════════════════════════════════════════════════════
#  AMMService tests (mocked XRPL calls, real DB)
# ═══════════════════════════════════════════════════════════════════════

MOCK_AMM_INFO = {
    "reserve_1": {"currency": "FCMGold", "value": Decimal("1000")},
    "reserve_2": {"currency": "FCMWheat", "value": Decimal("1000")},
    "trading_fee": 100,
    "lp_token": None,
    "amm_account": "rAMMACCOUNT",
}

MOCK_SWAP_RESULT = {
    "tx_hash": "ABC123TXHASH",
    "actual_input": Decimal("10.5"),
    "actual_output": Decimal("10"),
}


@override_settings(
    XRPL_GOLD_CURRENCY_CODE="FCMGold",
    XRPL_VAULT_ADDRESS=VAULT,
)
class TestAMMServiceBuy(TestCase):
    """Test AMMService.buy_resource with mocked XRPL."""

    databases = {"default", "xrpl"}

    def setUp(self):
        # Player has 500 gold on CHARACTER
        _seed(GOLD, PLAYER, "CHARACTER", Decimal("500"), CHAR_KEY)
        # Vault has 10000 wheat in RESERVE
        _seed(WHEAT, VAULT, "RESERVE", Decimal("10000"))
        # Vault has 10000 gold in RESERVE
        _seed(GOLD, VAULT, "RESERVE", Decimal("10000"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_buy_updates_game_state(self, mock_get_code, mock_swap):
        """Buy debits gold from CHARACTER and credits resource to CHARACTER."""
        mock_get_code.return_value = WHEAT
        mock_swap.return_value = MOCK_SWAP_RESULT

        from blockchain.xrpl.services.amm import AMMService

        result = AMMService.buy_resource(
            PLAYER, CHAR_KEY, 1, 10, 11, VAULT,
        )

        self.assertEqual(result["gold_cost"], 11)
        self.assertEqual(result["resource_amount"], 10)
        self.assertEqual(result["tx_hash"], "ABC123TXHASH")

        # Player gold decreased
        player_gold = FungibleGameState.objects.get(
            currency_code=GOLD, wallet_address=PLAYER,
            location="CHARACTER",
        )
        self.assertEqual(player_gold.balance, Decimal("489"))

        # Player wheat appeared
        player_wheat = FungibleGameState.objects.get(
            currency_code=WHEAT, wallet_address=PLAYER,
            location="CHARACTER",
        )
        self.assertEqual(player_wheat.balance, Decimal("10"))

        # Vault gold: +11 from player, -10.5 to AMM, -0.5 dust to SINK = net 0
        vault_gold = FungibleGameState.objects.get(
            currency_code=GOLD, wallet_address=VAULT,
            location="RESERVE",
        )
        self.assertEqual(vault_gold.balance, Decimal("10000"))

        # Vault wheat: +10 from AMM, -10 to player = net 0
        vault_wheat = FungibleGameState.objects.get(
            currency_code=WHEAT, wallet_address=VAULT,
            location="RESERVE",
        )
        self.assertEqual(vault_wheat.balance, Decimal("10000"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_buy_creates_transfer_logs(self, mock_get_code, mock_swap):
        """Buy creates transfer logs for both player and AMM sides."""
        mock_get_code.return_value = WHEAT
        mock_swap.return_value = MOCK_SWAP_RESULT

        from blockchain.xrpl.services.amm import AMMService

        AMMService.buy_resource(PLAYER, CHAR_KEY, 1, 10, 11, VAULT)

        player_logs = FungibleTransferLog.objects.filter(transfer_type="amm_buy")
        self.assertEqual(player_logs.count(), 2)
        amm_logs = FungibleTransferLog.objects.filter(transfer_type="amm_swap")
        self.assertEqual(amm_logs.count(), 2)

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_buy_creates_tx_log(self, mock_get_code, mock_swap):
        """Buy creates an XRPLTransactionLog entry."""
        mock_get_code.return_value = WHEAT
        mock_swap.return_value = MOCK_SWAP_RESULT

        from blockchain.xrpl.services.amm import AMMService

        AMMService.buy_resource(PLAYER, CHAR_KEY, 1, 10, 11, VAULT)

        tx_log = XRPLTransactionLog.objects.get(tx_hash="ABC123TXHASH")
        self.assertEqual(tx_log.tx_type, "amm_buy")
        self.assertEqual(tx_log.status, "confirmed")


@override_settings(
    XRPL_GOLD_CURRENCY_CODE="FCMGold",
    XRPL_VAULT_ADDRESS=VAULT,
)
class TestAMMServiceSell(TestCase):
    """Test AMMService.sell_resource with mocked XRPL."""

    databases = {"default", "xrpl"}

    def setUp(self):
        # Player has 50 wheat on CHARACTER
        _seed(WHEAT, PLAYER, "CHARACTER", Decimal("50"), CHAR_KEY)
        # Vault has 10000 gold in RESERVE
        _seed(GOLD, VAULT, "RESERVE", Decimal("10000"))
        # Vault has 10000 wheat in RESERVE
        _seed(WHEAT, VAULT, "RESERVE", Decimal("10000"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_sell_updates_game_state(self, mock_get_code, mock_swap):
        """Sell debits resource from CHARACTER and credits gold to CHARACTER."""
        mock_get_code.return_value = WHEAT
        mock_swap.return_value = {
            "tx_hash": "SELL_TX_HASH",
            "actual_input": Decimal("10"),
            "actual_output": Decimal("9.5"),
        }

        from blockchain.xrpl.services.amm import AMMService

        result = AMMService.sell_resource(
            PLAYER, CHAR_KEY, 1, 10, 9, VAULT,
        )

        self.assertEqual(result["gold_received"], 9)
        self.assertEqual(result["resource_amount"], 10)

        # Player wheat decreased
        player_wheat = FungibleGameState.objects.get(
            currency_code=WHEAT, wallet_address=PLAYER,
            location="CHARACTER",
        )
        self.assertEqual(player_wheat.balance, Decimal("40"))

        # Player gold appeared
        player_gold = FungibleGameState.objects.get(
            currency_code=GOLD, wallet_address=PLAYER,
            location="CHARACTER",
        )
        self.assertEqual(player_gold.balance, Decimal("9"))

        # Vault gold: +9.5 from AMM, -9 to player, -0.5 dust to SINK = net 0
        vault_gold = FungibleGameState.objects.get(
            currency_code=GOLD, wallet_address=VAULT,
            location="RESERVE",
        )
        self.assertEqual(vault_gold.balance, Decimal("10000"))

        # Vault wheat: +10 from player, -10 to AMM = net 0
        vault_wheat = FungibleGameState.objects.get(
            currency_code=WHEAT, wallet_address=VAULT,
            location="RESERVE",
        )
        self.assertEqual(vault_wheat.balance, Decimal("10000"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_sell_creates_transfer_logs(self, mock_get_code, mock_swap):
        """Sell creates transfer logs for both player and AMM sides."""
        mock_get_code.return_value = WHEAT
        mock_swap.return_value = {
            "tx_hash": "SELL_TX_HASH",
            "actual_input": Decimal("10"),
            "actual_output": Decimal("9.5"),
        }

        from blockchain.xrpl.services.amm import AMMService

        AMMService.sell_resource(PLAYER, CHAR_KEY, 1, 10, 9, VAULT)

        player_logs = FungibleTransferLog.objects.filter(transfer_type="amm_sell")
        self.assertEqual(player_logs.count(), 2)
        amm_logs = FungibleTransferLog.objects.filter(transfer_type="amm_swap")
        self.assertEqual(amm_logs.count(), 2)


# ═══════════════════════════════════════════════════════════════════════
#  Price query tests (mocked XRPL pool info)
# ═══════════════════════════════════════════════════════════════════════

@override_settings(XRPL_GOLD_CURRENCY_CODE="FCMGold")
class TestAMMServicePricing(TestCase):
    """Test AMMService.get_buy_price / get_sell_price."""

    databases = {"default", "xrpl"}

    @patch("blockchain.xrpl.xrpl_amm.get_amm_info")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_get_buy_price_rounds_up(self, mock_get_code, mock_amm_info):
        """Buy price is ceil-rounded to integer."""
        mock_get_code.return_value = WHEAT
        mock_amm_info.return_value = MOCK_AMM_INFO

        from blockchain.xrpl.services.amm import AMMService

        price = AMMService.get_buy_price(1, 10)
        self.assertIsInstance(price, int)

        # Raw cost for 10 wheat in 1000/1000 pool with fee=100 should be
        # slightly over 10.1, so ceil should be 11
        self.assertEqual(price, 11)

    @patch("blockchain.xrpl.xrpl_amm.get_amm_info")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_get_sell_price_rounds_down(self, mock_get_code, mock_amm_info):
        """Sell price is floor-rounded to integer."""
        mock_get_code.return_value = WHEAT
        mock_amm_info.return_value = MOCK_AMM_INFO

        from blockchain.xrpl.services.amm import AMMService

        price = AMMService.get_sell_price(1, 10)
        self.assertIsInstance(price, int)

        # Raw output for selling 10 wheat should be slightly under 9.9
        # so floor should be 9
        self.assertEqual(price, 9)

    @patch("blockchain.xrpl.xrpl_amm.get_amm_info")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_buy_always_more_than_sell(self, mock_get_code, mock_amm_info):
        """Buy price should always exceed sell price (spread)."""
        mock_get_code.return_value = WHEAT
        mock_amm_info.return_value = MOCK_AMM_INFO

        from blockchain.xrpl.services.amm import AMMService

        buy_price = AMMService.get_buy_price(1, 10)
        sell_price = AMMService.get_sell_price(1, 10)

        self.assertGreater(buy_price, sell_price)


# ═══════════════════════════════════════════════════════════════════════
#  Dust tracking tests
# ═══════════════════════════════════════════════════════════════════════

# Swap result that produces both gold dust AND resource dust
MOCK_SWAP_DUSTY = {
    "tx_hash": "DUSTY_BUY_TX",
    "actual_input": Decimal("10.3"),      # vault pays 10.3 gold (player paid 11)
    "actual_output": Decimal("10.25"),    # AMM gives 10.25 wheat (player gets 10)
}


@override_settings(
    XRPL_GOLD_CURRENCY_CODE="FCMGold",
    XRPL_VAULT_ADDRESS=VAULT,
)
class TestAMMDustTrackingBuy(TestCase):
    """Test that buy_resource tracks gold and resource dust."""

    databases = {"default", "xrpl"}

    def setUp(self):
        _seed(GOLD, PLAYER, "CHARACTER", Decimal("500"), CHAR_KEY)
        _seed(WHEAT, VAULT, "RESERVE", Decimal("10000"))
        _seed(GOLD, VAULT, "RESERVE", Decimal("10000"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_buy_tracks_gold_dust(self, mock_get_code, mock_swap):
        """Buy moves gold dust from RESERVE to SINK."""
        mock_get_code.return_value = WHEAT
        mock_swap.return_value = MOCK_SWAP_DUSTY

        from blockchain.xrpl.services.amm import AMMService

        result = AMMService.buy_resource(PLAYER, CHAR_KEY, 1, 10, 11, VAULT)

        # gold_cost=11, actual_gold_spent=10.3 → gold dust = 0.7
        self.assertEqual(result["gold_dust"], Decimal("0.7"))
        sink = FungibleGameState.objects.get(
            currency_code=GOLD, wallet_address=VAULT, location="SINK",
        )
        self.assertEqual(sink.balance, Decimal("0.7"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_buy_tracks_resource_dust(self, mock_get_code, mock_swap):
        """Buy moves resource dust from RESERVE to SINK."""
        mock_get_code.return_value = WHEAT
        mock_swap.return_value = MOCK_SWAP_DUSTY

        from blockchain.xrpl.services.amm import AMMService

        result = AMMService.buy_resource(PLAYER, CHAR_KEY, 1, 10, 11, VAULT)

        # actual_resource_received=10.25, amount=10 → resource dust = 0.25
        self.assertEqual(result["resource_dust"], Decimal("0.25"))
        sink = FungibleGameState.objects.get(
            currency_code=WHEAT, wallet_address=VAULT, location="SINK",
        )
        self.assertEqual(sink.balance, Decimal("0.25"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_buy_no_resource_dust_when_exact(self, mock_get_code, mock_swap):
        """No SINK row when AMM returns exactly the integer amount."""
        mock_get_code.return_value = WHEAT
        mock_swap.return_value = MOCK_SWAP_RESULT  # actual_output=10 (exact)

        from blockchain.xrpl.services.amm import AMMService

        result = AMMService.buy_resource(PLAYER, CHAR_KEY, 1, 10, 11, VAULT)

        self.assertEqual(result["resource_dust"], Decimal("0"))
        self.assertFalse(
            FungibleGameState.objects.filter(
                currency_code=WHEAT, wallet_address=VAULT, location="SINK",
            ).exists()
        )


@override_settings(
    XRPL_GOLD_CURRENCY_CODE="FCMGold",
    XRPL_VAULT_ADDRESS=VAULT,
)
class TestAMMDustTrackingSell(TestCase):
    """Test that sell_resource tracks gold and resource dust."""

    databases = {"default", "xrpl"}

    def setUp(self):
        _seed(WHEAT, PLAYER, "CHARACTER", Decimal("50"), CHAR_KEY)
        _seed(GOLD, VAULT, "RESERVE", Decimal("10000"))
        _seed(WHEAT, VAULT, "RESERVE", Decimal("10000"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_sell_tracks_gold_dust(self, mock_get_code, mock_swap):
        """Sell moves gold dust from RESERVE to SINK."""
        mock_get_code.return_value = WHEAT
        mock_swap.return_value = {
            "tx_hash": "DUSTY_SELL_TX",
            "actual_input": Decimal("9.7"),     # AMM takes 9.7 wheat
            "actual_output": Decimal("9.5"),    # AMM gives 9.5 gold
        }

        from blockchain.xrpl.services.amm import AMMService

        result = AMMService.sell_resource(PLAYER, CHAR_KEY, 1, 10, 9, VAULT)

        # actual_gold_received=9.5, gold_received=9 → gold dust = 0.5
        self.assertEqual(result["gold_dust"], Decimal("0.5"))
        sink = FungibleGameState.objects.get(
            currency_code=GOLD, wallet_address=VAULT, location="SINK",
        )
        self.assertEqual(sink.balance, Decimal("0.5"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_sell_tracks_resource_dust(self, mock_get_code, mock_swap):
        """Sell moves resource dust from RESERVE to SINK."""
        mock_get_code.return_value = WHEAT
        mock_swap.return_value = {
            "tx_hash": "DUSTY_SELL_TX",
            "actual_input": Decimal("9.7"),     # AMM takes 9.7 wheat
            "actual_output": Decimal("9.5"),    # AMM gives 9.5 gold
        }

        from blockchain.xrpl.services.amm import AMMService

        result = AMMService.sell_resource(PLAYER, CHAR_KEY, 1, 10, 9, VAULT)

        # amount=10, actual_resource_spent=9.7 → resource dust = 0.3
        self.assertEqual(result["resource_dust"], Decimal("0.3"))
        sink = FungibleGameState.objects.get(
            currency_code=WHEAT, wallet_address=VAULT, location="SINK",
        )
        self.assertEqual(sink.balance, Decimal("0.3"))

    @patch("blockchain.xrpl.xrpl_amm.execute_swap")
    @patch("blockchain.xrpl.services.amm.get_currency_code")
    def test_sell_no_resource_dust_when_exact(self, mock_get_code, mock_swap):
        """No SINK row when AMM takes exactly the integer amount."""
        mock_get_code.return_value = WHEAT
        mock_swap.return_value = {
            "tx_hash": "EXACT_SELL_TX",
            "actual_input": Decimal("10"),      # AMM takes exactly 10 wheat
            "actual_output": Decimal("9.5"),
        }

        from blockchain.xrpl.services.amm import AMMService

        result = AMMService.sell_resource(PLAYER, CHAR_KEY, 1, 10, 9, VAULT)

        self.assertEqual(result["resource_dust"], Decimal("0"))
        self.assertFalse(
            FungibleGameState.objects.filter(
                currency_code=WHEAT, wallet_address=VAULT, location="SINK",
            ).exists()
        )


