"""
Superuser command to rebuild the game world asynchronously.

Wipes all active zones and rebuilds from scratch without freezing
the server. Players are evacuated to Limbo during the rebuild.

Usage (OOC, superuser only):
    rebuild_world
"""

from evennia import Command
from twisted.internet import threads


class CmdRebuildWorld(Command):
    """
    Wipe all active zones and rebuild the full game world.

    Players are evacuated to Limbo, all zone objects are deleted,
    then every active zone is rebuilt from its build script.

    Runs in a background thread so the server stays responsive.

    Usage:
        rebuild_world
    """

    key = "rebuild_world"
    aliases = ["rebuildworld"]
    locks = "cmd:id(1) and is_ooc()"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        caller.msg("|c--- Rebuild World ---|n")
        caller.msg("Rebuilding all zones... (server stays responsive)")

        d = threads.deferToThread(_run_rebuild_world)
        d.addCallback(lambda _: _on_complete(caller))
        d.addErrback(lambda f: _on_error(caller, f))


def _run_rebuild_world():
    """Worker thread — wipe and rebuild all zones."""
    from world.game_world.deploy_world import soft_deploy_world
    soft_deploy_world()


def _on_complete(caller):
    """Reactor thread — notify caller."""
    if caller.sessions.count():
        caller.msg("|c--- Rebuild World Complete ---|n")


def _on_error(caller, failure):
    """Reactor thread — rebuild failed."""
    if caller.sessions.count():
        caller.msg(f"|r--- Rebuild Error: {failure.getErrorMessage()} ---|n")
