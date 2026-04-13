"""
Superuser command: show service status and start missing services.

With no arguments, shows the status of all global service scripts.
With a service name, starts that service if it's not running.

Usage:
    service_run                 — show all services and their status
    service_run <name>          — start a missing service
    service_run all             — start all missing services
"""

from evennia import Command, GLOBAL_SCRIPTS, create_script
from server.conf.at_server_startstop import _GLOBAL_SCRIPTS


# Build a lookup for quick name matching (supports partial names)
_SCRIPT_MAP = {key: path for key, path in _GLOBAL_SCRIPTS}
# Short aliases: "spawn" → "unified_spawn_service", etc.
_SHORT_ALIASES = {}
for key, _ in _GLOBAL_SCRIPTS:
    # strip _service/_script suffix for convenience
    short = key.replace("_service", "").replace("_script", "")
    _SHORT_ALIASES[short] = key
    # also allow just the first word
    first_word = key.split("_")[0]
    if first_word not in _SHORT_ALIASES:
        _SHORT_ALIASES[first_word] = key


def _resolve_name(name):
    """Resolve a service name, supporting exact match, short alias, or partial match."""
    name = name.lower().strip()
    # Exact match
    if name in _SCRIPT_MAP:
        return name
    # Short alias
    if name in _SHORT_ALIASES:
        return _SHORT_ALIASES[name]
    # Partial match
    matches = [key for key in _SCRIPT_MAP if name in key]
    if len(matches) == 1:
        return matches[0]
    return None


class CmdServiceRun(Command):
    """
    Show service status or start a missing service.

    Usage:
        service_run                 — list all services and their status
        service_run <name>          — start a specific missing service
        service_run all             — start all missing services

    Service names support partial matching:
        service_run spawn           → unified_spawn_service
        service_run regen           → regeneration_service
        service_run telemetry       → telemetry_aggregator_service
    """

    key = "service_run"
    aliases = ["services"]
    locks = "cmd:id(1)"
    help_category = "Admin"

    def func(self):
        args = self.args.strip().lower()

        if not args:
            self._show_report()
        elif args == "all":
            self._start_all_missing()
        else:
            self._start_one(args)

    def _show_report(self):
        """Display status of all global services."""
        self.msg("|w=== Service Report ===|n\n")

        found = 0
        missing = 0

        for key, typeclass_path in _GLOBAL_SCRIPTS:
            script = getattr(GLOBAL_SCRIPTS, key, None)
            if script:
                found += 1
                interval = getattr(script, 'interval', None)
                if interval:
                    if interval >= 3600:
                        interval_str = f"{interval / 3600:.1f}h"
                    elif interval >= 60:
                        interval_str = f"{interval / 60:.0f}m"
                    else:
                        interval_str = f"{interval}s"
                else:
                    interval_str = "no tick"

                self.msg(f"  |gRUNNING|n  |w{key}|n  ({interval_str})")
            else:
                missing += 1
                self.msg(f"  |rMISSING|n  |w{key}|n")

        # Summary
        total = len(_GLOBAL_SCRIPTS)
        self.msg("")
        if missing:
            self.msg(
                f"|w{found}/{total}|n services running, "
                f"|r{missing} missing|n. "
                f"Use |wservice_run all|n or |wservice_run <name>|n to start."
            )
        else:
            self.msg(f"|wAll {total} services running.|n")

    def _start_one(self, name):
        """Start a single service by name."""
        resolved = _resolve_name(name)
        if not resolved:
            self.msg(f"|rUnknown service: {name}|n")
            self.msg("Available services:")
            for key, _ in _GLOBAL_SCRIPTS:
                self.msg(f"  {key}")
            return

        # Check if already running
        existing = getattr(GLOBAL_SCRIPTS, resolved, None)
        if existing:
            self.msg(f"|w{resolved}|n is already running.")
            return

        # Start it
        typeclass_path = _SCRIPT_MAP[resolved]
        create_script(typeclass_path, key=resolved, obj=None)
        self.msg(f"|gStarted|n |w{resolved}|n")

    def _start_all_missing(self):
        """Start all services that are not currently running."""
        started = 0
        for key, typeclass_path in _GLOBAL_SCRIPTS:
            existing = getattr(GLOBAL_SCRIPTS, key, None)
            if not existing:
                create_script(typeclass_path, key=key, obj=None)
                self.msg(f"  |gStarted|n |w{key}|n")
                started += 1

        if started:
            self.msg(f"\n|gStarted {started} service(s).|n")
        else:
            self.msg("All services already running.")
