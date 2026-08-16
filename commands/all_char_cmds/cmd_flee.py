"""
CmdFlee — attempt to escape combat by fleeing through a random exit.

In combat: the shared flee process in combat_utils — DEX check (d20 + DEX
mod vs DC 10), a random open exit on success, and on failure the lost action
and a round of advantage for every enemy. This command supplies only the
wording; a wimpy threshold firing and a frightened creature compelled to run
use the same implementation with words of their own.

Height advantage: if no enemy has a melee weapon at the same height,
flee auto-succeeds (no DEX check needed).

Out of combat: comic panic run through a random exit (auto-success).
"""

import random

from evennia import Command

from combat.combat_utils import FleeWording, flee_from_combat
from commands.command import FCMCommandMixin
from enums.condition import Condition
from utils.targeting.helpers import open_exits


VOLUNTARY_FLEE = FleeWording(
    to_actor="|rYou flee {direction}!|n",
    failed_to_actor="|rYou try to flee but can't escape!|n",
    failed_in_room="$You() $conj(try) to run but cannot escape!",
    no_exits="|rYou try to flee but there's nowhere to go!|n",
)


def _direction_of(exit_obj):
    """
    The direction to tell the fleeing character they went.

    Exits are keyed by their destination's name, so the key is no use here —
    "You flee Old Trade Way West!" reads as nonsense. Fall back to it only
    when an exit carries no direction at all.
    """
    return getattr(exit_obj, "direction", None) or exit_obj.key


class CmdFlee(FCMCommandMixin, Command):
    """
    Flee from combat through a random exit.

    Usage:
        flee

    In combat, roll a DEX check to escape. On success you flee
    through a random open exit. On failure you lose your action
    and enemies gain advantage against you.

    Out of combat, you panic and run in a random direction.
    """

    key = "flee"
    aliases = []
    help_category = "Combat"

    def func(self):
        caller = self.caller
        handler = caller.scripts.get("combat_handler")

        if handler:
            flee_from_combat(caller, handler[0], VOLUNTARY_FLEE)
        else:
            self._flee_out_of_combat(caller)

    def _flee_out_of_combat(self, caller):
        """Comic panic run — auto-success, random exit.

        Not the combat process: there is no fight to disengage from, so
        there is nothing to roll against and nothing to lose by failing.
        """
        # Bolting is not sneaking. Without this a hidden character could
        # panic-run into the next room and still get a stealth roll there,
        # while the room they left is told someone fled it in plain terms.
        # Combat flee needs no equivalent: attack, stab and join all strip
        # HIDDEN, so nobody reaches a fight still concealed.
        if caller.has_condition(Condition.HIDDEN):
            caller.remove_condition(Condition.HIDDEN)
            caller.msg("|yYou break cover as you bolt!|n")

        exits = open_exits(caller)
        if not exits:
            caller.msg("|yYou panic but there's nowhere to run!|n")
            if caller.location:
                caller.location.msg_contents(
                    "$You() $conj(look) around in a panic but "
                    "there's nowhere to run!",
                    from_obj=caller,
                    exclude=[caller],
                )
            return

        chosen = random.choice(exits)
        direction = _direction_of(chosen)

        caller.msg(f"|yYou panic and flee {direction}!|n")

        # One-off wording, so it is passed rather than given a flag of its own.
        chosen.at_traverse(
            caller,
            chosen.destination,
            move_type="flee",
            msg_from="{name} panics and flees {direction} for no apparent reason!",
            msg_to="{name} arrives {direction}, in a blind panic.",
        )
