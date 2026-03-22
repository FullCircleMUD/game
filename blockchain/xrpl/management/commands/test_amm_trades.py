"""
Live AMM integration test — runs real trades against XRPL testnet.

Executes buy and sell trades at various amounts against each detected
AMM pool, then verifies that the game's accounting is correct: the
game must always charge players >= what the vault actually pays on-chain.

Usage:
    evennia run test_amm_trades           # test all detected pools
    evennia run test_amm_trades wheat     # test only wheat pool
    evennia run test_amm_trades --dry-run # query pools, no trades

NOT part of the formal test suite. Run manually against testnet only.
"""

import time
from dataclasses import dataclass, field
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from blockchain.xrpl.models import (
    CurrencyType,
    FungibleGameState,
    FungibleTransferLog,
    XRPLTransactionLog,
)
from blockchain.xrpl.services.amm import AMMService
from blockchain.xrpl.xrpl_amm import get_amm_info
from blockchain.xrpl.xrpl_tx import get_wallet_balances

# Test identity — fake player that only exists in game-state DB.
TEST_WALLET = "rINTEGRATION_TEST"
TEST_CHAR = "integration_test_char"

BUY_AMOUNTS = [1, 5, 10, 50, 100]
SELL_AMOUNTS = [1, 5, 10, 50, 100]


@dataclass
class TradeResult:
    ok: bool
    direction: str
    amount: int
    currency_code: str
    resource_name: str
    quoted_gold: int
    actual_delta: Decimal
    margin: Decimal
    margin_unit: str
    tx_hash: str
    skipped: bool = False
    skip_reason: str = ""
    error: str = ""


@dataclass
class PoolSummary:
    currency_code: str
    resource_name: str
    resource_id: int
    gold_reserve: Decimal
    resource_reserve: Decimal
    trading_fee: int
    results: list = field(default_factory=list)


