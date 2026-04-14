"""
Moderator command: stop and recreate global service scripts.

Forces every global script to pick up its current class-level
interval and configuration. Use after changing a script's interval
in code, or to repair a wedged script.

The pipeline scripts (telemetry/saturation/spawn) are recreated as
a group with the staggered creation offsets that establish their
pipeline order — accepting the reset for any one of them resets
all three together so the offsets are preserved.

Per-actor and per-instance scripts (combat handlers, dot scripts,
dungeon instances, tutorial instances, effect timers, etc.) are
explicitly NOT in scope. The command operates on an allowlist of
global service scripts only — anything not on the allowlist is
unreachable from this command, so accidentally killing live
combat or dungeon state is impossible.

Usage:
    reset_scripts                           — list and prompt for all
    reset_scripts <script_key>              — reset one named script
    reset_scripts force                     — reset all without prompt
    reset_scripts <script_key> force        — reset one without prompt
"""

from evennia import Command, GLOBAL_SCRIPTS, create_script, logger
from evennia.utils.evmenu import get_input
from twisted.internet import threads


# ----------------------------------------------------------------- #
# Allowlist of resettable global scripts.
#
# Each entry is (key, typeclass_path, is_pipeline). Anything not on
# this list is rejected with an "unknown script" error — combat
# handlers, dot scripts, dungeon instances, tutorial instances, and
# any other per-actor or per-instance scripts are unreachable.
#
# Pipeline scripts are reset as a group: see _PIPELINE_KEYS.
# ----------------------------------------------------------------- #
RESETTABLE_SCRIPTS = [
    # (key, typeclass_path, is_pipeline)
    ("regeneration_service",        "typeclasses.scripts.regeneration_service.RegenerationService",     False),
    ("survival_service",            "typeclasses.scripts.survival_service.SurvivalService",              False),
    ("day_night_service",           "typeclasses.scripts.day_night_service.DayNightService",             False),
    ("season_service",              "typeclasses.scripts.season_service.SeasonService",                  False),
    ("weather_service",             "typeclasses.scripts.weather_service.WeatherService",                False),
    ("reallocation_service",        "typeclasses.scripts.reallocation_service.ReallocationServiceScript",False),
    ("durability_decay_service",    "typeclasses.scripts.durability_decay_service.DurabilityDecayService",False),
    ("telemetry_aggregator_service","typeclasses.scripts.telemetry_service.TelemetryAggregatorScript",   True),
    ("nft_saturation_service",      "typeclasses.scripts.nft_saturation_service.NFTSaturationScript",    True),
    ("unified_spawn_service",       "typeclasses.scripts.unified_spawn_service.UnifiedSpawnScript",      True),
]

_PIPELINE_KEYS = {key for key, _, is_pipeline in RESETTABLE_SCRIPTS if is_pipeline}
_BY_KEY = {key: (typeclass_path, is_pipeline) for key, typeclass_path, is_pipeline in RESETTABLE_SCRIPTS}


def _format_interval(seconds):
    """Render a script interval in a human-readable form."""
    if seconds is None:
        return "?"
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


def _get_script(key):
    """Look up a script in GLOBAL_SCRIPTS by key, or return None."""
    return getattr(GLOBAL_SCRIPTS, key, None)


def _stop_and_delete(key):
    """
    Stop and delete a script if it exists. Returns True if a
    script was deleted, False if there was nothing to delete.
    """
    script = _get_script(key)
    if not script:
        return False
    try:
        script.stop()
    except Exception as exc:
        logger.log_err(f"reset_scripts: stop({key}) failed: {exc}")
    try:
        script.delete()
    except Exception as exc:
        logger.log_err(f"reset_scripts: delete({key}) failed: {exc}")
        return False
    return True


def _create_one(key, typeclass_path):
    """Create a single global script. Logs on success."""
    create_script(typeclass_path, key=key, obj=None)
    logger.log_info(f"reset_scripts: recreated {key}")


def _reset_pipeline():
    """
    Stop, delete, and recreate the entire telemetry/saturation/spawn
    pipeline group with staggered creation offsets, by calling the
    shared helper in at_server_startstop.
    """
    from server.conf.at_server_startstop import _create_pipeline_scripts

    for key, _, _ in RESETTABLE_SCRIPTS:
        if key in _PIPELINE_KEYS:
            _stop_and_delete(key)

    _create_pipeline_scripts(skip_existing=False)


def _reset_one(key):
    """Stop, delete, and recreate a single non-pipeline script."""
    typeclass_path, _ = _BY_KEY[key]
    _stop_and_delete(key)
    _create_one(key, typeclass_path)


