"""
Footpads — hostile thief mobs on Millholm rooftops.

Aggressive L2 rogues that wander the rooftop district and attack
players on sight. Equipped with daggers, SKILLED stab ability.
No armour — rely on high DEX for AC.

The Magpie (FootpadBoss) is a passive L5 rogue on the elevated
Merchant's Rooftop (rooftops_gareth). LLM-powered roleplay, future
quest giver. Fights back when attacked with EXPERT stab + dodge.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from evennia.utils import create

from typeclasses.actors.mob import CombatMob
from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.items.mob_items.mob_item import MobItem
from typeclasses.mixins.llm_mixin import LLMMixin
from typeclasses.mixins.mob_abilities.combat_abilities import StabAbility, DodgeAbility
from typeclasses.mixins.mob_abilities.weapon_mastery import WeaponMasteryMixin
from typeclasses.mixins.wearslots.humanoid_wearslots import HumanoidWearslotsMixin


class Footpad(StabAbility, WeaponMasteryMixin, HumanoidWearslotsMixin, AggressiveMob):
    """Rooftop footpad — aggressive thief with a dagger."""

    alignment_score = AttributeProperty(-100)  # slightly evil (petty criminal)
    default_weapon_masteries = {"dagger": MasteryLevel.SKILLED.value}
    room_description = AttributeProperty(
        "lurks in the shadows, fingers hovering near a sheathed dagger."
    )

    # ── Combat fallbacks ──
    damage_dice = AttributeProperty("1d4")
    damage_type = AttributeProperty(DamageType.PIERCING)  # dagger fallback
    attack_message = AttributeProperty("stabs at")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(4)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(5)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.5)  # flees at half health
    max_per_room = AttributeProperty(2)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(6)

    def at_object_creation(self):
        super().at_object_creation()
        # Stats — high DEX thief
        self.base_strength = 8
        self.base_dexterity = 16
        self.base_constitution = 10
        self.base_intelligence = 12
        self.base_wisdom = 10
        self.base_charisma = 8
        self.strength = 8
        self.dexterity = 16
        self.constitution = 10
        self.intelligence = 12
        self.wisdom = 10
        self.charisma = 8
        self.base_armor_class = 10
        self.armor_class = 10
        self.base_hp_max = 10
        self.hp_max = 10
        self.hp = 10
        self.level = 2
        self.initiative_speed = 3
        # Equip
        weapon = MobItem.spawn_mob_item("training_dagger", location=self)
        if weapon:
            self.wear(weapon)


class FootpadBoss(
    StabAbility,
    DodgeAbility,
    WeaponMasteryMixin,
    LLMMixin,
    HumanoidWearslotsMixin,
    CombatMob,
):
    """The Magpie — rooftop kingpin. Passive, talks via LLM, fights if attacked."""

    default_weapon_masteries = {"dagger": MasteryLevel.EXPERT.value}
    # Override StabAbility mastery to EXPERT
    ability_mastery = MasteryLevel.EXPERT

    # ── Combat fallbacks ──
    damage_dice = AttributeProperty("1d4")
    damage_type = AttributeProperty(DamageType.SLASHING)  # dagger fallback
    attack_message = AttributeProperty("slashes at")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(4)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(5)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.25)
    max_per_room = AttributeProperty(1)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(8)

    # ── LLM ──
    llm_prompt_file = AttributeProperty("footpad_boss.md")
    llm_use_vector_memory = AttributeProperty(True)

    def at_object_creation(self):
        super().at_object_creation()
        # Stats — expert rogue
        self.base_strength = 10
        self.base_dexterity = 16
        self.base_constitution = 12
        self.base_intelligence = 14
        self.base_wisdom = 12
        self.base_charisma = 14
        self.strength = 10
        self.dexterity = 16
        self.constitution = 12
        self.intelligence = 14
        self.wisdom = 12
        self.charisma = 14
        self.base_armor_class = 10
        self.armor_class = 10
        self.base_hp_max = 35
        self.hp_max = 35
        self.hp = 35
        self.level = 5
        self.initiative_speed = 3
        # Equip
        weapon = MobItem.spawn_mob_item("iron_dagger", location=self)
        if weapon:
            self.wear(weapon)
        # Key to the rooftop stash — transfers to corpse on death
        from typeclasses.world_objects.key_item import KeyItem
        key = create.create_object(
            KeyItem,
            key="a tarnished brass key",
            location=self,
        )
        key.key_tag = "magpie_stash"
        key.db.desc = "A small brass key, worn smooth from use. It has a magpie etched into the bow."
        # LLM init
        if hasattr(self, "at_llm_init"):
            self.at_llm_init()

    def ai_wander(self):
        """Stationary — The Magpie stays on his rooftop."""
        pass

    def llm_fallback_response(self, speaker, interaction_type):
        """Fallback when LLM is unavailable."""
        return "*leans back against the chimney and watches you with sharp eyes*"
