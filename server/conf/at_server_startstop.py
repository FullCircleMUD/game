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
    _cleanup_renamed_scripts()
    _ensure_global_scripts()
    _close_stale_sessions()
    _clear_dungeon_instances()
    _restart_corpse_timers()
    _restart_purgatory_timers()
    _restart_mob_tickers()


# ================================================================== #
#  Global script management
# ================================================================== #

# The hourly telemetry pipeline. Each script ticks every 60s and fires its
# snapshot once per hour at its designated wall-clock slot (telemetry HH:00,
# saturation HH:05, spawn HH:10). Wall-clock alignment is enforced inside
# each script's at_repeat; the third tuple field is retained for backwards
# compatibility with existing `(key, path, _)` unpacking in cmd_services.py
# but is otherwise unused.
_PIPELINE_SCRIPTS = [
    # (key, typeclass_path, _unused)
    ("telemetry_aggregator_service", "typeclasses.scripts.telemetry_service.TelemetryAggregatorScript", 0),
    ("nft_saturation_service",       "typeclasses.scripts.nft_saturation_service.NFTSaturationScript",  0),
    ("unified_spawn_service",        "typeclasses.scripts.unified_spawn_service.UnifiedSpawnScript",    0),
]

# Other global service scripts. Each entry is (key, typeclass_path).
# These are unscheduled relative to each other — they're created
# immediately at boot and tick on their own intervals.
_GLOBAL_SCRIPTS = [
    ("regeneration_service",     "typeclasses.scripts.regeneration_service.RegenerationService"),
    ("survival_service",         "typeclasses.scripts.survival_service.SurvivalService"),
    ("day_night_service",        "typeclasses.scripts.day_night_service.DayNightService"),
    ("season_service",           "typeclasses.scripts.season_service.SeasonService"),
    ("weather_service",          "typeclasses.scripts.weather_service.WeatherService"),
    ("reallocation_service",     "typeclasses.scripts.reallocation_service.ReallocationServiceScript"),
    ("durability_decay_service", "typeclasses.scripts.durability_decay_service.DurabilityDecayService"),
]


_RENAMED_SCRIPT_KEYS = [
    # Old keys whose typeclass has been renamed/moved. Cleared on first boot
    # after the rename and a no-op forever after. Add an entry here when
    # renaming a global script so the old DB row doesn't linger as a ghost
    # service alongside the new one.
    "hunger_service",  # renamed -> survival_service
]


def _cleanup_renamed_scripts():
    """
    Delete any stale global script rows whose key has been renamed.

    Evennia stores scripts by key. Renaming a class without deleting the
    old row leaves a ghost service running on the old key alongside the
    new one. This sweep runs once on the first boot after a rename and
    is harmless on subsequent boots (the lookup just returns nothing).
    """
    from evennia import GLOBAL_SCRIPTS, logger

    for stale_key in _RENAMED_SCRIPT_KEYS:
        existing = getattr(GLOBAL_SCRIPTS, stale_key, None)
        if existing:
            existing.delete()
            logger.log_info(f"Global scripts: removed stale {stale_key}")


def _ensure_global_scripts():
    """
    Ensure all global service scripts exist. Creates any that are missing.

    Called from at_server_start() so scripts launch on every boot,
    independent of which world (test/game) is built. GLOBAL_SCRIPTS
    lookup returns None for missing scripts, so duplicates are impossible.

    Pipeline scripts (telemetry/saturation/spawn) are wall-clock aligned —
    see _create_pipeline_scripts(). We also sweep any duplicate rows left
    behind by earlier versions that used evennia.utils.delay() to stagger
    creation (that scheme could race reload windows and create extras).
    """
    from evennia import GLOBAL_SCRIPTS, create_script, logger

    for key, typeclass_path in _GLOBAL_SCRIPTS:
        existing = getattr(GLOBAL_SCRIPTS, key, None)
        if not existing:
            create_script(typeclass_path, key=key, obj=None)
            logger.log_info(f"Global scripts: started {key}")

    _dedupe_pipeline_scripts()
    _create_pipeline_scripts(skip_existing=True)


def _dedupe_pipeline_scripts():
    """
    Delete duplicate ScriptDB rows for pipeline keys, keeping the oldest.

    Earlier versions staggered pipeline script creation via
    evennia.utils.delay() whose callbacks did not survive reload, which
    could leave duplicate rows behind when reloads happened inside the
    stagger window. This sweep is a no-op when there are no duplicates.
    """
    from evennia import ScriptDB, logger

    for key, _, _ in _PIPELINE_SCRIPTS:
        rows = list(ScriptDB.objects.filter(db_key=key).order_by("id"))
        if len(rows) <= 1:
            continue
        keeper = rows[0]
        for row in rows[1:]:
            try:
                row.stop()
            except Exception:
                pass
            row.delete()
            logger.log_info(
                f"Pipeline dedupe: deleted duplicate {key} id={row.id}, "
                f"kept id={keeper.id}"
            )


def _create_pipeline_scripts(skip_existing=False):
    """
    Create the telemetry/saturation/spawn pipeline scripts.

    All three scripts tick every 60s and self-align to wall-clock minute
    slots (telemetry HH:00, saturation HH:05, spawn HH:10), so there is
    no creation-time stagger to preserve — just create them immediately.

    Args:
        skip_existing: If True, only create pipeline scripts that don't
            already exist. Used by the boot path (_ensure_global_scripts)
            so reload doesn't recreate running pipeline scripts. The
            services reset command passes False because it has already
            deleted the existing scripts.
    """
    from evennia import GLOBAL_SCRIPTS, create_script, logger

    for key, typeclass_path, _ in _PIPELINE_SCRIPTS:
        existing = getattr(GLOBAL_SCRIPTS, key, None)
        if existing and skip_existing:
            continue
        create_script(typeclass_path, key=key, obj=None)
        logger.log_info(f"Pipeline scripts: started {key}")


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
#  Corpse timer restart
# ================================================================== #

def _restart_corpse_timers():
    """
    Find all Corpse and QuitDrop objects and restart their unlock/despawn
    timers based on persisted timestamps.
    """
    from evennia import logger
    from evennia.objects.models import ObjectDB

    from typeclasses.world_objects.corpse import Corpse

    corpse_count = 0
    for obj in ObjectDB.objects.filter(
        db_typeclass_path__contains="corpse"
    ) | ObjectDB.objects.filter(
        db_typeclass_path__contains="quit_drop"
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
