"""
Speak with Animals — nature magic spell, available from BASIC mastery.

Allows the caster to communicate with animal mobs. Can be used to
calm aggressive animals, gather information, or avoid combat.

Scaling (duration and effect):
    BASIC(1):    15 min,  mana 3  — basic communication
    SKILLED(2):  30 min,  mana 5  — can calm aggressive animals
    EXPERT(3):   60 min,  mana 7  — animals share info about nearby rooms
    MASTER(4):   90 min,  mana 9  — can request animals to scout
    GM(5):      120 min,  mana 12 — animals may fight alongside caster briefly

Recasting refreshes duration.
"""

from enums.mastery_level import MasteryLevel
from enums.named_effect import NamedEffect
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# Duration in seconds per mastery tier. Per the design docstring above:
# BASIC 15min, SKILLED 30min, EXPERT 60min, MASTER 90min, GM 120min.
_DURATION_SECONDS = {
    1: 15 * 60,
    2: 30 * 60,
    3: 60 * 60,
    4: 90 * 60,
    5: 120 * 60,
}


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
        "Basic: simple communication.\n"
        "Duration: 15 min (Basic) to 2 hours (GM).\n"
        "Higher-tier features (calm aggression, scouting, combat assistance) "
        "are planned follow-ups.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        if caster.has_effect(NamedEffect.SPEAK_WITH_ANIMALS_BUFF.value):
            tier = self.get_caster_tier(caster)
            caster.mana += self.mana_cost.get(tier, 0)
            return (False, {
                "first": "Your bond with the speech of animals is already active.",
                "second": None,
                "third": None,
            })

        tier = self.get_caster_tier(caster)
        duration = _DURATION_SECONDS.get(tier, _DURATION_SECONDS[1])

        caster.apply_named_effect(
            NamedEffect.SPEAK_WITH_ANIMALS_BUFF, duration=duration,
        )

        return (True, {
            "first": None,    # apply_named_effect already sent the start message
            "second": None,
            "third": None,    # apply_named_effect already sent the third-person message
        })
