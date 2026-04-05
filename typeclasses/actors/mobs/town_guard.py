"""
Town Guards — Millholm South Gate garrison.

First humanoid mobs with full equipment and combat skills. Three
variants, all passive (fight back when attacked, don't aggro):

- **MeleeGuard** — leather armor, wooden shield, bronze shortsword.
  Skilled shortsword, skilled bash. Level 5, 65 HP. Tier 2 (lore).
- **RangedGuard** — leather armor, shortbow. Skilled bow, skilled
  bash. Level 5, 65 HP. Tier 2 (lore).
- **GuardSergeant** — studded leather armor, bronze greatsword.
  Expert greatsword, expert bash. Level 8, 98 HP. Tier 3 (lore +
  long-term memory).

Guards follow the sergeant via MobFollowableMixin. When any guard
is attacked, enter_combat() pulls in the entire group — all guards
and the sergeant fight together. Groups auto-reform after staggered
respawns via ai_idle() reacquire.

All guards are human warriors (emulated — no actual class needed).
Stats: STR 14, DEX 12, CON 12, INT 10, WIS 10, CHA 10.

Equipment spawned via MobItem.spawn_mob_item() from shared prototypes.
Abilities composed via BashAbility + WeaponMasteryMixin.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.mastery_level import MasteryLevel
from typeclasses.actors.mob import LLMCombatMob
from typeclasses.items.mob_items.mob_item import MobItem
from typeclasses.mixins.mob_abilities.combat_abilities import BashAbility
from typeclasses.mixins.mob_abilities.weapon_mastery import WeaponMasteryMixin
from typeclasses.mixins.mob_behaviours.mob_followable_mixin import MobFollowableMixin
from typeclasses.mixins.wearslots.humanoid_wearslots import HumanoidWearslotsMixin


def _set_guard_stats(mob, hp, level, initiative=1):
    """Set base and current stats for a guard mob.

    Sets base_* values first (Tier 1) so that _recalculate_stats()
    (triggered by wear/buff changes) rebuilds Tier 2 correctly.
    Then sets current values and HP.
    """
    # Tier 1 — base values (never changed by recalculate)
    mob.base_strength = 14
    mob.base_dexterity = 12
    mob.base_constitution = 12
    mob.base_intelligence = 10
    mob.base_wisdom = 10
    mob.base_charisma = 10
    mob.base_armor_class = 10
    mob.base_hp_max = hp

    # Tier 2 — current values (rebuilt by _recalculate_stats)
    mob.strength = 14
    mob.dexterity = 12
    mob.constitution = 12
    mob.intelligence = 10
    mob.wisdom = 10
    mob.charisma = 10
    mob.armor_class = 10
    mob.hp_max = hp
    mob.hp = hp

    # Other
    mob.level = level
    mob.initiative_speed = initiative


# ── Sergeant defined first — guards reference it as squad_leader_typeclass ──

class GuardSergeant(BashAbility, WeaponMasteryMixin, HumanoidWearslotsMixin, LLMCombatMob):
    """Guard sergeant with greatsword and studded leather armor.

    Tier 3: lore-aware with long-term character memory. Remembers
    who caused trouble, who's been helpful, and past conversations.

    Squad leader — guards follow this mob via MobFollowableMixin.
    Does not need MobFollowableMixin itself (it's the leader, not
    a follower). Gets FollowableMixin from CombatMob.
    """

    alignment_influence = AttributeProperty(-30)  # killing a guard is evil

    room_description = AttributeProperty("stands watch here, a bronze greatsword resting across broad shoulders.")

    # ── LLM (Tier 3: lore + long-term memory) ──
    llm_prompt_file = AttributeProperty("guard_sergeant.md")
    llm_use_lore = AttributeProperty(True)
    llm_use_vector_memory = AttributeProperty(True)
    llm_speech_mode = AttributeProperty("name_match")
    llm_personality = AttributeProperty(
        "A grizzled veteran who has seen it all. Blunt, no-nonsense, "
        "and deeply protective of the town. Speaks with clipped military "
        "efficiency. Respects strength and directness, has no patience "
        "for fools or troublemakers. Knows every face that comes through "
        "the south gate and remembers who caused problems."
    )

    default_weapon_masteries = {"greatsword": MasteryLevel.EXPERT.value}
    # Override BashAbility default mastery to EXPERT
    ability_mastery = MasteryLevel.EXPERT

    # ── Combat fallbacks ──
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

    def ai_wander(self):
        """Stationary — sergeant stays at the gate."""
        pass

    def at_object_creation(self):
        super().at_object_creation()
        _set_guard_stats(self, hp=98, level=8, initiative=0)
        self._equip_gear()

    def _equip_gear(self):
        """Spawn and equip gear from prototypes."""
        armor = MobItem.spawn_mob_item("studded_leather_armor", location=self)
        if armor:
            self.wear(armor)
        weapon = MobItem.spawn_mob_item("bronze_greatsword", location=self)
        if weapon:
            self.wear(weapon)


# ── Guards — follow the sergeant via MobFollowableMixin ──

class MeleeGuard(BashAbility, WeaponMasteryMixin, MobFollowableMixin, HumanoidWearslotsMixin, LLMCombatMob):
    """Town guard with shortsword, shield, and leather armor.

    Tier 2: lore-aware with short-term memory. Can give basic
    directions and answer questions about the town.

    Follows the GuardSergeant via MobFollowableMixin. Auto-reacquires
    the sergeant on each AI idle tick if not currently following.
    Stationary — does not wander from post.
    """

    room_description = AttributeProperty("stands guard here, hand on sword hilt.")

    # ── LLM (Tier 2: lore + short-term memory) ──
    llm_prompt_file = AttributeProperty("town_guard.md")
    llm_use_lore = AttributeProperty(True)
    llm_use_vector_memory = AttributeProperty(False)
    llm_speech_mode = AttributeProperty("name_match")
    llm_personality = AttributeProperty(
        "A professional town guard. Dutiful, alert, and not very "
        "talkative on duty. Can give directions and basic information "
        "about the town but keeps it brief — there's a gate to watch."
    )
    default_weapon_masteries = {"shortsword": MasteryLevel.SKILLED.value}
    squad_leader_typeclass = GuardSergeant

    def ai_wander(self):
        """Stationary — gate guards stay at their post."""
        pass

    # ── Combat fallbacks ──
    damage_dice = AttributeProperty("1d6")
    attack_message = AttributeProperty("swings at")
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
        _set_guard_stats(self, hp=65, level=5, initiative=1)
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


class RangedGuard(BashAbility, WeaponMasteryMixin, MobFollowableMixin, HumanoidWearslotsMixin, LLMCombatMob):
    """Town guard with shortbow and leather armor.

    Tier 2: lore-aware with short-term memory.

    Follows the GuardSergeant via MobFollowableMixin.
    Stationary — does not wander from post.
    """

    room_description = AttributeProperty("stands guard here, bow at the ready.")

    # ── LLM (Tier 2: lore + short-term memory) ──
    llm_prompt_file = AttributeProperty("town_guard.md")
    llm_use_lore = AttributeProperty(True)
    llm_use_vector_memory = AttributeProperty(False)
    llm_speech_mode = AttributeProperty("name_match")
    llm_personality = AttributeProperty(
        "A professional town guard. Dutiful, alert, and not very "
        "talkative on duty. Can give directions and basic information "
        "about the town but keeps it brief — there's a gate to watch."
    )
    default_weapon_masteries = {"bow": MasteryLevel.SKILLED.value}
    squad_leader_typeclass = GuardSergeant

    def ai_wander(self):
        """Stationary — gate guards stay at their post."""
        pass

    # ── Combat fallbacks ──
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
        _set_guard_stats(self, hp=65, level=5, initiative=1)
        self._equip_gear()

    def _equip_gear(self):
        """Spawn and equip gear from prototypes."""
        armor = MobItem.spawn_mob_item("leather_armor", location=self)
        if armor:
            self.wear(armor)
        weapon = MobItem.spawn_mob_item("shortbow", location=self)
        if weapon:
            self.wear(weapon)
