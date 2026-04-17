"""
Superuser command to rebuild the test world asynchronously.

Wipes all test-zone objects and rebuilds from scratch without
freezing the server. Players are evacuated to Limbo during the rebuild.

Usage (OOC, superuser only):
    rebuild_test
"""

from evennia import Command
from twisted.internet import threads


class CmdRebuildTest(Command):
    """
    Wipe the test world and rebuild it from scratch.

    Players are evacuated to Limbo, all test-zone objects are deleted
    (preserving player inventories and system rooms), then the test
    world is rebuilt from its build script.

    Runs in a background thread so the server stays responsive.

    Usage:
        rebuild_test
    """

    key = "rebuild_test"
    aliases = []
    locks = "cmd:id(1) and is_ooc()"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        caller.msg("|c--- Rebuild Test World ---|n")
        caller.msg("Rebuilding test world... (server stays responsive)")

        d = threads.deferToThread(_run_rebuild_test)
        d.addCallback(lambda _: _on_complete(caller))
        d.addErrback(lambda f: _on_error(caller, f))


def _run_rebuild_test():
    """Worker thread — wipe and rebuild the test world."""
    from world.test_world.soft_rebuild_test_world import soft_rebuild
    soft_rebuild()


def _on_complete(caller):
    """Reactor thread — notify caller."""
    if caller.sessions.count():
        caller.msg("|c--- Rebuild Test World Complete ---|n")


def _on_error(caller, failure):
    """Reactor thread — rebuild failed."""
    if caller.sessions.count():
        caller.msg(f"|r--- Rebuild Error: {failure.getErrorMessage()} ---|n")
