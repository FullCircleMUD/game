"""
Gnoll — aggressive raider with Rampage ability.

The toughest standard mob in the Millholm southern plains. Gnolls are
brutal fighters that become more dangerous as they kill — when a gnoll
slays a target, it immediately attacks the next enemy with zero delay
(Rampage), provided by RampageMixin.

Stats: L4, 40HP, 1d6+2 damage, AC 14, STR 14, DEX 10.
Designed for parties of level 4-5. A solo L4 can beat one with effort;
solo L2-3 should avoid them.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.mixins.mob_behaviours.rampage_mixin import RampageMixin


class Gnoll(RampageMixin, AggressiveMob):
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
    initiative_speed = AttributeProperty(1)
    damage_dice = AttributeProperty("1d6")  # +2 from STR 14 via effective_damage_bonus
    attack_message = AttributeProperty("slashes at")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(6)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(8)

    # ── Knowledge loot ──
    spawn_scrolls_max = AttributeProperty({"basic": 1})
    spawn_recipes_max = AttributeProperty({"basic": 1})

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.25)  # fights to 25% HP before fleeing
    max_per_room = AttributeProperty(2)
    rampage_message = AttributeProperty(
        "|r{name} snarls with bloodlust and turns on {target}!|n"
    )

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(8)
    respawn_delay = AttributeProperty(180)

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
