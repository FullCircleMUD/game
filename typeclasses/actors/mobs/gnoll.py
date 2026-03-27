"""
Gnoll — aggressive raider with Rampage ability.

The toughest standard mob in the Millholm southern plains. Gnolls are
brutal fighters that become more dangerous as they kill — when a gnoll
slays a target, it immediately attacks the next enemy with zero delay
(Rampage).

Stats: L4, 40HP, 1d6+2 damage, AC 14, STR 14, DEX 10.
Designed for parties of level 4-5. A solo L4 can beat one with effort;
solo L2-3 should avoid them.

Rampage: at_kill() fires execute_attack() at the next living enemy in
the room, bypassing the normal 2-8s attack delay. Follows the same
pattern as the greatsword's executioner mechanic.
"""

import random

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob


class Gnoll(AggressiveMob):
    """A savage gnoll raider. Rampages through enemies on a kill."""

    # ── Stats ──
    hp = AttributeProperty(40)
    hp_max = AttributeProperty(40)
    strength = AttributeProperty(14)
    dexterity = AttributeProperty(10)
    constitution = AttributeProperty(14)
    base_armor_class = AttributeProperty(14)
    armor_class = AttributeProperty(14)
    level = AttributeProperty(4)

    # ── Combat ──
    damage_dice = AttributeProperty("1d6")  # +2 from STR 14 via effective_damage_bonus
    attack_message = AttributeProperty("slashes at")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(6)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(12)

    # ── Knowledge loot ──
    spawn_scrolls_max = AttributeProperty({"basic": 1, "skilled": 1})
    spawn_recipes_max = AttributeProperty({"basic": 1, "skilled": 1})

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.25)  # fights to 25% HP before fleeing
    max_per_room = AttributeProperty(2)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(8)
    respawn_delay = AttributeProperty(180)

    # ── Rampage ──

    def at_kill(self, victim):
        """Rampage — immediately attack the next enemy on a kill."""
        if not self.is_alive or not self.location:
            return

        # Find living players still in the room
        targets = [
            obj for obj in self.location.contents
            if obj != victim
            and getattr(obj, "is_pc", False)
            and getattr(obj, "hp", 0) > 0
        ]
        if not targets:
            return

        target = random.choice(targets)

        # Announce the rampage
        self.location.msg_contents(
            f"|r{self.key} snarls with bloodlust and turns on {target.key}!|n",
            from_obj=self,
        )

        # Instant attack — bypasses normal delay
        from combat.combat_utils import execute_attack
        execute_attack(self, target)

    # ── Retreat ──

    def ai_retreating(self):
        """Flee when badly wounded. Unlike dire wolves, gnolls just run."""
        if not self.location:
            return
        if self.hp_fraction >= self.aggro_hp_threshold:
            # Recovered enough to fight again
            self.ai.set_state("wander")
            return
        # Try to flee
        exi = self.ai.pick_random_exit()
        if exi:
            if self.location:
                self.location.msg_contents(
                    f"{self.key} snarls and retreats, wounded!",
                    exclude=[self],
                )
            self.move_to(exi.destination, quiet=False)
