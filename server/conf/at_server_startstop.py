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
    _start_message_bus()
    _start_scripts_for_this_role()
    _close_stale_sessions()
    _clear_dungeon_instances()
    _restart_corpse_timers()
    _restart_purgatory_timers()
    _restart_mob_tickers()


def _start_message_bus():
    """Start the cross-shard message bus polling loop.

    One of the two calls the shards library asks a consumer to make (the
    other being the role accessors) — see the library's
    docs/library-scope-and-mandates.md. Without it the Postgres `messages`
    table is never polled, so nothing addressed to this process is ever
    processed: spawn placements dispatched by the router, and the
    `flush_from_cache` the library sends after a cross-shard move to drop
    the destination's stale view of the arrival room.

    Skipped in monolith, where there is nothing to poll for — a process
    cannot message itself, and `send_message()` refuses same-shard
    delivery outright.
    """
    from evennia_shards import ROLE_MONOLITH, get_role, start_message_bus

    if get_role() == ROLE_MONOLITH:
        return

    from server.conf.messaging import FCMMessageHandler

    start_message_bus(FCMMessageHandler())


# ================================================================== #
#  Global script management
# ================================================================== #

# --- Role sets -----------------------------------------------------
#
# Which deployment roles a script runs on. "monolith" is a first-class
# role, never derived from the other two — that is what makes it
# possible to declare a script needed only in a sharded deployment.
#
# A ScriptDB row is shared by every process (ScriptDB is not
# tenant-scoped), but each process attaches its own LoopingCall, so a
# script listed for N roles ticks once per process. Whether that is
# correct depends on the script: safe for anything holding no
# persistent state and acting only on process-local data (e.g. walking
# SESSION_HANDLER); not safe for anything querying the world or
# emitting a once-only side effect. See
# libraries/evennia-shards/docs/shard-settings.md
# § Global scripts run one instance per process.

ALL_ROLES            = ("shard", "router", "monolith")
SHARDED_ONLY_ALL     = ("shard", "router")    # not needed in single-process mode
SHARDED_ONLY_SHARD   = ("shard",)
SHARDED_ONLY_ROUTER  = ("router",)
GAME_ROLES           = ("shard", "monolith")  # anywhere characters live
ROUTER_ROLES         = ("router", "monolith")


# --- Script declarations -------------------------------------------
#
# One entry per script: (key, typeclass_path, roles, tags)
#
#   roles — where it runs, from the sets above.
#   tags  — orthogonal attributes. "pipeline" marks the wall-clock
#           aligned hourly scripts, which have their own reset path and
#           duplicate sweep. A script's tags say nothing about where it
#           runs; that is the roles column's job.

