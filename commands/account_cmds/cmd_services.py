"""
Superuser command: show service status and reset global service scripts.

Consolidates the former ``service_run`` (status report + start missing)
and ``reset_scripts`` (stop/delete/recreate) into a single command.

Reset on a running service stops, deletes, and recreates it so it picks
up current code. Reset on a missing service simply creates it. Pipeline
scripts (telemetry/saturation/spawn) are always reset as a group.

Usage:
    services                              — show all services and status
    services reset <name>                 — reset one (Y/N prompt)
    services reset all                    — reset pipeline + global (prompt)
    services reset zone <zone_key>        — reset one zone script (prompt)
    services reset zones all              — reset all zone scripts (prompt)
    services reset <...> force            — skip prompt
"""

import glob
import os
import time

from evennia import Command, GLOBAL_SCRIPTS, create_script, logger
from evennia.utils.evmenu import get_input
from twisted.internet import threads

from server.conf.at_server_startstop import (
    _GLOBAL_SCRIPTS,
    _PIPELINE_SCRIPTS,
    _create_pipeline_scripts,
)
from typeclasses.scripts.nft_saturation_service import (
    SLOT_MINUTE as _SATURATION_SLOT,
)
from typeclasses.scripts.telemetry_service import (
    SLOT_MINUTE as _TELEMETRY_SLOT,
)
from typeclasses.scripts.unified_spawn_service import (
    SLOT_MINUTE as _SPAWN_SLOT,
)
from typeclasses.scripts.zone_spawn_script import ZoneSpawnScript


# ----------------------------------------------------------------- #
# Zone spawn script discovery
# ----------------------------------------------------------------- #

_SPAWNS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "world", "spawns")
)


def _discover_zone_keys():
    """Enumerate zone_keys from world/spawns/*.json filenames."""
    return sorted(
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(_SPAWNS_DIR, "*.json"))
    )


def _get_zone_script(zone_key):
    """Look up a ZoneSpawnScript by zone_key, or return None."""
    return ZoneSpawnScript.objects.filter(db_key=f"zone_spawn_{zone_key}").first()


def _running_zone_keys():
    """Return zone_keys for every ZoneSpawnScript currently in the DB."""
    keys = []
    for script in ZoneSpawnScript.objects.all():
        key = script.key or ""
        if key.startswith("zone_spawn_"):
            keys.append(key[len("zone_spawn_"):])
    return keys


def _format_age(seconds):
    """Render an elapsed-time span in a compact form."""
    if seconds is None:
        return "never"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def _reset_zone(zone_key):
    """Stop, delete, and recreate a single zone spawn script."""
    script = _get_zone_script(zone_key)
    if script:
        try:
            script.stop()
        except Exception as exc:
            logger.log_err(f"services: stop(zone_spawn_{zone_key}) failed: {exc}")
        try:
            script.delete()
        except Exception as exc:
            logger.log_err(f"services: delete(zone_spawn_{zone_key}) failed: {exc}")
    ZoneSpawnScript.create_for_zone(zone_key)


