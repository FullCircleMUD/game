"""
Recording the failures that need a person.

The happy path is already written down — on the ledger, and in the transfer
and transaction logs. This is the exceptions list, so there is one place to
ask "has anything failed?" rather than reading three.

Only record what someone could act on. A failure that leaves the player's
balances untouched on both sides is not one, however noisy it looks; a
failure that leaves their assets moved on-chain and unreflected in the game
is, because nothing but a person can put it right.

See design/database.md § What the ledger changes.
"""

import logging

from django.db import router, transaction

from blockchain.xrpl.models import ReconciliationFailure

logger = logging.getLogger("evennia")


def record_failure(operation, wallet_address, error, character_key=None,
                   currency_code=None, amount=None, tx_hash=None):
    """
    Write one row describing an operation that needs manual reconciliation.

    Never raises. This is called from an exception handler that is about to
    re-raise the real error, and a failure to write the record must not
    replace it — losing the note is bad, losing the exception is worse.

    Args:
        operation (str): the method that failed, e.g. "deposit_gold_from_chain".
        wallet_address (str): the player's wallet.
        error (Exception|str): what went wrong, for whoever picks this up.
        character_key (str): the character involved, where there is one.
        currency_code (str): gold or resource currency, where there is one.
        amount (Decimal|int): how much, where there is an amount.
        tx_hash (str): the on-chain transaction, where there is one.

    Returns:
        ReconciliationFailure: the row, or None if it could not be written.
    """
    try:
        with transaction.atomic(using=router.db_for_write(ReconciliationFailure)):
            return ReconciliationFailure.objects.create(
                operation=operation,
                wallet_address=wallet_address or "",
                character_key=character_key,
                currency_code=currency_code,
                amount=amount,
                tx_hash=tx_hash,
                error=str(error),
            )
    except Exception:
        logger.exception(
            f"Could not record a reconciliation failure for {operation} "
            f"({wallet_address}): the original error is being re-raised."
        )
        return None
