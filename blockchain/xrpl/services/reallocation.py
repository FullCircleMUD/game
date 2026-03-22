"""
Reallocation service — periodic SINK → RESERVE drain.

Moves all accumulated SINK balances back to RESERVE, making consumed
assets available for re-spawning. Currently drains 100% of all currencies
(gold + resources). A future evolution may burn a percentage of gold
to the issuer once vault signing is sorted.

Called by the ReallocationServiceScript on a daily timer.
"""

import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F

from blockchain.xrpl.models import FungibleGameState, FungibleTransferLog

logger = logging.getLogger("evennia")


def reallocate_sinks():
    """
    Drain all SINK → RESERVE. Returns summary dict.

    For each currency with a SINK balance:
      1. Credits vault RESERVE by the SINK amount
      2. Deletes the SINK row (zero-balance rows not kept)
      3. Logs a FungibleTransferLog with transfer_type="reallocation"

    Returns:
        list of dicts with currency_code, amount drained.
    """
    vault_address = settings.XRPL_VAULT_ADDRESS

    results = []

    with transaction.atomic(using="xrpl"):
        sink_rows = list(
            FungibleGameState.objects.using("xrpl")
            .select_for_update()
            .filter(
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_SINK,
            )
        )

        for row in sink_rows:
            cc = row.currency_code
            amount = row.balance

            # Credit RESERVE
            reserve_row, created = FungibleGameState.objects.using("xrpl").get_or_create(
                currency_code=cc,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
                defaults={"balance": amount},
            )
            if not created:
                FungibleGameState.objects.using("xrpl").filter(
                    pk=reserve_row.pk
                ).update(balance=F("balance") + amount)

            # Delete SINK row
            row.delete()

            # Log the transfer
            FungibleTransferLog.objects.using("xrpl").create(
                currency_code=cc,
                from_wallet=vault_address,
                to_wallet=vault_address,
                amount=amount,
                transfer_type="reallocation",
            )

            results.append({
                "currency_code": cc,
                "amount": amount,
            })

    if results:
        total = sum(r["amount"] for r in results)
        logger.info(
            f"Reallocation: drained {len(results)} SINK entries, "
            f"total {total} across all currencies"
        )
    else:
        logger.info("Reallocation: no SINK balances to drain")

    return results
