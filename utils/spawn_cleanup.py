"""
Spawn cleanup utility — wipe all non-player-owned spawned items.

Removes all NFTs, gold, and resources from rooms, mobs, and containers
that were placed by the spawn system. Returns everything to RESERVE.
Player-owned items (on characters and in account banks) are never touched.

Called by the superuser ``wipe_spawns`` command. NOT called on server
restart — spawned loot survives restarts and is only cleared manually
or by ``soft_deploy_world`` (which does its own zone-level cleanup).

Usage:
    from utils.spawn_cleanup import clear_spawned_items
    clear_spawned_items()
"""


def _is_player_owned(obj):
    """
    Check if an Evennia object belongs to a player and should be preserved.

    Currently protected:
        - FCMCharacter (player characters)
        - AccountBank (player bank storage)
        - Corpse (may contain player loot)
    """
    from typeclasses.actors.character import FCMCharacter
    from typeclasses.accounts.account_bank import AccountBank
    from typeclasses.world_objects.corpse import Corpse
    return isinstance(obj, (FCMCharacter, AccountBank, Corpse))


def clear_spawned_items():
    """
    Clear all spawned items from the game world.

    Three-sweep approach:

    SWEEP 1 — Delete spawned NFT Evennia objects.
        Iterates all in-game NFT objects and deletes any that are NOT
        inside a player-owned object. The at_object_delete() hook on
        BaseNFTItem automatically calls NFTService.despawn(), which
        transitions the mirror DB row from SPAWNED → RESERVE.

    SWEEP 2 — Reset orphaned mirror DB rows.
        After sweep 1, queries the mirror DB for any rows still marked
        SPAWNED. These are "orphans" — the Evennia object was lost
        (e.g. server crash) but the mirror DB row was not updated.
        Calls the existing service despawn methods to move them back
        to RESERVE.

    SWEEP 3 — Clear local fungible state (db.gold, db.resources).
        Zeroes out gold and resources on all Evennia objects that are
        NOT player-owned. This keeps the local Evennia state in sync
        with the mirror DB (which was reset in sweep 2).
    """
    from django.conf import settings
    from evennia import logger
    from evennia.objects.models import ObjectDB

    from blockchain.xrpl.models import NFTGameState, FungibleGameState
    from blockchain.xrpl.services.nft import NFTService
    from blockchain.xrpl.services.gold import GoldService
    from blockchain.xrpl.services.resource import ResourceService
    from blockchain.xrpl import currency_cache
    from typeclasses.items.base_nft_item import BaseNFTItem

    vault = settings.XRPL_VAULT_ADDRESS

    # ── SWEEP 1 — delete spawned NFT Evennia objects ──
    nft_count = 0
    for obj in ObjectDB.objects.filter(
        db_typeclass_path__startswith="typeclasses.items."
    ):
        if not isinstance(obj, BaseNFTItem):
            continue
        loc = obj.location
        if _is_player_owned(loc):
            continue
        try:
            obj.delete()
            nft_count += 1
        except Exception as err:
            logger.log_err(
                f"Spawned cleanup: failed to delete {obj}: {err}"
            )

    if nft_count:
        logger.log_info(
            f"Spawned cleanup: deleted {nft_count} NFT object(s)"
        )

    # ── SWEEP 2 — orphaned mirror DB rows ──

    # NFTs still marked SPAWNED after sweep 1
    orphaned_nft_ids = list(
        NFTGameState.objects.filter(
            location=NFTGameState.LOCATION_SPAWNED,
        ).values_list("nftoken_id", flat=True)
    )

    orphan_nft_count = 0
    for nftoken_id in orphaned_nft_ids:
        try:
            NFTService.despawn(nftoken_id, None, None)
            orphan_nft_count += 1
        except ValueError:
            pass

    if orphan_nft_count:
        logger.log_info(
            f"Spawned cleanup: reset {orphan_nft_count} orphaned "
            f"NFT mirror row(s)"
        )

    # Gold still marked SPAWNED
    gold_rows = list(
        FungibleGameState.objects.filter(
            location=FungibleGameState.LOCATION_SPAWNED,
            currency_code=settings.XRPL_GOLD_CURRENCY_CODE,
        ).values("balance")
    )

    for row in gold_rows:
        try:
            GoldService.despawn(row["balance"], None, None, vault)
        except ValueError:
            pass

    if gold_rows:
        logger.log_info(
            f"Spawned cleanup: reset {len(gold_rows)} spawned gold row(s)"
        )

    # Resources still marked SPAWNED
    resource_rows = list(
        FungibleGameState.objects.filter(
            location=FungibleGameState.LOCATION_SPAWNED,
        ).exclude(
            currency_code=settings.XRPL_GOLD_CURRENCY_CODE,
        ).values("currency_code", "balance")
    )

    for row in resource_rows:
        try:
            resource_id = currency_cache.get_resource_id(row["currency_code"])
            if resource_id is not None:
                ResourceService.despawn(
                    resource_id, row["balance"], None, None, vault,
                )
        except ValueError:
            pass

    if resource_rows:
        logger.log_info(
            f"Spawned cleanup: reset {len(resource_rows)} spawned "
            f"resource row(s)"
        )

    # ── SWEEP 3 — clear local fungible state on world objects ──
    fungible_count = 0
    for obj in ObjectDB.objects.all():
        if _is_player_owned(obj):
            continue

        had_gold = getattr(obj.db, "gold", None)
        had_resources = getattr(obj.db, "resources", None)

        cleared = False
        if had_gold and had_gold > 0:
            obj.db.gold = 0
            cleared = True
        if had_resources and any(v > 0 for v in had_resources.values()):
            obj.db.resources = {}
            cleared = True

        if cleared:
            fungible_count += 1

    if fungible_count:
        logger.log_info(
            f"Spawned cleanup: cleared local fungible state on "
            f"{fungible_count} world object(s)"
        )