class CmdResetScripts(Command):
    """
    Reset global service scripts.

    Stops and recreates global service scripts so they pick up their
    current class-level interval and configuration. Use after changing
    a script's interval in code, or to repair a wedged script.

    Pipeline scripts (telemetry/saturation/spawn) are reset together
    as a group so their staggered offsets are preserved.

    Per-actor and per-instance scripts (combat handlers, dot effects,
    dungeon instances, tutorial instances) are NOT in scope and cannot
    be reached by this command — running it during live combat or an
    active dungeon is safe.

    Usage:
        reset_scripts                          — list resettable scripts
                                                  and prompt to reset all
        reset_scripts <script_key>             — reset one named script
                                                  (after Y/N confirmation)
        reset_scripts force                    — reset all, no prompt
        reset_scripts <script_key> force       — reset one, no prompt
    """

    key = "reset_scripts"
    locks = "cmd:id(1)"
    help_category = "Admin"

    def func(self):
        args = (self.args or "").strip().split()
        force = False
        target_key = None

        for token in args:
            if token.lower() == "force":
                force = True
            elif token in _BY_KEY:
                target_key = token
            else:
                self.msg(
                    f"|rUnknown script: {token}|n\n"
                    "Resettable scripts:\n  "
                    + "\n  ".join(key for key, _, _ in RESETTABLE_SCRIPTS)
                )
                return

        if target_key:
            self._reset_targeted(target_key, force)
        else:
            self._reset_all(force)

    # ─────────────────────────────────────────────────────────────── #
    # Reset all
    # ─────────────────────────────────────────────────────────────── #

    def _reset_all(self, force):
        lines = ["|c--- Resettable Global Scripts ---|n"]
        for i, (key, _, is_pipeline) in enumerate(RESETTABLE_SCRIPTS, 1):
            script = _get_script(key)
            interval = getattr(script, "interval", None) if script else None
            tag = " |y[PIPELINE]|n" if is_pipeline else ""
            status = "" if script else " |x[not running]|n"
            lines.append(
                f"  {i:2d}. {key:32s} (interval={_format_interval(interval)}){tag}{status}"
            )
        lines.append("")
        lines.append(
            "|yPipeline scripts (telemetry/saturation/spawn) will be "
            "recreated as a group with staggered offsets: "
            "telemetry @+0s, saturation @+60s, spawn @+120s.|n"
        )
        self.msg("\n".join(lines))

        if force:
            self.msg(
                f"|yResetting all {len(RESETTABLE_SCRIPTS)} scripts "
                "(force — no confirmation)...|n"
            )
            self._do_reset_all()
            return

        get_input(
            self.account if hasattr(self, "account") else self.caller,
            f"\nReset all {len(RESETTABLE_SCRIPTS)} scripts? [Y]/N? ",
            self._on_confirm_all,
        )

    def _on_confirm_all(self, caller, prompt, result):
        answer = (result or "").strip().lower()
        if answer in ("n", "no"):
            caller.msg("Reset cancelled.")
            return False
        self._do_reset_all()
        return False

    def _do_reset_all(self):
        # Pipeline scripts first (so they go through the grouped path)
        # then the non-pipeline ones individually.
        d = threads.deferToThread(self._reset_all_worker)
        d.addCallback(lambda _: self.msg("|gAll scripts reset.|n"))
        d.addErrback(
            lambda f: self.msg(f"|rReset failed: {f.getErrorMessage()}|n")
        )

    def _reset_all_worker(self):
        _reset_pipeline()
        for key, typeclass_path, is_pipeline in RESETTABLE_SCRIPTS:
            if is_pipeline:
                continue
            _stop_and_delete(key)
            _create_one(key, typeclass_path)
        return True

    # ─────────────────────────────────────────────────────────────── #
    # Reset one (or its pipeline group)
    # ─────────────────────────────────────────────────────────────── #

    def _reset_targeted(self, key, force):
        is_pipeline = _BY_KEY[key][1]

        if is_pipeline:
            self.msg(
                f"|y{key} is a pipeline script. The reset will also "
                "recreate the other two pipeline scripts to preserve "
                "the staggered offsets.|n"
            )
            for pkey in _PIPELINE_KEYS:
                script = _get_script(pkey)
                interval = getattr(script, "interval", None) if script else None
                self.msg(
                    f"  {pkey:32s} (interval={_format_interval(interval)})"
                )
            count = len(_PIPELINE_KEYS)
            prompt = f"\nReset all {count} pipeline scripts? [Y]/N? "
        else:
            script = _get_script(key)
            interval = getattr(script, "interval", None) if script else None
            self.msg(
                f"|c--- Reset {key} ---|n\n"
                f"Current interval: {_format_interval(interval)}"
            )
            prompt = f"\nReset {key}? [Y]/N? "

        if force:
            self.msg(f"|y(force — no confirmation)|n")
            self._do_reset_targeted(key, is_pipeline)
            return

        def _on_confirm(caller, _, result):
            answer = (result or "").strip().lower()
            if answer in ("n", "no"):
                caller.msg("Reset cancelled.")
                return False
            self._do_reset_targeted(key, is_pipeline)
            return False

        get_input(
            self.account if hasattr(self, "account") else self.caller,
            prompt,
            _on_confirm,
        )

    def _do_reset_targeted(self, key, is_pipeline):
        d = threads.deferToThread(
            self._reset_targeted_worker, key, is_pipeline,
        )
        d.addCallback(lambda _: self.msg("|gDone.|n"))
        d.addErrback(
            lambda f: self.msg(f"|rReset failed: {f.getErrorMessage()}|n")
        )

    def _reset_targeted_worker(self, key, is_pipeline):
        if is_pipeline:
            _reset_pipeline()
        else:
            _reset_one(key)
        return True
