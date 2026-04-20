"""
Superuser command: show service status and reset global service scripts.

Consolidates the former ``service_run`` (status report + start missing)
and ``reset_scripts`` (stop/delete/recreate) into a single command.

Reset on a running service stops, deletes, and recreates it so it picks
up current code. Reset on a missing service simply creates it. Pipeline
scripts (telemetry/saturation/spawn) are always reset as a group to
preserve their staggered creation offsets.

Usage:
    services                              — show all services and status
    services reset <name>                 — reset one (Y/N prompt)
    services reset all                    — reset all (Y/N prompt)
    services reset <name> force           — reset one, no prompt
    services reset all force              — reset all, no prompt
"""

from evennia import Command, GLOBAL_SCRIPTS, create_script, logger
from evennia.utils.evmenu import get_input
from twisted.internet import threads

from server.conf.at_server_startstop import (
    _GLOBAL_SCRIPTS,
    _PIPELINE_SCRIPTS,
    _create_pipeline_scripts,
)


# ----------------------------------------------------------------- #
# Unified script registry — built from both lists in at_server_startstop.
# ----------------------------------------------------------------- #

_PIPELINE_KEYS = {key for key, _, _ in _PIPELINE_SCRIPTS}

# (key, typeclass_path, is_pipeline) — pipeline scripts first, then the rest.
_ALL_SCRIPTS = [
    (key, path, True) for key, path, _ in _PIPELINE_SCRIPTS
] + [
    (key, path, False) for key, path in _GLOBAL_SCRIPTS
]

_BY_KEY = {key: (path, is_pipeline) for key, path, is_pipeline in _ALL_SCRIPTS}

# Short aliases: "spawn" → "unified_spawn_service", etc.
_SHORT_ALIASES = {}
for _key, _, _ in _ALL_SCRIPTS:
    _short = _key.replace("_service", "").replace("_script", "")
    _SHORT_ALIASES[_short] = _key
    _first_word = _key.split("_")[0]
    if _first_word not in _SHORT_ALIASES:
        _SHORT_ALIASES[_first_word] = _key


# ----------------------------------------------------------------- #
# Helpers
# ----------------------------------------------------------------- #

def _resolve_name(name):
    """Resolve a service name via exact match, short alias, or partial match."""
    name = name.lower().strip()
    if name in _BY_KEY:
        return name
    if name in _SHORT_ALIASES:
        return _SHORT_ALIASES[name]
    matches = [key for key in _BY_KEY if name in key]
    if len(matches) == 1:
        return matches[0]
    return None


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
        logger.log_err(f"services: stop({key}) failed: {exc}")
    try:
        script.delete()
    except Exception as exc:
        logger.log_err(f"services: delete({key}) failed: {exc}")
        return False
    return True


def _create_one(key, typeclass_path):
    """Create a single global script. Logs on success."""
    create_script(typeclass_path, key=key, obj=None)
    logger.log_info(f"services: recreated {key}")


def _reset_pipeline():
    """
    Stop, delete, and recreate the entire telemetry/saturation/spawn
    pipeline group with staggered creation offsets.
    """
    for key in _PIPELINE_KEYS:
        _stop_and_delete(key)
    _create_pipeline_scripts(skip_existing=False)


def _reset_one(key):
    """Stop, delete, and recreate a single non-pipeline script."""
    typeclass_path, _ = _BY_KEY[key]
    _stop_and_delete(key)
    _create_one(key, typeclass_path)


# ----------------------------------------------------------------- #
# Command
# ----------------------------------------------------------------- #

