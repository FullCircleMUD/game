"""
Server startstop hooks

This module contains functions called by Evennia at various
points during its startup, reload and shutdown sequence. It
allows for customizing the server operation as desired.

This module must contain at least these global functions:

at_server_init()
at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()

"""


def at_server_init():
    """
    This is called first as the server is starting up, regardless of how.
    """
    _register_dungeon_templates()


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    _ensure_global_scripts()
    _close_stale_sessions()
    _clear_spawned_items()
    _clear_dungeon_instances()
    _restart_corpse_timers()
    _restart_purgatory_timers()
    _restart_mob_tickers()


# ================================================================== #
#  Global script management
# ================================================================== #

# Scripts that should always be running. Each entry is (key, typeclass_path).
_GLOBAL_SCRIPTS = [
    ("regeneration_service", "typeclasses.scripts.regeneration_service.RegenerationService"),
    ("hunger_service", "typeclasses.scripts.hunger_service.HungerService"),
    ("day_night_service", "typeclasses.scripts.day_night_service.DayNightService"),
    ("season_service", "typeclasses.scripts.season_service.SeasonService"),
    ("weather_service", "typeclasses.scripts.weather_service.WeatherService"),
    ("telemetry_aggregator_service", "typeclasses.scripts.telemetry_service.TelemetryAggregatorScript"),
    ("reallocation_service", "typeclasses.scripts.reallocation_service.ReallocationServiceScript"),
    ("durability_decay_service", "typeclasses.scripts.durability_decay_service.DurabilityDecayService"),
    ("nft_saturation_service", "typeclasses.scripts.nft_saturation_service.NFTSaturationScript"),
    ("unified_spawn_service", "typeclasses.scripts.unified_spawn_service.UnifiedSpawnScript"),
]


def _ensure_global_scripts():
    """
    Ensure all global service scripts exist. Creates any that are missing.

    Called from at_server_start() so scripts launch on every boot,
    independent of which world (test/game) is built. GLOBAL_SCRIPTS
    lookup returns None for missing scripts, so duplicates are impossible.
    """
    from evennia import GLOBAL_SCRIPTS, create_script, logger

    for key, typeclass_path in _GLOBAL_SCRIPTS:
        existing = getattr(GLOBAL_SCRIPTS, key, None)
        if not existing:
            create_script(typeclass_path, key=key, obj=None)
            logger.log_info(f"Global scripts: started {key}")


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    pass


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    pass


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    pass


def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    pass


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    pass


# ================================================================== #
#  Stale session cleanup (telemetry)
# ================================================================== #

def _close_stale_sessions():
    """Close any player sessions left open from a server crash."""
    from blockchain.xrpl.services.telemetry import TelemetryService

    TelemetryService.close_stale_sessions()


# ================================================================== #
#  Dungeon instance cleanup
# ================================================================== #

def _clear_dungeon_instances():
    """
    Collapse all dungeon instances on server start.

    Any instances that survived a crash or restart are stale —
    collapse them to clean up rooms, exits, and mobs.
    """
    from evennia import logger, ScriptDB

    from typeclasses.scripts.dungeon_instance import DungeonInstanceScript

    count = 0
    for script in ScriptDB.objects.filter(
        db_typeclass_path__contains="dungeon_instance"
    ):
        if not isinstance(script, DungeonInstanceScript):
            continue
        if script.state == "done":
            script.delete()
            continue
        try:
            script.collapse_instance()
            count += 1
        except Exception as err:
            logger.log_err(
                f"Dungeon cleanup: failed to collapse {script.key}: {err}"
            )

    if count:
        logger.log_info(
            f"Dungeon cleanup: collapsed {count} stale dungeon instance(s)"
        )


# ================================================================== #
#  Spawned item cleanup
# ================================================================== #

