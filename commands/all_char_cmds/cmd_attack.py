"""
CmdAttack — basic melee/ranged attack command.

Initiates combat with a free instigator attack, rolls initiative for all
participants, and starts staggered repeating attack tickers.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from combat.combat_utils import enter_combat
from combat.height_utils import can_reach_target
from enums.condition import Condition
from utils.targeting.helpers import resolve_target


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

        # Determine weapon range for height filtering.
        # TODO: temporary call-site mapping for POC. When weapons gain
        # a universal `range` attribute (matching spells), this mapping
        # goes away and we pass weapon.range directly.
        weapon = caller.get_slot("WIELD") if hasattr(caller, "get_slot") else None
        if weapon and getattr(weapon, "weapon_type", "melee") == "missile":
            attack_range = "ranged"
        elif getattr(caller, "mob_weapon_type", None) == "missile":
            attack_range = "ranged"
        else:
            attack_range = "melee"

        target, _ = resolve_target(
            caller, search_term, "actor_hostile", range=attack_range,
        )

        if target is None:
            # resolve_target already sent the error message
            return

        if target == caller:
            caller.msg("You can't attack yourself.")
            return

        # Belt-and-suspenders height check — resolve_target already
        # filters by height via the range parameter, but this catches
        # edge cases like innate ranged with limited range that the
        # simple melee/ranged binary doesn't express.
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