class Command(BaseCommand):
    help = "Run live AMM integration tests against XRPL testnet"
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "resource", nargs="?", default=None,
            help="Test specific resource by name (e.g. wheat, flour)",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Query pools only, no trades executed",
        )

    def handle(self, *args, **options):
        resource_filter = options["resource"]
        dry_run = options["dry_run"]
        vault = settings.XRPL_VAULT_ADDRESS
        gold = settings.XRPL_GOLD_CURRENCY_CODE

        self.stdout.write("\n=== AMM Integration Test ===")
        self.stdout.write(f"Vault: {vault}")
        self.stdout.write(f"Network: {settings.XRPL_NETWORK_URL}")
        self.stdout.write("")

        # 1. Detect pools
        pools = self._detect_pools(gold, resource_filter)
        if not pools:
            self.stdout.write(self.style.WARNING("No AMM pools detected."))
            return

        pool_names = ", ".join(p.resource_name for p in pools)
        self.stdout.write(f"Detected pools: {pool_names}\n")

        if dry_run:
            for pool in pools:
                fee_pct = Decimal(pool.trading_fee) / Decimal(1000)
                self.stdout.write(
                    f"  {pool.currency_code} (id={pool.resource_id}): "
                    f"{pool.gold_reserve} {gold} / "
                    f"{pool.resource_reserve} {pool.currency_code} "
                    f"(fee: {fee_pct}%)"
                )
            self.stdout.write("\nDry run — no trades executed.")
            return

        # 2. Seed test player + run trades + cleanup
        try:
            self._seed_test_player(gold, pools, vault)
            for pool in pools:
                self._test_pool(pool, vault, gold)
        finally:
            self._cleanup_test_data()

        # 3. Summary
        self._print_summary(pools)

    # ── Pool Detection ──────────────────────────────────────────────

    def _detect_pools(self, gold_currency, resource_filter):
        """Query all non-gold currencies for AMM pools."""
        currencies = CurrencyType.objects.using("xrpl").filter(is_gold=False)
        pools = []

        for ct in currencies:
            if resource_filter and ct.name.lower() != resource_filter.lower():
                continue

            self.stdout.write(
                f"  Checking {ct.currency_code}...", ending=""
            )
            try:
                info = get_amm_info(gold_currency, ct.currency_code)
            except Exception as e:
                self.stdout.write(f" error: {e}")
                continue

            if info is None:
                self.stdout.write(" no pool")
                continue

            r1 = info["reserve_1"]
            r2 = info["reserve_2"]
            if r1["currency"] == gold_currency:
                gold_res, resource_res = r1["value"], r2["value"]
            else:
                gold_res, resource_res = r2["value"], r1["value"]

            pools.append(PoolSummary(
                currency_code=ct.currency_code,
                resource_name=ct.name,
                resource_id=ct.resource_id,
                gold_reserve=gold_res,
                resource_reserve=resource_res,
                trading_fee=info["trading_fee"],
            ))
            fee_pct = Decimal(info["trading_fee"]) / Decimal(1000)
            self.stdout.write(
                f" found ({gold_res} gold / {resource_res} resource, "
                f"fee: {fee_pct}%)"
            )

        self.stdout.write("")
        return pools

    # ── Seed / Cleanup ──────────────────────────────────────────────

    def _seed_test_player(self, gold_currency, pools, vault):
        """Create game-state rows so the test player has funds to trade."""
        self.stdout.write("Seeding test player...")

        # Gold for buying
        FungibleGameState.objects.using("xrpl").create(
            currency_code=gold_currency,
            wallet_address=TEST_WALLET,
            location=FungibleGameState.LOCATION_CHARACTER,
            character_key=TEST_CHAR,
            balance=Decimal("1000000"),
        )

        # Resources for selling
        for pool in pools:
            FungibleGameState.objects.using("xrpl").create(
                currency_code=pool.currency_code,
                wallet_address=TEST_WALLET,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=TEST_CHAR,
                balance=Decimal("10000"),
            )

        self.stdout.write("  Test player seeded.\n")

    def _cleanup_test_data(self):
        """Remove all test data from the database."""
        self.stdout.write("\nCleaning up test data...")
        count_gs = FungibleGameState.objects.using("xrpl").filter(
            wallet_address=TEST_WALLET,
        ).delete()[0]
        count_tl = FungibleTransferLog.objects.using("xrpl").filter(
            from_wallet=TEST_WALLET,
        ).delete()[0]
        count_tl2 = FungibleTransferLog.objects.using("xrpl").filter(
            to_wallet=TEST_WALLET,
        ).delete()[0]
        count_xl = XRPLTransactionLog.objects.using("xrpl").filter(
            wallet_address=TEST_WALLET,
        ).delete()[0]
        self.stdout.write(
            f"  Removed {count_gs} game-state rows, "
            f"{count_tl + count_tl2} transfer logs, "
            f"{count_xl} tx logs."
        )

    # ── Per-Pool Test ───────────────────────────────────────────────

    def _test_pool(self, pool, vault, gold_currency):
        """Run buy and sell trades against one pool."""
        fee_pct = Decimal(pool.trading_fee) / Decimal(1000)
        self.stdout.write(
            f"--- {pool.resource_name} ({pool.currency_code}, "
            f"id={pool.resource_id}) ---"
        )
        self.stdout.write(
            f"Pool: {pool.gold_reserve} {gold_currency} / "
            f"{pool.resource_reserve} {pool.currency_code} "
            f"(fee: {fee_pct}%)\n"
        )

        self.stdout.write("  BUY (margin = gold dust)")
        for amount in BUY_AMOUNTS:
            result = self._run_trade("buy", pool, amount, vault)
            pool.results.append(result)
            self._print_result(result)

        self.stdout.write("  " + "=" * 72)
        self.stdout.write("  SELL (margin = resource dust)")
        for amount in SELL_AMOUNTS:
            result = self._run_trade("sell", pool, amount, vault)
            pool.results.append(result)
            self._print_result(result)

        self.stdout.write("")

    def _run_trade(self, direction, pool, amount, vault):
        """Execute one trade and verify accounting."""
        rid = pool.resource_id
        cc = pool.currency_code
        gold_currency = settings.XRPL_GOLD_CURRENCY_CODE

        # Get quote first (to check if trade is viable)
        try:
            if direction == "buy":
                quoted_gold = AMMService.get_buy_price(rid, amount)
            else:
                quoted_gold = AMMService.get_sell_price(rid, amount)
        except ValueError as e:
            return TradeResult(
                ok=True, direction=direction, amount=amount,
                currency_code=cc, resource_name=pool.resource_name,
                quoted_gold=0, actual_delta=Decimal("0"),
                margin=Decimal("0"), margin_unit="", tx_hash="",
                skipped=True, skip_reason=str(e),
            )

        # Skip sells that would yield 0 gold
        if direction == "sell" and quoted_gold <= 0:
            return TradeResult(
                ok=True, direction=direction, amount=amount,
                currency_code=cc, resource_name=pool.resource_name,
                quoted_gold=0, actual_delta=Decimal("0"),
                margin=Decimal("0"), margin_unit="", tx_hash="",
                skipped=True, skip_reason="0 gold yield",
            )

        # Pre-trade snapshot (on-chain)
        pre_balances = get_wallet_balances(vault)
        pre_vault_gold = pre_balances.get(gold_currency, Decimal("0"))
        pre_vault_resource = pre_balances.get(cc, Decimal("0"))

        # Execute
        try:
            if direction == "buy":
                result = AMMService.buy_resource(
                    TEST_WALLET, TEST_CHAR, rid, amount, quoted_gold, vault,
                )
            else:
                result = AMMService.sell_resource(
                    TEST_WALLET, TEST_CHAR, rid, amount, quoted_gold, vault,
                )
        except Exception as e:
            return TradeResult(
                ok=False, direction=direction, amount=amount,
                currency_code=cc, resource_name=pool.resource_name,
                quoted_gold=quoted_gold, actual_delta=Decimal("0"),
                margin=Decimal("0"), margin_unit="", tx_hash="",
                error=str(e),
            )

        # Brief pause to let ledger close
        time.sleep(1)

        # Post-trade snapshot (on-chain)
        post_balances = get_wallet_balances(vault)
        post_vault_gold = post_balances.get(gold_currency, Decimal("0"))
        post_vault_resource = post_balances.get(cc, Decimal("0"))

        tx_hash = result.get("tx_hash", "")

        # Calculate actual on-chain movement and margin
        if direction == "buy":
            # Vault spent gold to receive resource from AMM
            # Margin = gold charged to player - gold actually spent (gold dust kept)
            actual_gold_spent = pre_vault_gold - post_vault_gold
            margin = Decimal(quoted_gold) - actual_gold_spent
            ok = margin >= 0
            actual_delta = actual_gold_spent
            margin_unit = "gold"
        else:
            # Vault sent resource to AMM, received gold
            # Player gave `amount` (integer) resource, vault sent less (fractional) to AMM
            # Margin = resource taken from player - resource actually sent to AMM (resource dust kept)
            actual_resource_sent = pre_vault_resource - post_vault_resource
            margin = Decimal(amount) - actual_resource_sent
            ok = margin >= 0
            actual_delta = actual_resource_sent
            margin_unit = pool.resource_name.lower()

        return TradeResult(
            ok=ok, direction=direction, amount=amount,
            currency_code=cc, resource_name=pool.resource_name,
            quoted_gold=quoted_gold, actual_delta=actual_delta,
            margin=margin, margin_unit=margin_unit, tx_hash=tx_hash,
        )

    # ── Output ──────────────────────────────────────────────────────

    def _print_result(self, r):
        """Print one trade result line."""
        if r.skipped:
            self.stdout.write(
                f"  {r.direction.upper():4s} {r.amount:>5d} {r.resource_name:>10s} | "
                f"SKIP ({r.skip_reason})"
            )
            return

        if r.error:
            self.stdout.write(self.style.ERROR(
                f"  {r.direction.upper():4s} {r.amount:>5d} {r.resource_name:>10s} | "
                f"ERROR: {r.error}"
            ))
            return

        status = self.style.SUCCESS("PASS") if r.ok else self.style.ERROR("FAIL")
        margin_sign = "+" if r.margin >= 0 else ""

        if r.direction == "buy":
            self.stdout.write(
                f"  {r.direction.upper():4s} {r.amount:>5d} {r.resource_name:>10s} | "
                f"quoted: {r.quoted_gold:>6d} gold | "
                f"on-chain: {r.actual_delta:>10.3f} gold | "
                f"margin: {margin_sign}{r.margin:.3f} gold | "
                f"{status}"
            )
        else:
            self.stdout.write(
                f"  {r.direction.upper():4s} {r.amount:>5d} {r.resource_name:>10s} | "
                f"quoted: {r.quoted_gold:>6d} gold | "
                f"on-chain: {r.actual_delta:>10.3f} {r.margin_unit} | "
                f"margin: {margin_sign}{r.margin:.3f} {r.margin_unit} | "
                f"{status}"
            )

    def _print_summary(self, pools):
        """Print final summary."""
        total = 0
        passed = 0
        failed = 0
        skipped = 0
        total_margin = Decimal("0")

        for pool in pools:
            for r in pool.results:
                if r.skipped:
                    skipped += 1
                    continue
                if r.error:
                    failed += 1
                    total += 1
                    continue
                total += 1
                if r.ok:
                    passed += 1
                    total_margin += r.margin
                else:
                    failed += 1

        self.stdout.write("\n--- Summary ---")
        self.stdout.write(
            f"Trades: {total} run, {passed} passed, {failed} failed, "
            f"{skipped} skipped"
        )
        self.stdout.write(f"Total margin captured: +{total_margin:.3f} gold")

        if failed == 0:
            self.stdout.write(self.style.SUCCESS(
                "All assertions passed — game never loses money on trades."
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"{failed} FAILURES — game lost money on some trades!"
            ))