def _is_player_owned(obj):
    """
    Check if an Evennia object belongs to a player and should be
    preserved across restarts.

    Currently protected:
        - FCMCharacter (player characters)
        - AccountBank (player bank storage)

    TODO: When implemented, also protect:
        - PetNFTItem (pets owned by characters — carry fungibles)
        - ContainerNFTItem / backpacks (containers in character/pet/account
          inventory — carry fungibles and NFTs)
    """
    from typeclasses.actors.character import FCMCharacter
    from typeclasses.accounts.account_bank import AccountBank
    from typeclasses.world_objects.corpse import Corpse
    # TODO: add PetNFTItem, ContainerNFTItem once they exist
    return isinstance(obj, (FCMCharacter, AccountBank, Corpse))


def _clear_spawned_items():
    """
    Clear all spawned items from the game world on server start.

    Spawned items are game-world instances of NFTs, gold, and resources
    that were placed by the game system (mob loot, room rewards, chests)
    but haven't been picked up by a player. These are ephemeral — they
    should not persist across server restarts.

    Items owned by players (on characters or in account banks) are
    NEVER touched.

    Three-sweep approach:

    SWEEP 1 — Delete spawned NFT Evennia objects.
        Iterates all in-game NFT objects and deletes any that are NOT
        inside a player-owned object. The at_object_delete() hook on
        BaseNFTItem automatically calls NFTService.despawn(), which
        transitions the mirror DB row from SPAWNED → RESERVE and wipes
        the item's identity (item_type=None, metadata={}).

    SWEEP 2 — Reset orphaned mirror DB rows.
        After sweep 1, queries the mirror DB for any rows still marked
        SPAWNED. These are "orphans" — the Evennia object was lost
        (e.g. server crash) but the mirror DB row was not updated.
        Calls the existing service despawn methods to move them back
        to RESERVE.

    SWEEP 3 — Clear local fungible state (db.gold, db.resources).
        Zeroes out gold and resources on all Evennia objects that are
        NOT player-owned. This keeps the local Evennia state in sync
        with the mirror DB (which was reset in sweep 2). Without this,
        rooms would still show fungibles after restart even though the
        DB backing was cleared.
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

    # -------------------------------------------------------------- #
    #  SWEEP 1 — delete spawned NFT Evennia objects
    #
    #  All item typeclasses live under typeclasses.items.* so we use
    #  a db_typeclass_path prefix filter to narrow the queryset, then
    #  isinstance() to confirm it's actually a BaseNFTItem subclass.
    #
    #  Items inside a player-owned object are skipped — those belong
    #  to players and must never be cleared.
    #
    #  Everything else (items in rooms, on mobs, in chests, or with
    #  no location) is deleted. The at_object_delete() hook fires
    #  NFTService.despawn() which updates the mirror DB automatically.
    #
    #  TODO: When ContainerNFTItem exists, items inside a container
    #  that is itself inside a player-owned object must also be
    #  preserved. _is_player_owned() on the container's location
    #  handles the direct case, but nested containers may need
    #  recursive location traversal.
    # -------------------------------------------------------------- #
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

    # -------------------------------------------------------------- #
    #  SWEEP 2 — orphaned mirror DB rows
    #
    #  If the server crashed, Evennia objects may have been lost while
    #  the mirror DB still shows them as SPAWNED. Sweep 1 can't catch
    #  these because there's no Evennia object to delete.
    #
    #  We query each mirror table for remaining SPAWNED rows and call
    #  the existing service despawn methods to return them to RESERVE.
    # -------------------------------------------------------------- #

    # --- NFTs still marked SPAWNED after sweep 1 ---
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

    # --- Gold still marked SPAWNED ---
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

    # --- Resources still marked SPAWNED ---
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

    # -------------------------------------------------------------- #
    #  SWEEP 3 — clear local fungible state on world objects
    #
    #  Sweeps 1-2 reset the mirror DB, but Evennia objects (rooms,
    #  mobs, etc.) still have db.gold and db.resources set from
    #  before the restart. Clear these so the local state matches
    #  the now-empty SPAWNED pool.
    #
    #  Player-owned objects are skipped — their fungibles are tracked
    #  as CHARACTER rows in the mirror DB, not SPAWNED, so they
    #  were never touched by sweeps 1-2.
    #
    #  TODO: When PetNFTItem and ContainerNFTItem exist, they will
    #  also hold fungibles and must be skipped here. Update
    #  _is_player_owned() to include them.
    # -------------------------------------------------------------- #
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


# ================================================================== #
#  Corpse timer restart
# ================================================================== #

def _restart_corpse_timers():
    """
    Find all Corpse objects and restart their unlock/despawn timers
    based on persisted timestamps.
    """
    from evennia import logger
    from evennia.objects.models import ObjectDB

    from typeclasses.world_objects.corpse import Corpse

    corpse_count = 0
    for obj in ObjectDB.objects.filter(
        db_typeclass_path__contains="corpse"
    ):
        if not isinstance(obj, Corpse):
            continue
        try:
            obj.restart_timers()
            corpse_count += 1
        except Exception as err:
            logger.log_err(f"Corpse timer restart failed for {obj}: {err}")

    if corpse_count:
        logger.log_info(
            f"Corpse restart: restarted timers on {corpse_count} corpse(s)"
        )


# ================================================================== #
#  Purgatory release timer restart
# ================================================================== #

def _restart_purgatory_timers():
    """
    Find all characters currently in a purgatory room and restart
    their release timers (1 minute from now, since we don't know
    how much time remained).
    """
    from evennia import logger
    from evennia.objects.models import ObjectDB
    from evennia.utils.utils import delay

    from typeclasses.actors.character import FCMCharacter
    from typeclasses.terrain.rooms.room_purgatory import RoomPurgatory

    count = 0
    for obj in ObjectDB.objects.filter(
        db_typeclass_path__contains="character"
    ):
        if not isinstance(obj, FCMCharacter):
            continue
        if isinstance(obj.location, RoomPurgatory):
            if not obj.home:
                obj.home = obj._get_limbo()
                logger.log_warn(
                    f"Purgatory restart: {obj.key} had no home, set to Limbo"
                )
            delay(FCMCharacter.PURGATORY_DURATION, obj._purgatory_release)
            count += 1

    if count:
        logger.log_info(
            f"Purgatory restart: scheduled release for {count} character(s)"
        )


# ================================================================== #
#  Dungeon template registration
# ================================================================== #

def _register_dungeon_templates():
    """
    Import all dungeon templates so they register themselves.

    Called from at_server_init() to ensure templates are available
    even on restarts (not just during world building).
    """
    import world.dungeons.templates.cave_dungeon  # noqa: F401
    import world.dungeons.templates.deep_woods_passage  # noqa: F401
    import world.dungeons.templates.lake_passage  # noqa: F401
    import world.dungeons.templates.rat_cellar  # noqa: F401


# ================================================================== #
#  Mob AI ticker restart
# ================================================================== #

def _restart_mob_tickers():
    """
    Find all CombatMobs and restart their AI tickers.

    Living mobs with a location get their AI restarted.
    Dead mobs get their respawn rescheduled.
    """
    from evennia import logger
    from evennia.objects.models import ObjectDB
    from evennia.utils.utils import delay

    from typeclasses.actors.mob import CombatMob

    alive_count = 0
    dead_count = 0
    for obj in ObjectDB.objects.filter(
        db_typeclass_path__contains="mobs."
    ):
        if not isinstance(obj, CombatMob):
            continue
        if obj.is_alive and obj.location:
            obj.start_ai()
            alive_count += 1
        elif not obj.is_alive:
            delay(5, obj._respawn)
            dead_count += 1

    if alive_count or dead_count:
        logger.log_info(
            f"Mob restart: {alive_count} alive ticker(s), "
            f"{dead_count} dead mob(s) queued for respawn"
        )
