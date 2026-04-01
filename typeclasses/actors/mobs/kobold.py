"""
Kobold — cowardly pack fighter that only attacks with allies present.

Uses PackCourageMixin for pack courage mechanic: a kobold needs at
least `min_allies_to_attack` other living kobolds in the same room to
have the courage to fight.  Solo kobolds flee.  Cornered kobolds (no
valid exit) fight desperately.

Designed for the Millholm Mine — L2 mobs, individually weak but
dangerous in groups of 2-3.

Two variants share identical appearance, stats, and behaviour so players
cannot tell them apart:

- **Kobold** — drops gold, no knowledge loot.
- **KoboldRecipeLoad** — drops a recipe instead of gold.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.mixins.mob_behaviours.pack_courage_mixin import PackCourageMixin


class Kobold(PackCourageMixin, AggressiveMob):
    """A small, cowardly kobold. Fights in packs, flees when alone."""

    size = AttributeProperty("small")

    # ── Stats ──
    hp = AttributeProperty(14)
    hp_max = AttributeProperty(14)
    strength = AttributeProperty(8)
    dexterity = AttributeProperty(14)
    constitution = AttributeProperty(10)
    base_armor_class = AttributeProperty(12)
    armor_class = AttributeProperty(12)
    level = AttributeProperty(2)

    # ── Combat ──
    initiative_speed = AttributeProperty(2)
    damage_dice = AttributeProperty("1d4")
    attack_message = AttributeProperty("stabs at")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(5)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(2)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.7)  # flee early
    min_allies_to_attack = AttributeProperty(1)   # need 1+ ally
    flee_message = AttributeProperty("{name} squeals in panic and flees!")

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(6)
    respawn_delay = AttributeProperty(120)


class KoboldRecipeLoad(Kobold):
    """Kobold variant that carries a recipe instead of gold."""

    loot_gold_max = AttributeProperty(0)
    spawn_recipes_max = AttributeProperty({"basic": 1})
