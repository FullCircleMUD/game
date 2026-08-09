"""
Broadcast helper — announces a message to every session on this process.

The router dispatches; each shard (or monolith, directly) calls
broadcast_to_local_sessions() to reach its own connected players.
SESSION_HANDLER is per-process, so only the process actually hosting a
player's session can reach them. See commands/account_cmds/cmd_broadcast.py.
"""

MESSAGE_KIND = "broadcast_to_shard"


def broadcast_to_local_sessions(caller_name, message):
    """Announce `message` to every session connected to this process.

    Args:
        caller_name: display name of whoever sent the broadcast.
        message: the broadcast text.

    Returns:
        int — number of sessions the announcement reached.
    """
    from evennia.server.sessionhandler import SESSION_HANDLER

    SESSION_HANDLER.announce_all(
        f"\n|r--- Broadcast from {caller_name} ---|n\n"
        f"|w{message}|n\n"
        f"|r--- End Broadcast ---|n"
    )
    return SESSION_HANDLER.count()
