"""
RampageMixin — on-kill chain attack for mobs.

When a mob with this mixin slays a target it immediately attacks the
next living player it can perceive in the room, bypassing the normal
attack delay. Follows the same pattern as the greatsword's executioner
mechanic.

Usage:
    class Gnoll(RampageMixin, AggressiveMob):
        rampage_message = AttributeProperty(
            "|r{name} snarls with bloodlust and turns on {target}!|n"
        )
"""

import random

from evennia.typeclasses.attributes import AttributeProperty

from utils.targeting.predicates import p_excluding, p_is_character, p_living


class RampageMixin:
    """On kill, instantly attack the next enemy."""

    rampage_message = AttributeProperty(
        "|r{name} snarls with bloodlust and turns on {target}!|n"
    )

    def at_kill(self, victim):
        """Rampage — immediately attack the next enemy on a kill."""
        if not self.is_alive or not self.location:
            return

        targets = self.ai.get_targets_in_room(
            p_is_character, p_living, p_excluding(victim)
        )
        if not targets:
            return

        target = random.choice(targets)

        # Names travel as mapping entries so msg_contents resolves each
        # one per recipient — a concealed target reads as "Someone" to
        # anyone who cannot see them.
        self.location.msg_contents(
            self.rampage_message,
            from_obj=self,
            mapping={"name": self, "target": target},
        )

        from combat.combat_utils import execute_attack
        execute_attack(self, target)
