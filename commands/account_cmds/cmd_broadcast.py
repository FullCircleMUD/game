"""
Superuser command: broadcast a message to all connected players.

Usage:
    broadcast <message>

Router-only. Actual delivery happens in utils/broadcast.py — the
router dispatches a message to every shard, telling each one to
announce locally to its own connected players (SESSION_HANDLER is
per-process, so only the shard hosting a player can actually reach
them).
"""

from evennia import Command


class CmdBroadcast(Command):
    """
    Broadcast a message to all connected players.

    Usage:
        broadcast <message>

    Sends a highlighted message to every connected session across the
    whole cluster. Router-only — dispatches to every shard so the
    message reaches everyone, not just whoever happens to be connected
    to the process the command is run from.
    """

    key = "broadcast"
    aliases = []
    locks = "cmd:id(1)"
    help_category = "System"

    def func(self):
        from evennia_shards import ROLE_MONOLITH, ROLE_ROUTER, get_role

        role = get_role()
        if role not in (ROLE_MONOLITH, ROLE_ROUTER):
            self.msg("|rThis command can only be run OOC on the router.|n")
            return

        if not self.args or not self.args.strip():
            self.msg("Broadcast what?")
            return

        message = self.args.strip()
        caller_name = self.caller.key

        if role == ROLE_MONOLITH:
            from utils.broadcast import broadcast_to_local_sessions

            count = broadcast_to_local_sessions(caller_name, message)
            self.msg(f"|gBroadcast sent to {count} session(s).|n")
            return

        from django.conf import settings
        from evennia_shards import send_message
        from utils.broadcast import MESSAGE_KIND

        sent = 0
        for shard_id in settings.SHARD_URLS:
            try:
                send_message(
                    MESSAGE_KIND,
                    {"caller_name": caller_name, "message": message},
                    to_shard=shard_id,
                )
                sent += 1
            except Exception as err:
                self.msg(f"|rFailed dispatching to {shard_id}: {err}|n")

        self.msg(f"|gBroadcast dispatched to {sent} shard(s).|n")
