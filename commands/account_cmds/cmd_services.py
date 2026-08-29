"""
Superuser command: show which global service scripts should be running
on this process, and reset one.

Reads _SCRIPTS directly (server/conf/at_server_startstop.py) rather than
the retired role-blind shim, so the report is scoped to what this
process's role actually declares — a router shows router/monolith
scripts only, a shard shows shard/monolith scripts only. A script whose
role doesn't include this process is simply not listed, and cannot be
named as a reset target here — there is no "wrong process" error path
because there is no way to reach it in the first place.

Usage:
    services                    — list services that should run here,
                                   with live/heartbeat status
    services reset <name>       — reset one (Y/N prompt)
    services reset <name> force — skip the prompt
"""

from evennia import Command, GLOBAL_SCRIPTS, create_script, logger
from evennia.utils.evmenu import get_input
from evennia_shards import get_role
from utils.db_threads import defer_to_db_thread

from server.conf.at_server_startstop import _select_scripts


# ----------------------------------------------------------------- #
# Helpers
# ----------------------------------------------------------------- #

def _resolve_name(name, entries):
    """Resolve a service name via exact match, short alias, or partial
    match — only among `entries` (the (key, typeclass_path) pairs
    applicable to this process's role)."""
    name = name.lower().strip()
    by_key = dict(entries)
    if name in by_key:
        return name

    short_aliases = {}
    for key, _ in entries:
        short = key.replace("_service", "").replace("_script", "")
        short_aliases.setdefault(short, key)
        first_word = key.split("_")[0]
        short_aliases.setdefault(first_word, key)
    if name in short_aliases:
        return short_aliases[name]

    matches = [key for key, _ in entries if name in key]
    if len(matches) == 1:
        return matches[0]
    return None


def _get_script(key):
    """Look up a script in GLOBAL_SCRIPTS by key, or return None."""
    return getattr(GLOBAL_SCRIPTS, key, None)


def _is_running(script):
    """True if this process has a live ticker attached to the script."""
    if script is None:
        return False
    task = getattr(script.ndb, "_task", None)
    return bool(task and getattr(task, "running", False))


def _fmt_dt(dt):
    """Render an ndb timestamp, or 'never' if unset."""
    if dt is None:
        return "never"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


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


def _reset_one(key, typeclass_path):
    """Stop, delete, and recreate a single script from its DB row."""
    _stop_and_delete(key)
    create_script(typeclass_path, key=key, obj=None)
    logger.log_info(f"services: recreated {key}")


# ----------------------------------------------------------------- #
# Command
# ----------------------------------------------------------------- #

class CmdServices(Command):
    """
    Show which global service scripts should be running on this
    process, or reset one.

    With no arguments, lists every script _SCRIPTS declares for this
    process's role, whether it currently has a live ticker attached,
    and its last_repeat/last_work heartbeat timestamps (see
    typeclasses/scripts/heartbeat_script.py). Staleness is read by eye
    against each script's own known cadence — this command does not
    judge it for you.

    ``reset`` stops, deletes, and recreates a service from its DB row
    so it picks up current code, or creates it if it was missing. Only
    scripts valid for this process's role can be named as a target.

    Usage:
        services                    — list services for this role
        services reset <name>       — reset one (with prompt)
        services reset <name> force — skip prompt

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
            self.msg("Usage: services [reset <name> [force]]")
            return

        tokens = args[1:]
        force = any(t.lower() == "force" for t in tokens)
        non_force = [t for t in tokens if t.lower() != "force"]

        if len(non_force) != 1:
            self.msg("Usage: services reset <name> [force]")
            return

        entries = _select_scripts(role=get_role())
        resolved = _resolve_name(non_force[0], entries)
        if not resolved:
            self.msg(
                f"|rUnknown service: {non_force[0]}|n\n"
                f"Services on this {get_role()}:\n  "
                + "\n  ".join(key for key, _ in entries)
            )
            return

        typeclass_path = dict(entries)[resolved]
        self._reset_targeted(resolved, typeclass_path, force)

    # ─────────────────────────────────────────────────────────────── #
    # Status report
    # ─────────────────────────────────────────────────────────────── #

    def _show_report(self):
        role = get_role()
        entries = _select_scripts(role=role)

        lines = [f"|w=== Service Report ({role}) ===|n\n"]
        name_width = max((len(key) for key, _ in entries), default=20)
        lines.append(
            f"  {'SERVICE':{name_width}s}  RUNNING  "
            f"{'LAST REPEAT':19s}  LAST WORK"
        )

        for key, _typeclass_path in entries:
            script = _get_script(key)
            running = _is_running(script)
            status = "|gYES|n" if running else "|rNO |n "
            last_repeat = getattr(script.ndb, "last_repeat", None) if script else None
            last_work = getattr(script.ndb, "last_work", None) if script else None
            lines.append(
                f"  {key:{name_width}s}  {status}  "
                f"{_fmt_dt(last_repeat):19s}  {_fmt_dt(last_work)}"
            )

        self.msg("\n".join(lines))

    # ─────────────────────────────────────────────────────────────── #
    # Reset one
    # ─────────────────────────────────────────────────────────────── #

    def _reset_targeted(self, key, typeclass_path, force):
        script = _get_script(key)
        status = "|gYES|n" if _is_running(script) else "|rNO|n"
        self.msg(f"|c--- {key} ---|n\n  running: {status}")

        if force:
            self.msg("|y(force — no confirmation)|n")
            self._do_reset_targeted(key, typeclass_path)
            return

        def _on_confirm(caller, _, result):
            answer = (result or "").strip().lower()
            if answer in ("n", "no"):
                caller.msg("Reset cancelled.")
                return False
            self._do_reset_targeted(key, typeclass_path)
            return False

        get_input(
            self.account if hasattr(self, "account") else self.caller,
            f"\nReset {key}? [Y]/N? ",
            _on_confirm,
        )

    def _do_reset_targeted(self, key, typeclass_path):
        d = defer_to_db_thread(_reset_one, key, typeclass_path)
        d.addCallback(lambda _: self.msg(f"|g{key} reset.|n"))
        d.addErrback(
            lambda f: self.msg(f"|rReset failed: {f.getErrorMessage()}|n")
        )
