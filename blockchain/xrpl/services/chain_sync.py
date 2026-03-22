"""
XRPL Chain Sync Service.

Queries the vault wallet on-chain and syncs NFT state with the game
database. Also provides fungible reconciliation (read-only comparison).

Used by:
  - Superuser `sync_nfts` command (manual trigger)
  - Superuser `reconcile` command (fungible comparison)
  - Future: Evennia Script on a daily timer
"""

import asyncio
import logging
import re

from django.conf import settings
from django.db import transaction

from xrpl.asyncio.clients import AsyncWebsocketClient
from xrpl.models.requests import AccountNFTs

from decimal import Decimal

from blockchain.xrpl.models import NFTGameState, FungibleGameState, CurrencyType

logger = logging.getLogger("evennia")

# URI pattern: https://api.fcmud.world/nft/{game_id}
_NFT_URI_PATTERN = re.compile(r"/nft/(\d+)$")


def _hex_to_string(hex_str):
    """Decode a hex-encoded URI string."""
    result = []
    for i in range(0, len(hex_str), 2):
        code = int(hex_str[i:i + 2], 16)
        if code == 0:
            break
        result.append(chr(code))
    return "".join(result)


def _extract_game_id(uri_hex):
    """Extract game ID from a hex-encoded NFT URI. Returns int or None."""
    if not uri_hex:
        return None
    uri = _hex_to_string(uri_hex)
    match = _NFT_URI_PATTERN.search(uri)
    return int(match.group(1)) if match else None


async def _fetch_vault_nfts(network_url, vault_address):
    """Query all NFTs held by the vault wallet."""
    all_nfts = []
    async with AsyncWebsocketClient(network_url) as client:
        marker = None
        while True:
            request = AccountNFTs(
                account=vault_address,
                ledger_index="validated",
                limit=100,
            )
            if marker:
                request = AccountNFTs(
                    account=vault_address,
                    ledger_index="validated",
                    limit=100,
                    marker=marker,
                )
            response = await client.request(request)
            result = response.result
            all_nfts.extend(result.get("account_nfts", []))
            marker = result.get("marker")
            if not marker:
                break
    return all_nfts


def sync_nfts():
    """
    Sync vault NFTs from chain → game database.

    For each on-chain NFT:
      - If a placeholder row exists (nftoken_id = game_id string), update it
        with the real 64-char NFToken ID.
      - If no row exists for this NFToken ID, create a new RESERVE row.

    Returns:
        dict with keys: updated (int), created (int), unchanged (int),
                        skipped (int), on_chain_count (int)
    """
    vault_address = settings.XRPL_VAULT_ADDRESS
    network_url = settings.XRPL_NETWORK_URL

    # Fetch on-chain NFTs
    chain_nfts = asyncio.run(_fetch_vault_nfts(network_url, vault_address))

    updated = 0
    created = 0
    unchanged = 0
    skipped = 0

    with transaction.atomic(using="xrpl"):
        # Build lookup of existing rows by nftoken_id
        existing_by_id = {
            row.nftoken_id: row
            for row in NFTGameState.objects.using("xrpl").all()
        }

        for nft in chain_nfts:
            nftoken_id = nft["NFTokenID"]
            taxon = nft.get("nft_taxon", 0)
            game_id = _extract_game_id(nft.get("URI"))

            # Already tracked with real ID — nothing to do
            if nftoken_id in existing_by_id:
                unchanged += 1
                continue

            # Check for placeholder row (nftoken_id = "1", "2", etc.)
            if game_id is not None:
                placeholder_id = str(game_id)
                if placeholder_id in existing_by_id:
                    row = existing_by_id[placeholder_id]
                    row.nftoken_id = nftoken_id
                    row.taxon = taxon
                    row.save(using="xrpl")
                    # Update lookup so we don't double-process
                    del existing_by_id[placeholder_id]
                    existing_by_id[nftoken_id] = row
                    updated += 1
                    continue

            # No existing row — could not extract game_id from URI
            if game_id is None:
                skipped += 1
                continue

            # New NFT not in DB — create a RESERVE row
            new_row = NFTGameState(
                nftoken_id=nftoken_id,
                taxon=taxon,
                owner_in_game=vault_address,
                location="RESERVE",
                item_type=None,
                metadata={},
            )
            new_row.save(using="xrpl")
            existing_by_id[nftoken_id] = new_row
            created += 1

    return {
        "updated": updated,
        "created": created,
        "unchanged": unchanged,
        "skipped": skipped,
        "on_chain_count": len(chain_nfts),
    }



# ================================================================== #
#  Reconciliation
# ================================================================== #

