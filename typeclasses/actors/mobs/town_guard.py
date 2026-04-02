"""
Town Guards — Millholm South Gate garrison.

First humanoid mobs with full equipment and combat skills. Three
variants, all passive (fight back when attacked, don't aggro):

- **MeleeGuard** — leather armor, wooden shield, bronze shortsword.
  Skilled shortsword, skilled bash. Level 5, 65 HP.
- **RangedGuard** — leather armor, shortbow. Skilled bow, skilled
  bash. Level 5, 65 HP.
- **GuardSergeant** — studded leather armor, bronze greatsword.
  Expert greatsword, expert bash. Level 8, 98 HP. Unique boss.

All guards are human warriors (emulated — no actual class needed).
Stats: STR 14, DEX 12, CON 12, INT 10, WIS 10, CHA 10.

Equipment spawned via MobItem.spawn_mob_item() from shared prototypes.
Abilities composed via BashAbility + WeaponMasteryMixin.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.mastery_level import MasteryLevel
from typeclasses.actors.mob import CombatMob
from typeclasses.items.mob_items.mob_item import MobItem
from typeclasses.mixins.mob_abilities.combat_abilities import BashAbility
from typeclasses.mixins.mob_abilities.weapon_mastery import WeaponMasteryMixin
from typeclasses.mixins.wearslots.humanoid_wearslots import HumanoidWearslotsMixin


class MeleeGuard(BashAbility, WeaponMasteryMixin, HumanoidWearslotsMixin, CombatMob):
    """Town guard with shortsword, shield, and leather armor."""

    default_weapon_masteries = {"shortsword": MasteryLevel.SKILLED.value}

    # ── Stats ──
    hp = AttributeProperty(65)
    hp_max = AttributeProperty(65)
    strength = AttributeProperty(14)
    dexterity = AttributeProperty(12)
    constitution = AttributeProperty(12)
    intelligence = AttributeProperty(10)
    wisdom = AttributeProperty(10)
    charisma = AttributeProperty(10)
    base_armor_class = AttributeProperty(10)
    armor_class = AttributeProperty(10)
    level = AttributeProperty(5)

    # ── Combat ──
    initiative_speed = AttributeProperty(1)
    damage_dice = AttributeProperty("1d6")  # fallback if weapon fails
    attack_message = AttributeProperty("swings at")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(5)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(10)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.2)
    max_per_room = AttributeProperty(0)  # no limit

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(6)
    respawn_delay = AttributeProperty(3600)  # 1 hour

    def at_object_creation(self):
        super().at_object_creation()
        self._equip_gear()

    def _equip_gear(self):
        """Spawn and equip gear from prototypes."""
        armor = MobItem.spawn_mob_item("leather_armor", location=self)
        if armor:
            self.wear(armor)
        weapon = MobItem.spawn_mob_item("bronze_shortsword", location=self)
        if weapon:
            self.wear(weapon)
        shield = MobItem.spawn_mob_item("wooden_shield", location=self)
        if shield:
            self.wear(shield)


class RangedGuard(BashAbility, WeaponMasteryMixin, HumanoidWearslotsMixin, CombatMob):
    """Town guard with shortbow and leather armor."""

    default_weapon_masteries = {"bow": MasteryLevel.SKILLED.value}

    # ── Stats ──
    hp = AttributeProperty(65)
    hp_max = AttributeProperty(65)
    strength = AttributeProperty(14)
    dexterity = AttributeProperty(12)
    constitution = AttributeProperty(12)
    intelligence = AttributeProperty(10)
    wisdom = AttributeProperty(10)
    charisma = AttributeProperty(10)
    base_armor_class = AttributeProperty(10)
    armor_class = AttributeProperty(10)
    level = AttributeProperty(5)

    # ── Combat ──
    initiative_speed = AttributeProperty(1)
    damage_dice = AttributeProperty("1d6")
    attack_message = AttributeProperty("fires at")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(5)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(10)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.2)
    max_per_room = AttributeProperty(0)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(6)
    respawn_delay = AttributeProperty(3600)

    def at_object_creation(self):
        super().at_object_creation()
        self._equip_gear()

    def _equip_gear(self):
        """Spawn and equip gear from prototypes."""
        armor = MobItem.spawn_mob_item("leather_armor", location=self)
        if armor:
            self.wear(armor)
        weapon = MobItem.spawn_mob_item("shortbow", location=self)
        if weapon:
            self.wear(weapon)


class GuardSergeant(BashAbility, WeaponMasteryMixin, HumanoidWearslotsMixin, CombatMob):
    """Guard sergeant with greatsword and studded leather armor. Unique boss."""

    default_weapon_masteries = {"greatsword": MasteryLevel.EXPERT.value}
    # Override BashAbility default mastery to EXPERT
    ability_mastery = MasteryLevel.EXPERT

    is_unique = AttributeProperty(True)

    # ── Stats ──
    hp = AttributeProperty(98)
    hp_max = AttributeProperty(98)
    strength = AttributeProperty(14)
    dexterity = AttributeProperty(12)
    constitution = AttributeProperty(12)
    intelligence = AttributeProperty(10)
    wisdom = AttributeProperty(10)
    charisma = AttributeProperty(10)
    base_armor_class = AttributeProperty(10)
    armor_class = AttributeProperty(10)
    level = AttributeProperty(8)

    # ── Combat ──
    initiative_speed = AttributeProperty(0)
    damage_dice = AttributeProperty("2d6")
    attack_message = AttributeProperty("swings at")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(6)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(20)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.15)
    max_per_room = AttributeProperty(1)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(8)
    respawn_delay = AttributeProperty(3600)

    def at_object_creation(self):
        super().at_object_creation()
        self._equip_gear()

    def _equip_gear(self):
        """Spawn and equip gear from prototypes."""
        armor = MobItem.spawn_mob_item("studded_leather_armor", location=self)
        if armor:
            self.wear(armor)
        weapon = MobItem.spawn_mob_item("bronze_greatsword", location=self)
        if weapon:
            self.wear(weapon)
