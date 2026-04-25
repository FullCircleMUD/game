"""
Corren — the Raven Sage of the yew-ringed clearing south of Millholm.

Tier 3 LLM NPC: lore-aware (regional + local + raven-sage scope) with
long-term vector memory. Wanders slowly between the four rooms of his
clearing — the Study, the Hut Porch, the Standing Stones, and the
Herb Garden — at a sage's pace.

Effectively immortal: the seal he keeps depends on him not being able
to die in any ordinary sense. Combat damage is absorbed; he stays
calm and present.

Phase 1 scope: lore source only. No quest, no services, no reputation
gating. Those systems are on the long-term backlog.
"""

import random

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from typeclasses.actors.mob import LLMCombatMob


class Corren(LLMCombatMob):
    """The Raven Sage. Bound to the clearing, knows what nobody else does."""

    alignment_score = AttributeProperty(400)  # neutral good

    room_description = AttributeProperty(
        "stands quietly nearby, watching."
    )

    # ── LLM (Tier 3: lore + long-term memory) ──
    llm_prompt_file = AttributeProperty("raven_sage.md")
    llm_use_lore = AttributeProperty(True)
    llm_use_vector_memory = AttributeProperty(True)
    llm_speech_mode = AttributeProperty("name_match")
    llm_personality = AttributeProperty(
        "Old in a way that has nothing to do with the body. Tired but not "
        "bitter. Speaks slowly, with long pauses. Reserved with strangers, "
        "warm in small doses with those he has come to trust. Does not "
        "lecture. Does not volunteer. Answers what is asked, often "
        "obliquely. Quietly fond of the ravens. Cannot be hurried."
    )

    # ── Stats — ancient, unaging, hard to harm ──
    hp = AttributeProperty(100)
    base_hp_max = AttributeProperty(100)
    hp_max = AttributeProperty(100)
    base_strength = AttributeProperty(12)
    strength = AttributeProperty(12)
    base_dexterity = AttributeProperty(12)
    dexterity = AttributeProperty(12)
    base_constitution = AttributeProperty(16)
    constitution = AttributeProperty(16)
    base_armor_class = AttributeProperty(14)
    armor_class = AttributeProperty(14)
    level = AttributeProperty(10)
    is_immortal = AttributeProperty(True)
    is_unique = AttributeProperty(True)

    # ── Combat fallbacks (only matter if attacked) ──
    initiative_speed = AttributeProperty(2)
    damage_dice = AttributeProperty("1d6")
    damage_type = AttributeProperty(DamageType.BLUDGEONING)
    attack_message = AttributeProperty("turns aside the blow with a quiet word, and lays a hand on")
    attack_delay_min = AttributeProperty(4)
    attack_delay_max = AttributeProperty(8)

    # ── No loot ──
    loot_gold_max = AttributeProperty(0)

    # ── Behavior ──
    max_per_room = AttributeProperty(1)

    # ── AI timing — sage's pace ──
    ai_tick_interval = AttributeProperty(20)
    respawn_delay = AttributeProperty(600)

    def at_object_creation(self):
        super().at_object_creation()
        # Lore scope: he uniquely sees the raven_sage scope on top of
        # the regional + district scope inherited from his current room.
        if not self.tags.has("raven_sage", category="faction"):
            self.tags.add("raven_sage", category="faction")

    def ai_wander(self):
        """Slow drift through the clearing. About one move every ~6 minutes."""
        if not self.location:
            return
        if self.scripts.get("combat_handler"):
            return
        if random.random() < 0.05:
            self.wander()

    def die(self, cause="unknown", killer=None):
        """Effectively immortal. Damage closes; the seal does not break here."""
        if self.is_immortal:
            self.hp = self.hp_max
            self.is_alive = True
            self.exit_combat()
            if self.location:
                self.location.msg_contents(
                    "Corren stands a moment with eyes closed. The wound closes "
                    "without ceremony, as though it had never been there. He "
                    "looks very tired.",
                    from_obj=self, exclude=[self],
                )
            return
        super().die(cause, killer=killer)
