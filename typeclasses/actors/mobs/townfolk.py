"""
Townfolk — nondescript citizens wandering Millholm streets.

Tier 2 NPC intelligence: lore-aware with short-term rolling memory.
Can answer questions about the town, give directions, share common
knowledge. No long-term memory (they're generic/interchangeable).

Weak, unarmed, no special gear. Passive — fight back if attacked
but won't last long. Exist to populate the town with life, and
as future bait for the town watch arrest system.

Same patrol area as the city watch (city_watch_patrol mob_area).
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mob import LLMCombatMob


class Townfolk(LLMCombatMob):
    """A nondescript townsperson going about their business."""

    room_description = AttributeProperty("hurries past on some errand.")

    # ── LLM (Tier 2: lore + short-term memory) ──
    llm_prompt_file = AttributeProperty("townfolk.md")
    llm_use_lore = AttributeProperty(True)
    llm_use_vector_memory = AttributeProperty(False)
    llm_speech_mode = AttributeProperty("name_match")
    llm_personality = AttributeProperty(
        "An ordinary townsperson — busy, friendly enough if approached "
        "but not looking for a long conversation. You know the town well "
        "and can give directions or share local gossip."
    )

    # ── Combat ──
    damage_dice = AttributeProperty("1d2")
    attack_message = AttributeProperty("flails at")
    attack_delay_min = AttributeProperty(4)
    attack_delay_max = AttributeProperty(6)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(2)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.5)  # flees early
    max_per_room = AttributeProperty(1)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(10)
    respawn_delay = AttributeProperty(600)  # 10 minutes

    def at_object_creation(self):
        super().at_object_creation()
        self.base_strength = 8
        self.base_dexterity = 10
        self.base_constitution = 8
        self.base_intelligence = 10
        self.base_wisdom = 10
        self.base_charisma = 10
        self.strength = 8
        self.dexterity = 10
        self.constitution = 8
        self.intelligence = 10
        self.wisdom = 10
        self.charisma = 10
        self.base_armor_class = 10
        self.armor_class = 10
        self.base_hp_max = 6
        self.hp_max = 6
        self.hp = 6
        self.level = 1