# Wall-clock slot minute for each pipeline script. Used to render the
# "fires HH:MM" suffix in the status report.
PIPELINE_SLOT_MINUTES = {
    "telemetry_aggregator_service": _TELEMETRY_SLOT,
    "nft_saturation_service": _SATURATION_SLOT,
    "unified_spawn_service": _SPAWN_SLOT,
}


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
        services reset all                    — reset pipeline + global (prompt)
        services reset zone <zone_key>        — reset one zone script (prompt)
        services reset zones all              — reset all zone scripts (prompt)
        services reset <...> force            — skip prompt

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
            self.msg("Usage: services [reset [<name> | all | zone <key> | zones all] [force]]")
            return

        tokens = args[1:]
        force = any(t.lower() == "force" for t in tokens)
        non_force = [t for t in tokens if t.lower() != "force"]

        # Zone-script arms: `reset zone <key>` or `reset zones all`
        if non_force and non_force[0].lower() in ("zone", "zones"):
            self._handle_zone_reset(non_force, force)
            return

        target = None
        for token in non_force:
            if token.lower() == "all":
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
            self.msg("Usage: services reset [<name> | all | zone <key> | zones all] [force]")
            return

        if target == "all":
            self._reset_all(force)
        else:
            self._reset_targeted(target, force)

    # ─────────────────────────────────────────────────────────────── #
    # Zone-script reset
    # ─────────────────────────────────────────────────────────────── #

    def _handle_zone_reset(self, tokens, force):
        """Parse and dispatch `reset zone <key>` or `reset zones all`."""
        head = tokens[0].lower()
        zone_keys = _discover_zone_keys()

        if head == "zones":
            if len(tokens) < 2 or tokens[1].lower() != "all":
                self.msg("Usage: services reset zones all [force]")
                return
            self._reset_zones_all(zone_keys, force)
            return

        # head == "zone"
        if len(tokens) < 2:
            self.msg(
                "Usage: services reset zone <zone_key> [force]\n"
                "Available zones:\n  " + "\n  ".join(zone_keys)
            )
            return

        requested = tokens[1]
        if requested in zone_keys:
            zone_key = requested
        else:
            matches = [z for z in zone_keys if requested in z]
            if len(matches) == 1:
                zone_key = matches[0]
            else:
                self.msg(
                    f"|rUnknown zone: {requested}|n\n"
                    "Available zones:\n  " + "\n  ".join(zone_keys)
                )
                return

        self._reset_zone_targeted(zone_key, force)

    def _reset_zone_targeted(self, zone_key, force):
        script = _get_zone_script(zone_key)
        status = "|gRUNNING|n" if script else "|rMISSING|n"
        self.msg(f"|c--- zone_spawn_{zone_key} ---|n\n  {status}")

        if force:
            self.msg("|y(force — no confirmation)|n")
            self._do_reset_zone(zone_key)
            return

        def _on_confirm(caller, _, result):
            answer = (result or "").strip().lower()
            if answer in ("n", "no"):
                caller.msg("Reset cancelled.")
                return False
            self._do_reset_zone(zone_key)
            return False

        get_input(
            self.account if hasattr(self, "account") else self.caller,
            f"\nReset zone_spawn_{zone_key}? [Y]/N? ",
            _on_confirm,
        )

    def _do_reset_zone(self, zone_key):
        d = threads.deferToThread(_reset_zone, zone_key)
        d.addCallback(lambda _: self.msg(f"|gzone_spawn_{zone_key} reset.|n"))
        d.addErrback(
            lambda f: self.msg(f"|rReset failed: {f.getErrorMessage()}|n")
        )

    def _reset_zones_all(self, zone_keys, force):
        self.msg(
            f"|yResetting all {len(zone_keys)} zone spawn scripts:|n "
            + ", ".join(zone_keys)
        )

        if force:
            self.msg("|y(force — no confirmation)|n")
            self._do_reset_zones_all(zone_keys)
            return

        def _on_confirm(caller, _, result):
            answer = (result or "").strip().lower()
            if answer in ("n", "no"):
                caller.msg("Reset cancelled.")
                return False
            self._do_reset_zones_all(zone_keys)
            return False

        get_input(
            self.account if hasattr(self, "account") else self.caller,
            f"\nReset all {len(zone_keys)} zone spawn scripts? [Y]/N? ",
            _on_confirm,
        )

    def _do_reset_zones_all(self, zone_keys):
        def _worker():
            for zone_key in zone_keys:
                _reset_zone(zone_key)
            return True

        d = threads.deferToThread(_worker)
        d.addCallback(lambda _: self.msg(f"|g{len(zone_keys)} zone scripts reset.|n"))
        d.addErrback(
            lambda f: self.msg(f"|rReset failed: {f.getErrorMessage()}|n")
        )

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
                if is_pipeline:
                    slot = PIPELINE_SLOT_MINUTES.get(key)
                    detail = f"({_format_interval(interval)} tick, fires HH:{slot:02d})"
                    tag = " |y[PIPELINE]|n"
                else:
                    detail = f"({_format_interval(interval)})"
                    tag = ""
                lines.append(
                    f"  |gRUNNING|n  {key:36s} {detail}{tag}"
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

        # ── Zone spawn scripts ──
        lines.append("")
        lines.append("|w=== Zone Spawn Scripts ===|n")
        lines.append("")

        zone_keys = _discover_zone_keys()
        zone_found = 0
        zone_missing = 0
        zone_stalled = 0
        now = time.time()
        name_width = max((len(z) for z in zone_keys), default=20)

        for zone_key in zone_keys:
            script = _get_zone_script(zone_key)
            if not script:
                zone_missing += 1
                lines.append(f"  |rMISSING|n  {zone_key:{name_width}s}")
                continue

            zone_found += 1
            interval = getattr(script, "interval", None)
            last_times = dict(script.db.last_spawn_times or {})
            if last_times:
                last = max(last_times.values())
                age_str = _format_age(now - last)
                stall_tag = ""
            else:
                age_str = "never"
                stall_tag = " |y[STALLED?]|n"
                zone_stalled += 1
            lines.append(
                f"  |gRUNNING|n  {zone_key:{name_width}s} "
                f"({_format_interval(interval)} tick)  "
                f"last spawn: {age_str:>10s}{stall_tag}"
            )

        # Orphan scripts — DB rows with no matching JSON
        orphans = [k for k in _running_zone_keys() if k not in zone_keys]
        for orphan in sorted(orphans):
            lines.append(
                f"  |yORPHAN |n  {orphan:{name_width}s} "
                f"(no matching world/spawns/{orphan}.json)"
            )

        zone_total = len(zone_keys)
        summary_parts = [f"|w{zone_found}/{zone_total}|n zone scripts running"]
        if zone_missing:
            summary_parts.append(f"|r{zone_missing} missing|n")
        if zone_stalled:
            summary_parts.append(f"|y{zone_stalled} stalled|n")
        if orphans:
            summary_parts.append(f"|y{len(orphans)} orphan|n")
        lines.append("")
        lines.append(", ".join(summary_parts) + ".")

        if zone_missing or zone_stalled or orphans:
            lines.append(
                "Use |wservices reset zone <zone_key>|n or "
                "|wservices reset zones all|n to recreate."
            )
        if zone_stalled:
            lines.append(
                "|yStalled scripts (never spawned) often indicate rooms are "
                "missing `mob_area` tags — investigate before reset.|n"
            )

        self.msg("\n".join(lines))

    # ─────────────────────────────────────────────────────────────── #
    # Reset all
    # ─────────────────────────────────────────────────────────────── #

    def _reset_all(self, force):
        self._show_report()
        self.msg(
            "\n|yPipeline scripts will be recreated as a group. "
            f"Wall-clock slots: telemetry HH:{_TELEMETRY_SLOT:02d}, "
            f"saturation HH:{_SATURATION_SLOT:02d}, "
            f"spawn HH:{_SPAWN_SLOT:02d}.|n"
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
                "scripts as a group:|n"
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
