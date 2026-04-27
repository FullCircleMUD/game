"""
Librarian — the long-suffering guardian of the Millholm Public Library.

Tier 2 NPC intelligence: lore-aware with short-term rolling memory.
Perpetually shushing people and grumbling about overdue books.
Non-aggressive but technically fightable (weak — it's a librarian).
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mob import LLMCombatMob


class Librarian(LLMCombatMob):
    """The Millholm Public Library's resident guardian of silence."""

    room_description = AttributeProperty(
        "peers over half-moon spectacles with an expression of "
        "pre-emptive disapproval."
    )

    # ── LLM (Tier 2: lore + short-term memory) ──
    llm_prompt_file = AttributeProperty("librarian.md")
    llm_use_lore = AttributeProperty(True)
    llm_use_vector_memory = AttributeProperty(False)
    llm_speech_mode = AttributeProperty("name_match")
    llm_personality = AttributeProperty(
        "A thin, precise woman of indeterminate age with steel-grey hair "
        "pulled into a tight bun and half-moon spectacles perched on a "
        "sharp nose. She regards noise as a personal affront and treats "
        "every book as if it were a sacred relic. She is helpful if "
        "approached quietly and respectfully, but has zero tolerance "
        "for rowdiness, loud voices, or mistreatment of library property. "
        "She knows the library's collection intimately and can point "
        "people to the right section for any topic."
    )

    # ── Combat (minimal — she's a librarian) ──
    damage_dice = AttributeProperty("1d2")
    attack_message = AttributeProperty("swats at")
    attack_delay_min = AttributeProperty(5)
    attack_delay_max = AttributeProperty(7)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(1)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.8)  # flees very early
    max_per_room = AttributeProperty(1)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(15)

    def ai_wander(self):
        """Stationary — the librarian stays at the front desk."""
        pass

    def at_object_creation(self):
        super().at_object_creation()
        self.base_strength = 7
        self.base_dexterity = 10
        self.base_constitution = 8
        self.base_intelligence = 14
        self.base_wisdom = 14
        self.base_charisma = 8
        self.strength = 7
        self.dexterity = 10
        self.constitution = 8
        self.intelligence = 14
        self.wisdom = 14
        self.charisma = 8
        self.base_armor_class = 10
        self.armor_class = 10
        self.base_hp_max = 5
        self.hp_max = 5
        self.hp = 5
        self.level = 1
