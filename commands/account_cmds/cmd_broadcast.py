"""
Superuser command: broadcast a message to all connected players.

Usage:
    broadcast <message>
    wall <message>
"""

from evennia import Command


class CmdBroadcast(Command):
    """
    Broadcast a message to all connected players.

    Usage:
        broadcast <message>
        wall <message>

    Sends a highlighted message to every connected session.
    """

    key = "broadcast"
    aliases = []
    locks = "cmd:id(1)"
    help_category = "System"

    def func(self):
        if not self.args or not self.args.strip():
            self.msg("Broadcast what?")
            return

        message = self.args.strip()
        from evennia.server.sessionhandler import SESSION_HANDLER
        SESSION_HANDLER.announce_all(
            f"\n|r--- Broadcast from {self.caller.key} ---|n\n"
            f"|w{message}|n\n"
            f"|r--- End Broadcast ---|n"
        )
        self.msg(f"|gBroadcast sent to {SESSION_HANDLER.count()} session(s).|n")