def reconcile_fungibles():
    """
    Compare vault on-chain balances against game-state totals.

    For each currency, returns:
      - on_chain: Decimal — vault's actual balance on the XRPL ledger
      - game_reserve: Decimal — sum of RESERVE rows
      - game_distributed: Decimal — sum of CHARACTER + ACCOUNT + SPAWNED
      - game_sink: Decimal — sum of SINK rows
      - game_total: Decimal — sum of all locations
      - delta: Decimal — on_chain - game_total (should be 0)

    Delta should be zero. Positive = vault has uncounted assets (recent
    minting or AMM liquidity change). Negative = accounting bug (game DB
    thinks more exists than vault holds).

    Returns:
        list of dicts, one per currency (sorted by currency_code).
    """
    from blockchain.xrpl.xrpl_tx import get_wallet_balances

    vault_address = settings.XRPL_VAULT_ADDRESS

    # 1. On-chain vault balances (decoded currency codes → Decimal)
    chain_balances = get_wallet_balances(vault_address)

    # 2. Game-state totals per currency per location
    all_rows = FungibleGameState.objects.using("xrpl").all()

    reserve_totals = {}
    distributed_totals = {}
    sink_totals = {}

    distributed_locations = {
        FungibleGameState.LOCATION_CHARACTER,
        FungibleGameState.LOCATION_ACCOUNT,
        FungibleGameState.LOCATION_SPAWNED,
    }

    for row in all_rows:
        cc = row.currency_code
        bal = row.balance
        if row.location == FungibleGameState.LOCATION_RESERVE:
            reserve_totals[cc] = reserve_totals.get(cc, Decimal("0")) + bal
        elif row.location == FungibleGameState.LOCATION_SINK:
            sink_totals[cc] = sink_totals.get(cc, Decimal("0")) + bal
        elif row.location in distributed_locations:
            distributed_totals[cc] = distributed_totals.get(cc, Decimal("0")) + bal

    # 3. Build report — union of all currencies seen on-chain or in DB
    all_currencies = sorted(
        set(chain_balances.keys())
        | set(reserve_totals.keys())
        | set(distributed_totals.keys())
        | set(sink_totals.keys())
    )

    # Currency code → human name lookup
    name_lookup = {}
    for ct in CurrencyType.objects.using("xrpl").all():
        name_lookup[ct.currency_code] = ct.name

    results = []
    for cc in all_currencies:
        on_chain = chain_balances.get(cc, Decimal("0"))
        game_reserve = reserve_totals.get(cc, Decimal("0"))
        game_distributed = distributed_totals.get(cc, Decimal("0"))
        game_sink = sink_totals.get(cc, Decimal("0"))
        game_total = game_reserve + game_distributed + game_sink
        delta = on_chain - game_total

        results.append({
            "currency_code": cc,
            "name": name_lookup.get(cc, cc),
            "on_chain": on_chain,
            "game_reserve": game_reserve,
            "game_distributed": game_distributed,
            "game_sink": game_sink,
            "game_total": game_total,
            "delta": delta,
        })

    return results


# ================================================================== #
#  Reserve sync
# ================================================================== #

def sync_reserves():
    """
    Recalculate RESERVE from on-chain vault balances.

    For each currency:
        RESERVE = on_chain - (SPAWNED + ACCOUNT + CHARACTER + SINK)

    This corrects RESERVE for admin operations that change vault
    balances without going through the game DB (minting new tokens,
    adding/removing AMM liquidity).

    IMPORTANT: Run `reconcile` first to review deltas. Expected deltas
    come from admin operations. Unexpected deltas indicate accounting
    bugs — investigate before syncing.

    Returns:
        list of dicts with currency_code, old_reserve, new_reserve, delta.
    """
    from blockchain.xrpl.xrpl_tx import get_wallet_balances

    vault_address = settings.XRPL_VAULT_ADDRESS

    # 1. On-chain vault balances
    chain_balances = get_wallet_balances(vault_address)

    # 2. Sum non-reserve locations per currency
    non_reserve_totals = {}
    non_reserve_locations = {
        FungibleGameState.LOCATION_CHARACTER,
        FungibleGameState.LOCATION_ACCOUNT,
        FungibleGameState.LOCATION_SPAWNED,
        FungibleGameState.LOCATION_SINK,
    }

    all_rows = FungibleGameState.objects.using("xrpl").all()

    old_reserve = {}
    for row in all_rows:
        cc = row.currency_code
        if row.location == FungibleGameState.LOCATION_RESERVE:
            old_reserve[cc] = old_reserve.get(cc, Decimal("0")) + row.balance
        elif row.location in non_reserve_locations:
            non_reserve_totals[cc] = non_reserve_totals.get(cc, Decimal("0")) + row.balance

    # 3. Calculate new RESERVE per currency and update
    results = []
    all_currencies = sorted(
        set(chain_balances.keys())
        | set(non_reserve_totals.keys())
        | set(old_reserve.keys())
    )

    with transaction.atomic(using="xrpl"):
        for cc in all_currencies:
            on_chain = chain_balances.get(cc, Decimal("0"))
            non_reserve = non_reserve_totals.get(cc, Decimal("0"))
            new_reserve = on_chain - non_reserve
            old_val = old_reserve.get(cc, Decimal("0"))
            delta = new_reserve - old_val

            if delta != 0 and new_reserve > 0:
                # Update or create RESERVE row
                row, created = FungibleGameState.objects.using("xrpl").get_or_create(
                    currency_code=cc,
                    wallet_address=vault_address,
                    location=FungibleGameState.LOCATION_RESERVE,
                    defaults={"balance": new_reserve},
                )
                if not created:
                    row.balance = new_reserve
                    row.save(using="xrpl", update_fields=["balance", "updated_at"])
            elif delta != 0 and new_reserve <= 0:
                # Delete RESERVE row if it exists (balance would be 0 or negative)
                FungibleGameState.objects.using("xrpl").filter(
                    currency_code=cc,
                    wallet_address=vault_address,
                    location=FungibleGameState.LOCATION_RESERVE,
                ).delete()

            results.append({
                "currency_code": cc,
                "old_reserve": old_val,
                "new_reserve": max(new_reserve, Decimal("0")),
                "delta": delta,
            })

    return results
