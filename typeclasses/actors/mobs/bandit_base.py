"""
BobbinBandit — shared parent for the named LLM members of Bobbin Goode's
band of merry bandits, camped in the woods south of Millholm.

These are singletons: each lieutenant has a dedicated mob_area tag
pinning them to one room.

Tone: Mel-Brooks-Men-in-Tights pastiche overlaid on the camp's
established "theatrical comedy with real hardship underneath" register.
Personalities live in the per-character prompt templates under
``llm/prompts/``; this base handles only the shared mechanical setup.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from typeclasses.actors.mob import LLMCombatMob
from typeclasses.mixins.mob_abilities.weapon_mastery import WeaponMasteryMixin
from typeclasses.mixins.wearslots.humanoid_wearslots import HumanoidWearslotsMixin


class BobbinBandit(WeaponMasteryMixin, HumanoidWearslotsMixin, LLMCombatMob):
    """
    Shared base for the named bandits of Bobbin Goode's camp.

    Provides:
      - ``merry_bandits`` faction tag for shared lore scope
      - peaceful-in-camp default (``is_aggressive_to_players=False``)
      - LLM defaults tuned for a six-NPC concentration (cheap model,
        short responses, longer cooldown)
      - shared fallback emote for when the LLM is rate-limited or down

    Subclasses set: stats, ``llm_personality``, ``llm_prompt_file``,
    ``room_description``, weapon equipment, and any character-specific
    hooks (e.g. Bobbin's entry-song chain).
    """

    # ── Identity ──
    alignment_score = AttributeProperty(50)  # mostly-neutral; rob the deserving

    # ── LLM defaults (tuned for six NPCs concentrated in one area) ──
    llm_use_lore = AttributeProperty(True)
    llm_use_vector_memory = AttributeProperty(False)
    llm_speech_mode = AttributeProperty("name_match")
    llm_max_tokens = AttributeProperty(120)
    llm_cooldown_seconds = AttributeProperty(8)
    # llm_model left as None → uses settings.LLM_DEFAULT_MODEL.
    # Override per-NPC if Haiku-tier is preferred for cost reasons.

    # ── Camp policy: peaceful unless attacked first ──
    is_aggressive_to_players = AttributeProperty(False)

    # ── Combat fallbacks (only matter if attacked) ──
    damage_dice = AttributeProperty("1d4")
    damage_type = AttributeProperty(DamageType.SLASHING)
    attack_message = AttributeProperty("swings at")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(5)

    # ── AI timing — ambient camp life, not patrol ──
    ai_tick_interval = AttributeProperty(15)
    max_per_room = AttributeProperty(1)

    # Modest gold; the camp's real wealth is in the barn ledger
    loot_gold_max = AttributeProperty(3)

    default_weapon_masteries = {"shortsword": MasteryLevel.SKILLED.value}

    def at_object_creation(self):
        super().at_object_creation()
        if not self.tags.has("merry_bandits", category="faction"):
            self.tags.add("merry_bandits", category="faction")

    def llm_fallback_response(self, speaker, interaction_type):
        """Used when the LLM is rate-limited, down, or over budget."""
        return "*grins, shrugs theatrically, and gestures toward the common fire*"

    def ai_wander(self):
        """Pinned to their named room — no wandering."""
        return