_SCRIPTS = [
    ("regeneration_service", "typeclasses.scripts.regeneration_service.RegenerationService", GAME_ROLES, ()),
    ("survival_service",     "typeclasses.scripts.survival_service.SurvivalService",         GAME_ROLES, ()),
    ("durability_decay_service", "typeclasses.scripts.durability_decay_service.DurabilityDecayService", GAME_ROLES, ()),
    ("day_night_service",        "typeclasses.scripts.day_night_service.DayNightService",               GAME_ROLES, ()),
    ("season_service",           "typeclasses.scripts.season_service.SeasonService",                    GAME_ROLES, ()),
    ("weather_service",          "typeclasses.scripts.weather_service.WeatherService",                  GAME_ROLES, ()),

    # Drains SINK -> RESERVE daily so spent currency can be re-spawned.
    # Must run exactly once per cluster: it credits RESERVE by the SINK
    # balance and deletes the SINK row, so a second process running it
    # concurrently would credit the same amount twice and mint currency
    # that was never spent. Exactly-once here comes from only one role
    # being tagged, not from locking — the library mandates a single
    # router, and select_for_update would not save us if there were two.
    # Touches only the xrpl database (FungibleGameState /
    # FungibleTransferLog), never ObjectDB, so it needs nothing that
    # lives on a shard.
    ("reallocation_service",     "typeclasses.scripts.reallocation_service.ReallocationServiceScript",  ROUTER_ROLES, ()),

    # Writes one economy snapshot row per hour. Reads only the xrpl
    # mirror database — the module imports no evennia at all, so it
    # cannot touch ObjectDB, rooms or characters, and even "who is
    # online" comes from PlayerSession rows rather than SESSION_HANDLER.
    # Every shard writes its own PlayerSession rows to that shared
    # mirror, so one reader sees the whole cluster and every process
    # would compute identical numbers. Runs once because computing the
    # same aggregate four times an hour is waste, not because a shard
    # would get it wrong.
    #
    # Note self.db.last_run_hour reads like a cross-process double-fire
    # guard but is not one — attribute caching means a shard never sees
    # the router's write. It guards within a process only.
    ("telemetry_aggregator_service", "typeclasses.scripts.telemetry_service.TelemetryAggregatorScript", ROUTER_ROLES, ("pipeline",)),

    # Writes one saturation snapshot per tracked spell, recipe and item
    # type per hour. Router-only because the denominator is a
    # cluster-wide fact: three of its methods count the 7-day-active
    # population, and on a shard the auto-filter would return that
    # shard's characters alone — saturation computed against a fraction
    # of the players, so the spawn algorithm over-spawns for a world it
    # cannot see. The router is the only role that runs unscoped.
    #
    # Reading the whole cluster's characters is only acceptable because
    # every attribute read goes through _character_attributes() in
    # nft_saturation.py, which projects values rather than materialising
    # typeclass instances. Iterating characters here would pull the
    # cluster's active population into the router's idmapper, which the
    # library forbids outright (consumer-constraints.md).
    #
    # self.db.last_run_hour is a within-process guard only, same as
    # telemetry above — it is not what makes this run once.
    ("nft_saturation_service",       "typeclasses.scripts.nft_saturation_service.NFTSaturationScript",  ROUTER_ROLES, ("pipeline",)),

    # Keeps the Render-hosted cosigner from spinning down. Gated on this
    # process having a logged-in session, and "is anyone online" is a
    # cluster-wide fact that no single process can answer — a session
    # moves to a shard on IC, so the router sees nobody while players are
    # in-game, and the shards see nobody while a player sits at character
    # select. Runs everywhere rather than coordinating: the ping is
    # idempotent, deferToThread'd, and double-gated on settings, so the
    # cost of N processes pinging is a few redundant HTTP GETs.
    # Retires when the cosigner moves off Render's free tier — see
    # ops/DEVELOPMENT/DEPLOYMENT.md.
    ("cosigner_keepalive_service", "typeclasses.scripts.cosigner_keepalive_service.CosignerKeepAliveScript", ALL_ROLES, ()),

    # Decides how much of each item the world needs and which targets
    # receive it, then routes those placements to the shards owning them.
    # Router-only because both halves of that decision need the whole
    # cluster in view: the budget derives from cluster-wide consumption and
    # saturation, and allocation is proportional to headroom across every
    # shard's targets at once. A shard would see only its own slice and
    # distribute the entire world's budget into it.
    #
    # It reads without materialising anything — spawn/reader.py projects
    # values rather than instantiating typeclasses — so the routing process
    # never pulls another shard's objects into its idmapper.
    #
    # Shards deliberately run no counterpart script. Placements arrive as
    # `spawn_placements` bus messages and are carried out by
    # FCMMessageHandler, driven by the message bus LoopingCall started in
    # _start_message_bus() above. The library chose a LoopingCall over a
    # Script for the bus precisely to avoid a component that can sit wedged
    # in "stopped" while the game looks healthy; a shard-side script would
    # reintroduce exactly that.
    ("unified_spawn_service",      "typeclasses.scripts.unified_spawn_service.UnifiedSpawnScript",           ROUTER_ROLES, ("pipeline",)),
]


