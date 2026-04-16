"""
Input functions

Input functions are always called from the client (they handle server
input, hence the name).

This module is loaded by being included in the
`settings.INPUT_FUNC_MODULES` tuple.

All *global functions* included in this module are considered
input-handler functions and can be called by the client to handle
input.

An input function must have the following call signature:

    cmdname(session, *args, **kwargs)

Where session will be the active session and *args, **kwargs are extra
incoming arguments and keyword properties.

A special command is the "default" command, which is will be called
when no other cmdname matches. It also receives the non-found cmdname
as argument.

    default(session, cmdname, *args, **kwargs)

"""

from django.conf import settings

from evennia.commands.cmdhandler import cmdhandler

_IDLE_COMMAND = settings.IDLE_COMMAND
_IDLE_COMMAND = (_IDLE_COMMAND,) if _IDLE_COMMAND == "idle" else (_IDLE_COMMAND, "idle")

_STRIP_INCOMING_MXP = getattr(settings, "MXP_ENABLED", False) and getattr(
    settings, "MXP_OUTGOING_ONLY", False
)
_STRIP_MXP = None


def _maybe_strip_incoming_mxp(txt):
    global _STRIP_MXP
    if _STRIP_INCOMING_MXP:
        if not _STRIP_MXP:
            from evennia.utils.ansi import strip_mxp as _STRIP_MXP
        return _STRIP_MXP(txt)
    return txt


def text(session, *args, **kwargs):
    """
    Main text input from the client. This will execute a command
    string on the server.

    Overrides Evennia's default to add semicolon command stacking:
    input like "get sword;wield sword" is split into two separate
    commands processed sequentially.

    Args:
        session (Session): The active Session to receive the input.
        text (str): First arg is used as text-command input.
    """
    txt = args[0] if args else None
    if txt is None:
        return

    if txt.strip() in _IDLE_COMMAND:
        session.update_session_counters(idle=True)
        return

    txt = _maybe_strip_incoming_mxp(txt)

    if session.account:
        puppet = session.puppet
        if puppet:
            txt = puppet.nicks.nickreplace(
                txt, categories=("inputline"), include_account=True
            )
        else:
            txt = session.account.nicks.nickreplace(
                txt, categories=("inputline"), include_account=False
            )

    kwargs.pop("options", None)

    # ── Semicolon command stacking ───────────────────────────────
    # Split "get sword;wield sword" into two commands.
    # Skip splitting for alias/nick commands — semicolons there are
    # part of the alias definition, not command delimiters.
    _first_word = txt.split(None, 1)[0].lower() if txt.strip() else ""
    if ";" in txt and _first_word not in ("alias", "nick", "nickname", "nicks"):
        commands = [cmd.strip() for cmd in txt.split(";") if cmd.strip()]
    else:
        commands = [txt]

    for cmd in commands:
        cmdhandler(session, cmd, callertype="session", session=session, **kwargs)

    session.update_session_counters()