class CmdServices(Command):
    """
    Show service status or reset global service scripts.

    With no arguments, displays the status of all global scripts.
    ``reset`` stops, deletes, and recreates a service so it picks up
    current code — or simply creates it if it was missing.

    Pipeline scripts (telemetry/saturation/spawn) are always reset as
    a group to preserve their staggered tick offsets.

    Usage:
        services                              — list all services
        services reset <name>                 — reset one (with prompt)
        services reset all                    — reset all (with prompt)
        services reset <name> force           — reset one, no prompt
        services reset all force              — reset all, no prompt

    Service names support partial matching:
        services reset spawn       → unified_spawn_service
        services reset regen       → regeneration_service
        services reset telemetry   → telemetry_aggregator_service
    """

    key = "services"
    locks = "cmd:id(1)"
    help_category = "Admin"

    def func(self):
        args = (self.args or "").strip().split()

        if not args:
            self._show_report()
            return

        if args[0].lower() != "reset":
            self.msg("Usage: services [reset [<name> | all] [force]]")
            return

        tokens = args[1:]
        force = False
        target = None

        for token in tokens:
            if token.lower() == "force":
                force = True
            elif token.lower() == "all":
                target = "all"
            else:
                resolved = _resolve_name(token)
                if not resolved:
                    self.msg(
                        f"|rUnknown service: {token}|n\n"
                        "Available services:\n  "
                        + "\n  ".join(key for key, _, _ in _ALL_SCRIPTS)
                    )
                    return
                target = resolved

        if not target:
            self.msg("Usage: services reset [<name> | all] [force]")
            return

        if target == "all":
            self._reset_all(force)
        else:
            self._reset_targeted(target, force)

    # ─────────────────────────────────────────────────────────────── #
    # Status report
    # ─────────────────────────────────────────────────────────────── #

    def _show_report(self):
        lines = ["|w=== Service Report ===|n\n"]
        found = 0
        missing = 0

        for i, (key, _, is_pipeline) in enumerate(_ALL_SCRIPTS, 1):
            script = _get_script(key)
            if script:
                found += 1
                interval = getattr(script, "interval", None)
                tag = " |y[PIPELINE]|n" if is_pipeline else ""
                lines.append(
                    f"  |gRUNNING|n  {key:36s} "
                    f"({_format_interval(interval)}){tag}"
                )
            else:
                missing += 1
                tag = " |y[PIPELINE]|n" if is_pipeline else ""
                lines.append(
                    f"  |rMISSING|n  {key:36s}{tag}"
                )

        total = len(_ALL_SCRIPTS)
        lines.append("")
        if missing:
            lines.append(
                f"|w{found}/{total}|n services running, "
                f"|r{missing} missing|n. "
                f"Use |wservices reset all|n or "
                f"|wservices reset <name>|n to fix."
            )
        else:
            lines.append(f"|wAll {total} services running.|n")

        self.msg("\n".join(lines))

    # ─────────────────────────────────────────────────────────────── #
    # Reset all
    # ─────────────────────────────────────────────────────────────── #

    def _reset_all(self, force):
        self._show_report()
        self.msg(
            "\n|yPipeline scripts will be recreated as a group with "
            "staggered offsets: telemetry @+0s, saturation @+60s, "
            "spawn @+120s.|n"
        )

        if force:
            self.msg(
                f"|yResetting all {len(_ALL_SCRIPTS)} scripts "
                "(force — no confirmation)...|n"
            )
            self._do_reset_all()
            return

        get_input(
            self.account if hasattr(self, "account") else self.caller,
            f"\nReset all {len(_ALL_SCRIPTS)} scripts? [Y]/N? ",
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
        d = threads.deferToThread(self._reset_all_worker)
        d.addCallback(lambda _: self.msg("|gAll scripts reset.|n"))
        d.addErrback(
            lambda f: self.msg(f"|rReset failed: {f.getErrorMessage()}|n")
        )

    def _reset_all_worker(self):
        _reset_pipeline()
        for key, typeclass_path, is_pipeline in _ALL_SCRIPTS:
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
                f"|y{key} is a pipeline script. Resetting all 3 pipeline "
                "scripts to preserve staggered offsets:|n"
            )
            for pkey in sorted(_PIPELINE_KEYS):
                script = _get_script(pkey)
                interval = getattr(script, "interval", None) if script else None
                status = "|gRUNNING|n" if script else "|rMISSING|n"
                self.msg(
                    f"  {status}  {pkey:36s} "
                    f"({_format_interval(interval)})"
                )
            count = len(_PIPELINE_KEYS)
            prompt = f"\nReset all {count} pipeline scripts? [Y]/N? "
        else:
            script = _get_script(key)
            interval = getattr(script, "interval", None) if script else None
            status = "|gRUNNING|n" if script else "|rMISSING|n"
            self.msg(
                f"|c--- {key} ---|n\n"
                f"  {status}  interval: {_format_interval(interval)}"
            )
            prompt = f"\nReset {key}? [Y]/N? "

        if force:
            self.msg("|y(force — no confirmation)|n")
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
