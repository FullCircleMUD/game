"""
CmdAttack — basic melee/ranged attack command.

Initiates combat with a free instigator attack, rolls initiative for all
participants, and starts staggered repeating attack tickers.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from combat.combat_utils import enter_combat
from enums.condition import Condition
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import check_range


class CmdAttack(FCMCommandMixin, Command):
    """
    Attack a target.

    Usage:
        attack <target>
        kill <target>

    Initiates combat with the target and begins auto-attacking.
    Your group members in the same room will also enter combat.
    """

    key = "attack"
    aliases = ["kill"]
    help_category = "Combat"

    def func(self):
        caller = self.caller

        if not self.args or not self.args.strip():
            caller.msg("Attack what?")
            return

        search_term = self.args.strip()

        weapon = caller.get_slot("WIELD") if hasattr(caller, "get_slot") else None
        attack_range = (
            getattr(weapon, "weapon_type", "melee")
            if weapon
            else getattr(caller, "mob_weapon_type", "melee")
        )

        target, _ = resolve_target(caller, search_term, "actor_hostile")

        if target is None:
            # resolve_target already sent the error message
            return

        if target == caller:
            caller.msg("You can't attack yourself.")
            return

        if not check_range(caller, target, attack_range, source=weapon):
            return  # check_range already messaged

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