def _select_scripts(role=None, tag=None):
    """
    Return the _SCRIPTS entries matching both filters.

    Filters are ANDed, and either may be omitted:

        _select_scripts(role="shard")                 every script on shards
        _select_scripts(tag="pipeline")               every pipeline script
        _select_scripts(role="shard", tag="pipeline") pipeline scripts on shards

    ANDing is what makes "restart the pipeline on this process" express
    itself correctly — on a role that owns no pipeline scripts it
    selects nothing rather than starting scripts that don't belong there.
    """
    out = []
    for key, typeclass_path, roles, tags in _SCRIPTS:
        if role is not None and role not in roles:
            continue
        if tag is not None and tag not in tags:
            continue
        out.append((key, typeclass_path))
    return out


def start_scripts(role=None, tag=None):
    """
    Create (or re-attach) the scripts matching role/tag on this process.

    Called from at_server_start() so scripts launch on every boot,
    independent of which world (test/game) is built. GLOBAL_SCRIPTS
    lookup returns None for missing scripts, so duplicates are impossible.
    """
    from evennia import GLOBAL_SCRIPTS, create_script, logger

    for key, typeclass_path in _select_scripts(role=role, tag=tag):
        existing = getattr(GLOBAL_SCRIPTS, key, None)
        if not existing:
            create_script(typeclass_path, key=key, obj=None)
            logger.log_info(f"Global scripts: started {key}")
        elif not (existing.ndb._task and existing.ndb._task.running):
            # Row is active in DB but its LoopingCall isn't attached — happens
            # after hard kills where Evennia's restart-active-scripts walk
            # didn't complete. start() is idempotent (see DefaultScript._start_task).
            existing.start()
            logger.log_info(f"Global scripts: re-attached LoopingCall for {key}")


def safe_stop_scripts(role=None, tag=None):
    """
    Stop the scripts matching role/tag, leaving their ScriptDB rows intact.

    Stopping detaches this process's LoopingCall; other processes keep
    their own. A script that is already stopped, or whose row does not
    exist, is skipped rather than raising.
    """
    from evennia import GLOBAL_SCRIPTS, logger

    for key, _typeclass_path in _select_scripts(role=role, tag=tag):
        existing = getattr(GLOBAL_SCRIPTS, key, None)
        if not existing:
            continue
        try:
            existing.stop()
        except Exception:
            logger.log_trace(f"Global scripts: failed to stop {key}")
            continue
        logger.log_info(f"Global scripts: stopped {key}")


