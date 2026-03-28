"""
RampageMixin — on-kill chain attack for mobs.

When a mob with this mixin slays a target it immediately attacks the
next living player in the room, bypassing the normal attack delay.
Follows the same pattern as the greatsword's executioner mechanic.

Usage:
    class Gnoll(RampageMixin, AggressiveMob):
        rampage_message = AttributeProperty(
            "|r{name} snarls with bloodlust and turns on {target}!|n"
        )
"""

import random

from evennia.typeclasses.attributes import AttributeProperty


class RampageMixin:
    """On kill, instantly attack the next enemy."""

    rampage_message = AttributeProperty(
        "|r{name} snarls with bloodlust and turns on {target}!|n"
    )

    def at_kill(self, victim):
        """Rampage — immediately attack the next enemy on a kill."""
        if not self.is_alive or not self.location:
            return

        targets = [
            obj for obj in self.location.contents
            if obj != victim
            and getattr(obj, "is_pc", False)
            and getattr(obj, "hp", 0) > 0
        ]
        if not targets:
            return

        target = random.choice(targets)

        self.location.msg_contents(
            self.rampage_message.format(name=self.key, target=target.key),
            from_obj=self,
        )

        from combat.combat_utils import execute_attack
        execute_attack(self, target)
