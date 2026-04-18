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

from enums.mastery_level import MasteryLevel
from enums.size import Size
from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.items.mob_items.mob_item import MobItem
from typeclasses.mixins.mob_abilities.weapon_mastery import WeaponMasteryMixin
from typeclasses.mixins.mob_behaviours.pack_courage_mixin import PackCourageMixin
from typeclasses.mixins.wearslots.humanoid_wearslots import HumanoidWearslotsMixin


class Kobold(PackCourageMixin, WeaponMasteryMixin, HumanoidWearslotsMixin, AggressiveMob):
    """A small, cowardly kobold. Fights in packs, flees when alone."""

    alignment_score = AttributeProperty(-60)  # evil (hostile raider)
    base_size = AttributeProperty(Size.SMALL.value)
    size = AttributeProperty(Size.SMALL.value)
    default_weapon_masteries = {"dagger": MasteryLevel.BASIC.value}

    # ── Stats ──
    hp = AttributeProperty(14)
    base_hp_max = AttributeProperty(14)
    hp_max = AttributeProperty(14)
    base_strength = AttributeProperty(8)
    strength = AttributeProperty(8)
    base_dexterity = AttributeProperty(14)
    dexterity = AttributeProperty(14)
    base_constitution = AttributeProperty(10)
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

    def at_object_creation(self):
        super().at_object_creation()
        weapon = MobItem.spawn_mob_item("training_dagger", location=self)
        if weapon:
            self.wear(weapon)


class KoboldRecipeLoad(Kobold):
    """Kobold variant that carries a recipe instead of gold."""

    loot_gold_max = AttributeProperty(0)
    spawn_recipes_max = AttributeProperty({"basic": 1})