def _start_scripts_for_this_role():
    """
    Boot entry point: start everything declared for this process's role.

    get_role() returns "monolith" when SHARDS_ROLE is unset, so a
    single-process install starts everything tagged for monolith.
    """
    from evennia_shards import get_role

    start_scripts(role=get_role())


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

    Per-role behaviour:
      - router: skip entirely. The router doesn't own game-world corpses.
      - shard:  scope the query to this shard via shard_id. Corpses are
        in-world objects that live on the same shard as the room they
        dropped in; cross-shard restart is never correct.
      - monolith: no shard scoping; matches the pre-sharding behaviour.
    """
    from evennia_shards import ROLE_MONOLITH, ROLE_ROUTER, get_role, get_shard_id

    role = get_role()
    if role == ROLE_ROUTER:
        return

    from evennia import logger
    from evennia.objects.models import ObjectDB

    from typeclasses.world_objects.corpse import Corpse

    # Union of corpse and quit_drop typeclass paths via the | operator
    # on two filter() querysets of the same model. Django composes this
    # into a single SELECT with an OR'd predicate:
    #   WHERE (db_typeclass_path LIKE '%corpse%'
    #          OR db_typeclass_path LIKE '%quit_drop%')
    # Chaining .filter(shard_id=...) afterward adds an outer AND, so
    # the final predicate is:
    #   WHERE (corpse OR quit_drop) AND shard_id = '<this>'
    # Cross-shard rows are excluded by SQL; from_db is never called
    # on them.
    qs = ObjectDB.objects.filter(
        db_typeclass_path__contains="corpse"
    ) | ObjectDB.objects.filter(
        db_typeclass_path__contains="quit_drop"
    )
    if role != ROLE_MONOLITH:
        qs = qs.filter(shard_id=get_shard_id())

    corpse_count = 0
    for obj in qs:
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

    Per-role behaviour:
      - router: skip entirely. The router doesn't own game-world
        characters; purgatory is a shard-local concept.
      - shard:  scope the query to this shard only via shard_id. Each
        shard has its own RoomPurgatory (per fcm-world/<shard>/scaffold/);
        a character in purgatory on shard1 must be released by shard1.
      - monolith: no shard scoping; matches the pre-sharding behaviour.
    """
    from evennia_shards import ROLE_MONOLITH, ROLE_ROUTER, get_role, get_shard_id

    role = get_role()
    if role == ROLE_ROUTER:
        return

    from evennia import logger
    from evennia.objects.models import ObjectDB
    from evennia.utils.utils import delay

    from typeclasses.actors.character import FCMCharacter
    from typeclasses.terrain.rooms.room_purgatory import RoomPurgatory

    # Build the queryset in two steps. Django querysets are lazy: neither
    # of the .filter() calls below hits the database — they just compose
    # an SQL description. The actual SELECT runs only when the `for obj
    # in qs` loop starts iterating, at which point BOTH filters are
    # AND'd into a single WHERE clause. Result: cross-shard characters
    # are excluded by the SQL itself and never come back across the wire,
    # so the from_db chokepoint never sees them. We are NOT attempting to
    # load other shards' characters and discarding them in Python.
    qs = ObjectDB.objects.filter(db_typeclass_path__contains="character")
    if role != ROLE_MONOLITH:
        # In a sharded role, restrict to this shard. The composed SQL is:
        #   WHERE db_typeclass_path LIKE '%character%'
        #     AND shard_id = '<this_shard_id>'
        # Characters live on a specific shard, never the "*" global
        # sentinel, so equality with this shard's id is correct.
        qs = qs.filter(shard_id=get_shard_id())

    count = 0
    for obj in qs:
        # FCMCharacter isinstance check survives even the broad
        # db_typeclass_path__contains="character" pre-filter catching
        # anything unrelated (e.g. DefaultCharacter, future subclasses).
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
    import world.dungeons.templates.southern_woods_passage  # noqa: F401


# ================================================================== #
#  Mob AI ticker restart
# ================================================================== #

def _restart_mob_tickers():
    """
    Find all living CombatMobs and restart their AI tickers.

    Dead mobs are deleted in `die()`; the ZoneSpawnScript handles
    spawning fresh replacements on its own clock, so there is no
    restart-time respawn work to do.

    Per-role behaviour:
      - router: skip entirely. The router doesn't own game-world mobs.
      - shard:  scope the query to this shard only via shard_id. Mobs
        live on the same shard as the rooms they spawned into; a mob
        on shard1 must be ticked by shard1.
      - monolith: no shard scoping; matches the pre-sharding behaviour.
    """
    from evennia_shards import ROLE_MONOLITH, ROLE_ROUTER, get_role, get_shard_id

    role = get_role()
    if role == ROLE_ROUTER:
        return

    from evennia import logger
    from evennia.objects.models import ObjectDB

    from typeclasses.actors.mob import CombatMob

    # Lazy queryset composition — both filters AND in one WHERE clause
    # at iteration time, so cross-shard rows are excluded by SQL and
    # from_db is never called on them.
    qs = ObjectDB.objects.filter(db_typeclass_path__contains="mobs.")
    if role != ROLE_MONOLITH:
        qs = qs.filter(shard_id=get_shard_id())

    alive_count = 0
    for obj in qs:
        if not isinstance(obj, CombatMob):
            continue
        if obj.is_alive and obj.location:
            obj.start_ai()
            alive_count += 1

    if alive_count:
        logger.log_info(f"Mob restart: {alive_count} alive ticker(s)")
