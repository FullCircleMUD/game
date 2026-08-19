"""
CmdSetNPCSpeech — speech commands an NPC runs on itself.

NPCs speak the way players do: ``execute_cmd("say to <name> <text>")``
resolves through this cmdset, so one listener loop serves both. Deaf and
sleeping listeners, per-listener naming in the dark and language garbling
all come from `CmdSay` rather than being reimplemented for NPCs.

Service NPCs carry ``call:true()`` so players standing nearby can reach
their shop and trainer commands — which would also merge a second `say`
into every one of those players' command pools. `CmdNPCSay` refuses
player characters, so it never competes with the player's own `say`.
"""

from evennia import CmdSet

from commands.all_char_cmds.cmd_say import CmdSay
from utils.targeting.predicates import p_is_character


class CmdNPCSay(CmdSay):
    """`say` for NPC use — identical, but a player character can't call it."""

    def access(self, srcobj, access_type="cmd", default=False, session=None):
        """Refuse player characters; they have their own `say`."""
        if access_type == "cmd" and p_is_character(srcobj, srcobj):
            return False
        return super().access(
            srcobj, access_type, default=default, session=session
        )


class CmdSetNPCSpeech(CmdSet):
    """Speech commands for NPCs — the same commands players use."""

    key = "CmdSetNPCSpeech"

    def at_cmdset_creation(self):
        self.add(CmdNPCSay())
