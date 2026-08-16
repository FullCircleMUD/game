"""
NFT token_id patch sweep — brings live game objects into line with the
NFTGameState mirror after sync_nfts has updated it.

The router's job is only to make sure the mirror is current (sync_nfts'
own chain-vs-DB reconciliation), then tell every shard "the mirror just
changed, check your own objects against it." Each shard does its own
local, already-tenant-scoped lookup — nothing about which objects need
patching is computed on the router or shipped over the bus. This avoids
the cross-shard-read constraint entirely (see
blockchain/xrpl/services/spawn/reader.py): the router never touches
ObjectDB in this flow at all.

Used by:
  - Superuser `sync_nfts` command, after it updates NFTGameState.
"""

import logging

from blockchain.xrpl.models import NFTGameState

logger = logging.getLogger("evennia")

MESSAGE_KIND = "nft_token_patch_sweep"


def dispatch_patch_sweep():
    """Tell every shard to reconcile its own objects against the mirror.

    Monolith runs the sweep locally and returns its count. Sharded mode
    broadcasts an (empty-payload) trigger to every shard in
    `settings.SHARD_URLS` and returns None — the sweep happens
    asynchronously on each shard as the message bus is polled, so there
    is no synchronous count to report from the router.
    """
    from evennia_shards import ROLE_MONOLITH, get_role

    if get_role() == ROLE_MONOLITH:
        return apply_local_patches()

    from django.conf import settings

    from evennia_shards import send_message

    for shard_id in settings.SHARD_URLS:
        try:
            send_message(MESSAGE_KIND, {}, to_shard=shard_id)
        except Exception as err:
            logger.error(
                f"nft_token_patch: failed dispatching sweep trigger to "
                f"{shard_id}: {type(err).__name__}: {err}"
            )
    return None


def apply_local_patches():
    """Patch this process's own BaseNFTItem objects against the mirror.

    Only place this module instantiates game objects — always this
    process's own resident rows, found via the tenant auto-filter (a
    shard sees only its own; the router, or monolith, sees everything).

    Restricted to the BaseNFTItem typeclass tree (`typeclasses.items.`)
    — pets use a separate NFTPetMirrorMixin/token_id and are not covered
    here, matching sync_nfts' historical scope.

    Returns:
        int — objects patched.
    """
    from evennia.objects.models import ObjectDB
    from typeclasses.items.base_nft_item import BaseNFTItem

    patched = 0
    for obj in ObjectDB.objects.get_by_attribute("token_id"):
        if not isinstance(obj, BaseNFTItem):
            continue

        token_id = obj.token_id
        if token_id is None:
            continue
        token_str = str(token_id)
        if len(token_str) == 64:
            continue  # already a real NFToken ID

        try:
            game_id = int(token_str)
        except ValueError:
            continue

        row = (
            NFTGameState.objects.using("xrpl")
            .filter(uri_id=game_id)
            .first()
        )
        if row is None or len(row.nftoken_id) != 64:
            continue  # mirror doesn't have a real ID for this one yet

        obj.token_id = row.nftoken_id
        patched += 1
        logger.info(
            f"nft_token_patch: patched #{obj.id} token_id "
            f"{token_str} -> {row.nftoken_id[:16]}..."
        )

    return patched
