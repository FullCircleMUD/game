"""
Superuser command to rebuild a single zone asynchronously.

Wipes and rebuilds one zone without touching the rest of the world.
Players in the zone are evacuated to Limbo during the rebuild.

Usage (OOC, superuser only):
    rebuild_zone <zone_name>
    rebuild_zone               (lists available zones)
"""

import importlib

from evennia import Command
from twisted.internet import threads

from world.game_world.deploy_world import ACTIVE_ZONES


class CmdRebuildZone(Command):
    """
    Wipe and rebuild a single zone.

    Cleans all objects in the specified zone and rebuilds it from
    its build script. Other zones are not affected.

    Runs in a background thread so the server stays responsive.

    Usage:
        rebuild_zone <zone_name>
        rebuild_zone
    """

    key = "rebuild_zone"
    aliases = []
    locks = "cmd:id(1) and is_ooc()"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        zone_key = self.args.strip().lower()

        if not zone_key:
            zones = ", ".join(ACTIVE_ZONES)
            caller.msg(f"|wAvailable zones:|n {zones}")
            caller.msg("Usage: rebuild_zone <zone_name>")
            return

        if zone_key not in ACTIVE_ZONES:
            caller.msg(f"|rUnknown zone: {zone_key}|n")
            zones = ", ".join(ACTIVE_ZONES)
            caller.msg(f"|wAvailable zones:|n {zones}")
            return

        caller.msg(f"|c--- Rebuild Zone: {zone_key} ---|n")
        caller.msg(f"Rebuilding {zone_key}... (server stays responsive)")

        d = threads.deferToThread(_run_rebuild_zone, zone_key)
        d.addCallback(lambda _: _on_complete(caller, zone_key))
        d.addErrback(lambda f: _on_error(caller, f))


def _run_rebuild_zone(zone_key):
    """Worker thread — wipe and rebuild a single zone."""
    module = importlib.import_module(
        f"world.game_world.zones.{zone_key}.soft_deploy"
    )
    module.soft_deploy()


def _on_complete(caller, zone_key):
    """Reactor thread — notify caller."""
    if caller.sessions.count():
        caller.msg(f"|c--- Rebuild Zone: {zone_key} Complete ---|n")


def _on_error(caller, failure):
    """Reactor thread — rebuild failed."""
    if caller.sessions.count():
        caller.msg(f"|r--- Rebuild Error: {failure.getErrorMessage()} ---|n")
