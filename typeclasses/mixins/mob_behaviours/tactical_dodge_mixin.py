"""
TacticalDodgeMixin — random dodge during combat ticks.

Mobs with this mixin have a configurable chance to use the dodge
command (the same CmdDodge available to players) on each combat tick,
sacrificing their attack for a round of disadvantage on incoming hits.

Usage:
    class DireWolf(TacticalDodgeMixin, AggressiveMob):
        dodge_chance = AttributeProperty(0.25)
"""

import random

from evennia.typeclasses.attributes import AttributeProperty


class TacticalDodgeMixin:
    """Randomly uses the dodge command during combat ticks."""

    dodge_chance = AttributeProperty(0.25)

    def at_combat_tick(self, handler):
        """Roll for dodge; execute if lucky."""
        if random.random() < self.dodge_chance:
            self.execute_cmd("dodge")
