"""
Rebuild XRPL testnet state after a network wipe.

Recreates all on-chain infrastructure from the game DB:
  - Fund issuer, vault, and FakeRLUSD wallets via testnet faucet
  - Configure issuer flags (DefaultRipple, Clawback, NFT minter)
  - Create trust lines for all game currencies
  - Issue fungible supply to vault (matching game DB totals)
  - Create AMM pools (resource + proxy token pools, 0% fee)
  - Mint NFTs and transfer to vault (5% royalty, update DB)

Usage:
    evennia testnet_reinit --settings settings --issuer-seed sEdXXX
    evennia testnet_reinit --settings settings --issuer-seed sEdXXX --dry-run
    evennia testnet_reinit --settings settings --issuer-seed sEdXXX --skip-amm
    evennia testnet_reinit --settings settings --issuer-seed sEdXXX --force
"""

import asyncio

from decimal import Decimal

import httpx

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum

from xrpl.asyncio.clients import AsyncWebsocketClient
from xrpl.asyncio.transaction import submit_and_wait
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.requests import AccountInfo
from xrpl.models.transactions import (
    AccountSet,
    AccountSetAsfFlag,
    AMMCreate,
    NFTokenAcceptOffer,
    NFTokenCreateOffer,
    NFTokenMint,
    NFTokenMintFlag,
    Payment,
    TrustSet,
)
from xrpl.wallet import Wallet

from blockchain.xrpl.models import (
    CurrencyType,
    FungibleGameState,
    NFTGameState,
    NFTItemType,
    ResourceSnapshot,
    XRPLTransactionLog,
)
from blockchain.xrpl.xrpl_tx import encode_currency_hex


# ─── Constants ──────────────────────────────────────────────────────
FAUCET_URL = "https://faucet.altnet.rippletest.net/accounts"
TRUST_LIMIT = "999999999999999"
AMM_TRADING_FEE = 0             # 0% LP fee on reinit
NFT_TRANSFER_FEE = 5000        # 5% royalty (XRPL scale: 50000 = 50%)
NFT_BASE_URI = "https://nft.fcmud.world/"
NFT_FLAGS = (
    NFTokenMintFlag.TF_TRANSFERABLE | NFTokenMintFlag.TF_BURNABLE
)
AMM_RESOURCE_DEPOSIT = Decimal("1000")  # base resource deposit per pool


