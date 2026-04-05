"""
Thorn Whip — nature magic spell, available from BASIC mastery.

Lashes a target with a thorny vine, dealing piercing damage and
attempting to pull flying targets down to ground level.

Scaling:
    BASIC(1):   1d6 piercing, mana 3
    SKILLED(2): 2d6 piercing, mana 5
    EXPERT(3):  3d6 piercing, mana 7
    MASTER(4):  4d6 piercing, mana 9
    GM(5):      5d6 piercing, mana 12

Pull effect: contested WIS vs STR. If target is flying (height > 0),
success pulls them to ground (height 0) and removes FLY condition
temporarily (1-3 rounds scaling with tier). Triggers fall damage if
no climbable fixture. HUGE+ immune to pull.

No cooldown.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class ThornWhip(Spell):
    key = "thorn_whip"
    aliases = ["twhip", "tw"]
    name = "Thorn Whip"
    school = skills.NATURE_MAGIC
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "hostile"
    cooldown = 0
    description = "Lashes a target with a thorny vine, dragging flyers to the ground."
    mechanics = (
        "Deals (tier)d6 piercing damage.\n"
        "If target is flying: contested WIS vs STR to pull to ground.\n"
        "Success removes FLY for 1-3 rounds and triggers fall damage.\n"
        "HUGE+ immune to pull. Damage always applies.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Thorn Whip implementation pending — needs piercing damage roll, "
            "height check on target, contested WIS vs STR for pull, "
            "temporary FLY removal via named effect, fall damage trigger, "
            "size gating for pull immunity."
        )
