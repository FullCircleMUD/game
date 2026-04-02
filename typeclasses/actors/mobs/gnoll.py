"""
Gnoll — aggressive raider with Rampage ability.

The toughest standard mob in the Millholm southern plains. Gnolls are
brutal fighters that become more dangerous as they kill — when a gnoll
slays a target, it immediately attacks the next enemy with zero delay
(Rampage), provided by RampageMixin.

Stats: L4, 40HP, 1d6+2 damage, AC 14, STR 14, DEX 10.
Designed for parties of level 4-5. A solo L4 can beat one with effort;
solo L2-3 should avoid them.

Three variants share identical appearance, stats, and behaviour so
players cannot tell them apart:

- **Gnoll** — drops gold, no knowledge loot.
- **GnollRecipeLoad** — drops a recipe instead of gold.
- **GnollScrollLoad** — drops a scroll instead of gold.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.mastery_level import MasteryLevel
from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.items.mob_items.mob_item import MobItem
from typeclasses.mixins.mob_abilities.weapon_mastery import WeaponMasteryMixin
from typeclasses.mixins.mob_behaviours.rampage_mixin import RampageMixin
from typeclasses.mixins.wearslots.humanoid_wearslots import HumanoidWearslotsMixin


class Gnoll(RampageMixin, WeaponMasteryMixin, HumanoidWearslotsMixin, AggressiveMob):
    """A savage gnoll raider. Rampages through enemies on a kill.

    Equipped with crude hide armor (leather) and bronze spear.
    BASIC spear mastery — no special abilities yet, just base damage.
    """

    default_weapon_masteries = {"spear": MasteryLevel.BASIC.value}

    # ── Stats ──
    hp = AttributeProperty(40)
    base_hp_max = AttributeProperty(40)
    hp_max = AttributeProperty(40)
    base_strength = AttributeProperty(14)
    strength = AttributeProperty(14)
    base_dexterity = AttributeProperty(10)
    dexterity = AttributeProperty(10)
    base_constitution = AttributeProperty(14)
    constitution = AttributeProperty(14)
    base_armor_class = AttributeProperty(14)
    armor_class = AttributeProperty(14)
    level = AttributeProperty(4)

    # ── Combat ──
    initiative_speed = AttributeProperty(0)
    damage_dice = AttributeProperty("1d6")  # +2 from STR 14 via effective_damage_bonus
    attack_message = AttributeProperty("slashes at")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(6)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(3)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.25)  # fights to 25% HP before fleeing
    max_per_room = AttributeProperty(2)
    rampage_message = AttributeProperty(
        "|r{name} snarls with bloodlust and turns on {target}!|n"
    )

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(8)
    respawn_delay = AttributeProperty(180)

    def at_object_creation(self):
        super().at_object_creation()
        armor = MobItem.spawn_mob_item("leather_armor", location=self)
        if armor:
            # Rebrand as crude hide for gnoll flavour
            armor.key = "Crude Hide Armor"
            armor.desc = "Rough-cured animal hides lashed together with sinew. Crude but functional."
            self.wear(armor)
        weapon = MobItem.spawn_mob_item("bronze_spear", location=self)
        if weapon:
            self.wear(weapon)

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


class GnollArcher(Gnoll):
    """Gnoll variant with shortbow instead of spear. Covers flying targets."""

    default_weapon_masteries = {"bow": MasteryLevel.BASIC.value}

    def at_object_creation(self):
        # Skip Gnoll's spear equip — archer gets bow
        super(Gnoll, self).at_object_creation()
        armor = MobItem.spawn_mob_item("leather_armor", location=self)
        if armor:
            armor.key = "Crude Hide Armor"
            armor.desc = "Rough-cured animal hides lashed together with sinew. Crude but functional."
            self.wear(armor)
        weapon = MobItem.spawn_mob_item("shortbow", location=self)
        if weapon:
            self.wear(weapon)


class GnollRecipeLoad(Gnoll):
    """Gnoll variant that carries a recipe instead of gold."""

    loot_gold_max = AttributeProperty(0)
    spawn_recipes_max = AttributeProperty({"basic": 1})


class GnollScrollLoad(Gnoll):
    """Gnoll variant that carries a scroll instead of gold."""

    loot_gold_max = AttributeProperty(0)
    spawn_scrolls_max = AttributeProperty({"basic": 1})