class Command(BaseCommand):
    help = "Rebuild XRPL testnet state after a network wipe"
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--issuer-seed", required=True,
            help="Issuer wallet seed (not stored in Django settings)",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show what would be done without executing",
        )
        parser.add_argument(
            "--skip-amm", action="store_true",
            help="Skip AMM pool creation",
        )
        parser.add_argument(
            "--skip-nfts", action="store_true",
            help="Skip NFT minting and transfer",
        )
        parser.add_argument(
            "--force", action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.skip_amm = options["skip_amm"]
        self.skip_nfts = options["skip_nfts"]

        # ── Phase 1: Pre-flight ──────────────────────────────────────
        self._header("Phase 1: Pre-flight Checks")

        if not settings.IS_TESTNET:
            raise CommandError(
                "Refusing to run on mainnet. IS_TESTNET must be True."
            )

        issuer_seed = options["issuer_seed"]
        vault_seed = settings.XRPL_VAULT_WALLET_SEED
        faucet_seed = getattr(settings, "FAUCET_WALLET_SEED", "")

        if not vault_seed:
            raise CommandError("XRPL_VAULT_WALLET_SEED is not configured.")
        if not faucet_seed:
            raise CommandError("FAUCET_WALLET_SEED is not configured.")

        # Derive wallets from seeds
        self.issuer_wallet = Wallet.from_seed(issuer_seed)
        self.vault_wallet = Wallet.from_seed(vault_seed)
        self.faucet_wallet = Wallet.from_seed(faucet_seed)
        self.network_url = settings.XRPL_NETWORK_URL

        # Verify derived addresses match settings
        if self.issuer_wallet.address != settings.XRPL_ISSUER_ADDRESS:
            raise CommandError(
                f"Issuer seed derives address {self.issuer_wallet.address} "
                f"but settings has {settings.XRPL_ISSUER_ADDRESS}. "
                f"Wrong seed?"
            )
        if self.vault_wallet.address != settings.XRPL_VAULT_ADDRESS:
            raise CommandError(
                f"Vault seed derives address {self.vault_wallet.address} "
                f"but settings has {settings.XRPL_VAULT_ADDRESS}. "
                f"Wrong seed?"
            )

        # Gather stats
        currencies = list(
            CurrencyType.objects.using("xrpl").all()
            .values_list("currency_code", flat=True)
        )
        nft_count = NFTGameState.objects.using("xrpl").count()

        # Resource currencies (have a resource_id — used for resource AMM pools)
        self.resource_currencies = list(
            CurrencyType.objects.using("xrpl")
            .filter(resource_id__isnull=False)
            .values_list("currency_code", flat=True)
        )

        # Proxy token currencies (no resource_id, not gold, not PGold)
        self.proxy_currencies = list(
            CurrencyType.objects.using("xrpl")
            .filter(resource_id__isnull=True, is_gold=False)
            .exclude(currency_code=settings.XRPL_PGOLD_CURRENCY_CODE)
            .values_list("currency_code", flat=True)
        )

        self._info(f"Network:     {self.network_url}")
        self._info(f"Issuer:      {self.issuer_wallet.address}")
        self._info(f"Vault:       {self.vault_wallet.address}")
        self._info(f"FakeRLUSD:   {self.faucet_wallet.address}")
        self._info(f"Currencies:  {len(currencies)}")
        self._info(f"  Resources: {len(self.resource_currencies)}")
        self._info(f"  Proxy:     {len(self.proxy_currencies)}")
        self._info(f"NFTs:        {nft_count}")
        self._info(f"AMM pools:   {len(self.resource_currencies)} resource"
                    f" + {len(self.proxy_currencies)} proxy")

        # Check if issuer account already exists
        issuer_exists = asyncio.run(
            self._account_exists(self.issuer_wallet.address)
        )
        if issuer_exists:
            self._warn(
                "Issuer account already exists on-chain. "
                "This may not be a fresh wipe."
            )

        if self.dry_run:
            self._info("\n[DRY RUN] No changes will be made.")
            return

        if not options["force"]:
            confirm = input("\nProceed with testnet reinit? [y/N] ")
            if confirm.lower() != "y":
                self._info("Aborted.")
                return

        # ── Phase 2: Fund Wallets ────────────────────────────────────
        self._header("Phase 2: Fund Wallets")
        self._fund_wallet("Issuer", self.issuer_wallet.address)
        self._fund_wallet("Vault", self.vault_wallet.address)
        self._fund_wallet("FakeRLUSD", self.faucet_wallet.address)

        # ── Phase 3: Configure Issuer ────────────────────────────────
        self._header("Phase 3: Configure Issuer")
        asyncio.run(self._configure_issuer())

        # ── Phase 4: Trust Lines ─────────────────────────────────────
        self._header("Phase 4: Create Trust Lines")
        asyncio.run(self._create_trust_lines(currencies))

        # ── Phase 5: Issue Fungible Supply ───────────────────────────
        self._header("Phase 5: Issue Fungible Supply")
        asyncio.run(self._issue_fungible_supply(currencies))

        # ── Phase 6: AMM Pools ───────────────────────────────────────
        if self.skip_amm:
            self._header("Phase 6: AMM Pools [SKIPPED]")
        else:
            self._header("Phase 6: Create AMM Pools")
            asyncio.run(self._create_amm_pools())

        # ── Phase 7: NFTs ────────────────────────────────────────────
        if self.skip_nfts:
            self._header("Phase 7: NFTs [SKIPPED]")
        else:
            self._header("Phase 7: Mint & Reassign NFTs")
            asyncio.run(self._mint_and_reassign_nfts())

        # ── Phase 8: Cleanup ─────────────────────────────────────────
        self._header("Phase 8: Cleanup")
        orphaned = XRPLTransactionLog.objects.using("xrpl").filter(
            status="pending",
        ).update(status="orphaned_wipe")
        self._info(f"Marked {orphaned} pending transactions as orphaned.")

        self._header("DONE")
        self._ok("Testnet reinit complete.")

    # ================================================================ #
    #  Phase 2: Fund wallets via faucet
    # ================================================================ #

    def _fund_wallet(self, label, address):
        """Fund an account via the XRPL testnet faucet HTTP API."""
        self._info(f"  Funding {label} ({address})...")
        try:
            resp = httpx.post(
                FAUCET_URL,
                json={"destination": address},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            balance = data.get("amount", data.get("balance", "?"))
            self._ok(f"    Funded. Balance: {balance} XRP")
        except httpx.HTTPStatusError as e:
            # Some faucets return 200 with error, some return 4xx
            raise CommandError(
                f"Faucet request failed for {label}: {e.response.status_code} "
                f"{e.response.text}"
            )
        except Exception as e:
            raise CommandError(f"Faucet request failed for {label}: {e}")

        # Verify account exists
        exists = asyncio.run(self._account_exists(address))
        if not exists:
            raise CommandError(
                f"{label} account {address} not found after faucet funding."
            )

    # ================================================================ #
    #  Phase 3: Configure issuer
    # ================================================================ #

    async def _configure_issuer(self):
        """Set DefaultRipple, Clawback, and NFT minter on issuer."""
        async with AsyncWebsocketClient(self.network_url) as client:
            # DefaultRipple
            self._info("  Setting DefaultRipple...")
            tx = AccountSet(
                account=self.issuer_wallet.address,
                set_flag=AccountSetAsfFlag.ASF_DEFAULT_RIPPLE,
            )
            await submit_and_wait(tx, client, self.issuer_wallet)
            self._ok("    DefaultRipple enabled.")

            # Clawback
            self._info("  Setting AllowTrustLineClawback...")
            tx = AccountSet(
                account=self.issuer_wallet.address,
                set_flag=AccountSetAsfFlag.ASF_ALLOW_TRUSTLINE_CLAWBACK,
            )
            await submit_and_wait(tx, client, self.issuer_wallet)
            self._ok("    AllowTrustLineClawback enabled.")

            # NFT minter
            self._info(
                f"  Setting NFT minter to vault "
                f"({self.vault_wallet.address})..."
            )
            tx = AccountSet(
                account=self.issuer_wallet.address,
                nftoken_minter=self.vault_wallet.address,
            )
            await submit_and_wait(tx, client, self.issuer_wallet)
            self._ok("    NFT minter set.")

    # ================================================================ #
    #  Phase 4: Trust lines
    # ================================================================ #

    async def _create_trust_lines(self, currencies):
        """Create trust lines for all game currencies + FakeRLUSD."""
        issuer_addr = self.issuer_wallet.address

        async with AsyncWebsocketClient(self.network_url) as client:
            # Vault → Issuer for every game currency
            total = len(currencies)
            for i, cc in enumerate(currencies, 1):
                self._info(f"  [{i}/{total}] Vault trusts {cc}...")
                tx = TrustSet(
                    account=self.vault_wallet.address,
                    limit_amount=IssuedCurrencyAmount(
                        currency=encode_currency_hex(cc),
                        issuer=issuer_addr,
                        value=TRUST_LIMIT,
                    ),
                )
                await submit_and_wait(tx, client, self.vault_wallet)

            self._ok(f"    {total} vault trust lines created.")

            # Issuer → FakeRLUSD issuer (for receiving subscription payments)
            sub_currency = getattr(
                settings, "SUBSCRIPTION_CURRENCY_CODE", ""
            )
            sub_issuer = getattr(
                settings, "SUBSCRIPTION_CURRENCY_ISSUER", ""
            )
            if sub_currency and sub_issuer:
                self._info(
                    f"  Issuer trusts {sub_currency} "
                    f"(from {sub_issuer[:12]}...)..."
                )
                tx = TrustSet(
                    account=self.issuer_wallet.address,
                    limit_amount=IssuedCurrencyAmount(
                        currency=encode_currency_hex(sub_currency),
                        issuer=sub_issuer,
                        value=TRUST_LIMIT,
                    ),
                )
                await submit_and_wait(tx, client, self.issuer_wallet)
                self._ok("    Issuer FakeRLUSD trust line created.")
            else:
                self._warn(
                    "  Skipping FakeRLUSD trust line — "
                    "SUBSCRIPTION_CURRENCY_CODE or _ISSUER not configured."
                )

    # ================================================================ #
    #  Phase 5: Issue fungible supply
    # ================================================================ #

    async def _issue_fungible_supply(self, currencies):
        """Issue tokens to vault matching game DB totals."""
        issuer_addr = self.issuer_wallet.address
        vault_addr = self.vault_wallet.address

        async with AsyncWebsocketClient(self.network_url) as client:
            issued_count = 0
            for cc in currencies:
                # Sum all balances for this currency in the game DB
                total = (
                    FungibleGameState.objects.using("xrpl")
                    .filter(currency_code=cc)
                    .aggregate(total=Sum("balance"))["total"]
                ) or Decimal("0")

                if total <= 0:
                    continue

                self._info(f"  Issuing {total} {cc} to vault...")
                tx = Payment(
                    account=issuer_addr,
                    destination=vault_addr,
                    amount=IssuedCurrencyAmount(
                        currency=encode_currency_hex(cc),
                        value=str(total),
                        issuer=issuer_addr,
                    ),
                )
                result = await submit_and_wait(
                    tx, client, self.issuer_wallet
                )
                tx_result = result.result.get(
                    "meta", {}
                ).get("TransactionResult")
                if tx_result != "tesSUCCESS":
                    raise CommandError(
                        f"Payment failed for {cc}: {tx_result}"
                    )
                issued_count += 1

            self._ok(f"    Issued {issued_count} currencies to vault.")

    # ================================================================ #
    #  Phase 6: AMM pools
    # ================================================================ #

    async def _create_amm_pools(self):
        """Create resource and proxy token AMM pools."""
        issuer_addr = self.issuer_wallet.address
        gold_code = settings.XRPL_GOLD_CURRENCY_CODE
        pgold_code = settings.XRPL_PGOLD_CURRENCY_CODE

        async with AsyncWebsocketClient(self.network_url) as client:
            # ── Resource pools (FCMResource vs FCMGold) ──────────────
            self._info(f"  Creating {len(self.resource_currencies)} "
                       f"resource AMM pools...")
            for cc in self.resource_currencies:
                price = self._get_last_amm_price(cc)
                resource_deposit = AMM_RESOURCE_DEPOSIT
                gold_deposit = resource_deposit * price

                self._info(
                    f"    {cc}: {gold_deposit} {gold_code} / "
                    f"{resource_deposit} {cc} "
                    f"(price={price})"
                )
                await self._create_one_amm(
                    client, gold_code, gold_deposit,
                    cc, resource_deposit, issuer_addr,
                )

            # ── Proxy token pools (PGold vs proxy token) ─────────────
            if self.proxy_currencies:
                self._info(f"  Creating {len(self.proxy_currencies)} "
                           f"proxy token AMM pools...")
                for pc in self.proxy_currencies:
                    # Use game DB reserves to determine ratio, or default
                    proxy_deposit, pgold_deposit = (
                        self._get_proxy_pool_deposits(pc, pgold_code)
                    )

                    self._info(
                        f"    {pc}: {pgold_deposit} {pgold_code} / "
                        f"{proxy_deposit} {pc}"
                    )
                    await self._create_one_amm(
                        client, pgold_code, pgold_deposit,
                        pc, proxy_deposit, issuer_addr,
                    )

            self._ok("    AMM pools created.")

    async def _create_one_amm(self, client, code1, amount1,
                               code2, amount2, issuer_addr):
        """Create a single AMM pool. Catches 'already exists' errors."""
        tx = AMMCreate(
            account=self.vault_wallet.address,
            amount=IssuedCurrencyAmount(
                currency=encode_currency_hex(code1),
                value=str(amount1),
                issuer=issuer_addr,
            ),
            amount2=IssuedCurrencyAmount(
                currency=encode_currency_hex(code2),
                value=str(amount2),
                issuer=issuer_addr,
            ),
            trading_fee=AMM_TRADING_FEE,
        )
        try:
            result = await submit_and_wait(
                tx, client, self.vault_wallet
            )
            tx_result = result.result.get(
                "meta", {}
            ).get("TransactionResult")
            if tx_result != "tesSUCCESS":
                self._warn(f"      AMMCreate result: {tx_result}")
            else:
                self._ok(f"      Pool created.")
        except Exception as e:
            self._warn(f"      AMMCreate failed: {e}")

    def _get_last_amm_price(self, currency_code):
        """Get last known AMM buy price from ResourceSnapshot, or default 1."""
        snap = (
            ResourceSnapshot.objects.using("xrpl")
            .filter(currency_code=currency_code, amm_buy_price__isnull=False)
            .order_by("-hour")
            .values_list("amm_buy_price", flat=True)
            .first()
        )
        if snap and snap > 0:
            return snap
        return Decimal("1")  # default 1:1

    def _get_proxy_pool_deposits(self, proxy_code, pgold_code):
        """
        Determine deposit amounts for a proxy token AMM pool.

        Uses the initial reserve values from migration seed data as the
        target ratio. If FungibleGameState has current balances, use those
        to infer the pool split. Otherwise fall back to migration defaults.
        """
        # Look up the CurrencyType for this proxy to get initial_reserve
        # Since initial_reserve isn't a model field, we use the
        # FungibleGameState RESERVE balance as best proxy
        proxy_reserve = (
            FungibleGameState.objects.using("xrpl")
            .filter(
                currency_code=proxy_code,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            .aggregate(total=Sum("balance"))["total"]
        ) or Decimal("0")

        pgold_reserve = (
            FungibleGameState.objects.using("xrpl")
            .filter(
                currency_code=pgold_code,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            .aggregate(total=Sum("balance"))["total"]
        ) or Decimal("0")

        # Count how many proxy tokens exist (to split PGold evenly)
        proxy_count = len(self.proxy_currencies)

        if proxy_reserve > 0 and pgold_reserve > 0 and proxy_count > 0:
            # Split PGold evenly across all proxy pools
            pgold_per_pool = pgold_reserve / Decimal(proxy_count)
            # Use a portion of the proxy reserve (same fraction as original)
            proxy_deposit = min(proxy_reserve, Decimal("1000"))
            pgold_deposit = min(pgold_per_pool, Decimal("50000"))
        else:
            # Fallback defaults matching migration seed
            proxy_deposit = Decimal("1000")
            pgold_deposit = Decimal("25000")

        return proxy_deposit, pgold_deposit

    # ================================================================ #
    #  Phase 7: NFTs
    # ================================================================ #

    async def _mint_and_reassign_nfts(self):
        """Mint NFTs and transfer to vault, updating game DB."""
        nfts = list(
            NFTGameState.objects.using("xrpl")
            .select_related("item_type")
            .order_by("uri_id")
        )
        if not nfts:
            self._info("  No NFTs to mint.")
            return

        total = len(nfts)
        self._info(f"  Minting {total} NFTs...")
        nft_base_uri = NFT_BASE_URI

        async with AsyncWebsocketClient(self.network_url) as client:
            for i, nft in enumerate(nfts, 1):
                uri_str = f"{nft_base_uri}{nft.uri_id}"
                uri_hex = uri_str.encode("utf-8").hex().upper()

                # 1. Mint on issuer
                mint_tx = NFTokenMint(
                    account=self.issuer_wallet.address,
                    uri=uri_hex,
                    nftoken_taxon=nft.taxon,
                    transfer_fee=NFT_TRANSFER_FEE,
                    flags=NFT_FLAGS,
                )
                mint_result = await submit_and_wait(
                    mint_tx, client, self.issuer_wallet
                )
                tx_result = mint_result.result.get(
                    "meta", {}
                ).get("TransactionResult")
                if tx_result != "tesSUCCESS":
                    raise CommandError(
                        f"NFTokenMint failed for uri_id={nft.uri_id}: "
                        f"{tx_result}"
                    )

                # Extract new nftoken_id
                new_id = self._extract_nftoken_id(
                    mint_result.result.get("meta", {})
                )
                if not new_id:
                    raise CommandError(
                        f"Could not extract NFToken ID for "
                        f"uri_id={nft.uri_id}"
                    )

                # 2. Create sell offer (issuer → vault, 0 XRP)
                offer_tx = NFTokenCreateOffer(
                    account=self.issuer_wallet.address,
                    nftoken_id=new_id,
                    amount="0",
                    destination=self.vault_wallet.address,
                    flags=0x00000001,  # tfSellNFToken
                )
                offer_result = await submit_and_wait(
                    offer_tx, client, self.issuer_wallet
                )
                tx_result = offer_result.result.get(
                    "meta", {}
                ).get("TransactionResult")
                if tx_result != "tesSUCCESS":
                    raise CommandError(
                        f"NFTokenCreateOffer failed for "
                        f"uri_id={nft.uri_id}: {tx_result}"
                    )

                offer_id = self._extract_offer_id(
                    offer_result.result.get("meta", {})
                )
                if not offer_id:
                    raise CommandError(
                        f"Could not extract offer ID for "
                        f"uri_id={nft.uri_id}"
                    )

                # 3. Accept offer (vault)
                accept_tx = NFTokenAcceptOffer(
                    account=self.vault_wallet.address,
                    nftoken_sell_offer=offer_id,
                )
                accept_result = await submit_and_wait(
                    accept_tx, client, self.vault_wallet
                )
                tx_result = accept_result.result.get(
                    "meta", {}
                ).get("TransactionResult")
                if tx_result != "tesSUCCESS":
                    raise CommandError(
                        f"NFTokenAcceptOffer failed for "
                        f"uri_id={nft.uri_id}: {tx_result}"
                    )

                # 4. Update game DB
                old_id = nft.nftoken_id
                nft.nftoken_id = new_id
                nft.save(using="xrpl", update_fields=["nftoken_id"])

                if i % 10 == 0 or i == total:
                    self._info(f"    [{i}/{total}] minted + transferred")

        self._ok(f"    {total} NFTs minted and reassigned.")

    @staticmethod
    def _extract_nftoken_id(meta):
        """Extract the new NFToken ID from NFTokenMint metadata."""
        for node in meta.get("AffectedNodes", []):
            # Look for the NFTokenPage that was created or modified
            for action in ("CreatedNode", "ModifiedNode"):
                entry = node.get(action, {})
                if entry.get("LedgerEntryType") != "NFTokenPage":
                    continue
                fields = entry.get("FinalFields") or entry.get("NewFields")
                if not fields:
                    continue
                tokens = fields.get("NFTokens", [])
                if not tokens:
                    continue
                # The newly minted token is the one not in PreviousFields
                prev_fields = entry.get("PreviousFields", {})
                prev_tokens = {
                    t["NFToken"]["NFTokenID"]
                    for t in prev_fields.get("NFTokens", [])
                }
                for t in tokens:
                    tid = t["NFToken"]["NFTokenID"]
                    if tid not in prev_tokens:
                        return tid
                # If CreatedNode (new page), return last token
                if action == "CreatedNode":
                    return tokens[-1]["NFToken"]["NFTokenID"]
        return None

    @staticmethod
    def _extract_offer_id(meta):
        """Extract NFTokenOffer ID from transaction metadata."""
        for node in meta.get("AffectedNodes", []):
            created = node.get("CreatedNode", {})
            if created.get("LedgerEntryType") == "NFTokenOffer":
                return created.get("LedgerIndex")
        return None

    # ================================================================ #
    #  Helpers
    # ================================================================ #

    async def _account_exists(self, address):
        """Check if an XRPL account exists on the current network."""
        try:
            async with AsyncWebsocketClient(self.network_url) as client:
                response = await client.request(
                    AccountInfo(account=address, ledger_index="validated")
                )
                return "account_data" in response.result
        except Exception:
            return False

    def _header(self, text):
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(f"  {text}")
        self.stdout.write(f"{'=' * 60}")

    def _info(self, text):
        self.stdout.write(text)

    def _ok(self, text):
        self.stdout.write(self.style.SUCCESS(text))

    def _warn(self, text):
        self.stdout.write(self.style.WARNING(text))
