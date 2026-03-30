"""
CmdAttack — basic melee/ranged attack command.

Initiates combat with a free instigator attack, rolls initiative for all
participants, and starts staggered repeating attack tickers.
"""

from evennia import Command

from combat.combat_utils import enter_combat
from combat.height_utils import can_reach_target
from enums.condition import Condition


class CmdAttack(Command):
    """
    Attack a target.

    Usage:
        attack <target>
        kill <target>

    Initiates combat with the target and begins auto-attacking.
    Your group members in the same room will also enter combat.
    """

    key = "attack"
    aliases = ["kill", "att", "k"]
    help_category = "Combat"

    def func(self):
        caller = self.caller

        if not self.args or not self.args.strip():
            caller.msg("Attack what?")
            return

        # Search room contents only — quiet=True takes first match instead
        # of showing a disambiguation prompt (MUD convention: attack the
        # first matching mob, use 2.rat for the second).
        results = caller.search(
            self.args.strip(), location=caller.location, quiet=True
        )
        if not results:
            caller.msg(f"You don't see '{self.args.strip()}' here.")
            return
        target = results[0] if isinstance(results, list) else results

        if target == caller:
            caller.msg("You can't attack yourself.")
            return

        if not hasattr(target, "hp") or target.hp is None:
            caller.msg("You can't attack that.")
            return

        if target.hp <= 0:
            caller.msg(f"{target.key} is already dead.")
            return

        # Height reachability check — melee requires same height
        weapon = caller.get_slot("WIELD") if hasattr(caller, "get_slot") else None
        if not can_reach_target(caller, target, weapon):
            caller.msg(
                "They are out of melee range. "
                "You need a ranged weapon or to match their height."
            )
            return

        # Attack from hide — break hidden, grant advantage on free attack
        attacking_from_hide = (
            hasattr(caller, "has_condition")
            and caller.has_condition(Condition.HIDDEN)
        )
        if attacking_from_hide:
            caller.remove_condition(Condition.HIDDEN)
            caller.msg(
                "|yYou strike from the shadows! "
                "You have advantage on your first attack.|n"
            )

        # Attack from invisibility — break invis, grant advantage on free attack
        attacking_from_invis = (
            hasattr(caller, "break_invisibility")
            and caller.has_condition(Condition.INVISIBLE)
        )
        if attacking_from_invis:
            caller.break_invisibility()
            caller.msg(
                "|yYou strike from invisibility! "
                "You have advantage on your first attack.|n"
            )

        caller.msg(f"|rYou attack {target.key}!|n")

        # Enter combat — fires free instigator attack, rolls initiative,
        # starts staggered tickers for all participants.
        enter_combat(
            caller, target,
            instigator=caller,
            instigator_advantage=(attacking_from_hide or attacking_from_invis),
        )
