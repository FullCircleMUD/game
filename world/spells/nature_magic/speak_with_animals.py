"""
Speak with Animals — nature magic spell, available from BASIC mastery.

Allows the caster to communicate with animal mobs. Can be used to
calm aggressive animals, gather information, or avoid combat.

Scaling (duration and effect):
    BASIC(1):   5 min,  mana 3  — basic communication
    SKILLED(2): 10 min, mana 5  — can calm aggressive animals
    EXPERT(3):  15 min, mana 7  — animals share info about nearby rooms
    MASTER(4):  30 min, mana 9  — can request animals to scout
    GM(5):      1 hour, mana 12 — animals may fight alongside caster briefly

Recasting refreshes duration.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class SpeakWithAnimals(Spell):
    key = "speak_with_animals"
    aliases = ["swa", "speak animals"]
    name = "Speak with Animals"
    school = skills.NATURE_MAGIC
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "self"
    cooldown = 0
    description = "Grants the ability to communicate with animals."
    mechanics = (
        "Self-buff — understand and speak with animal mobs.\n"
        "Basic: simple communication. Skilled: calm aggression.\n"
        "Expert: animals share info. Master: animals scout.\n"
        "GM: animals fight briefly for caster.\n"
        "Duration: 5 min (Basic) to 1 hour (GM).\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Speak with Animals implementation pending — needs animal mob "
            "detection, LLM or scripted dialogue, aggro suppression at "
            "SKILLED+, info/scout mechanics at higher tiers."
        )
