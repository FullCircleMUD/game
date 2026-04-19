"""
True Sight — divination spell, available from SKILLED mastery.

Grants the caster the ability to see HIDDEN actors, objects, fixtures,
and exits. Does NOT remove HIDDEN — the caster silently sees through
physical concealment. Single-purpose: does not detect traps, see
invisible entities, or grant darkvision.

Duration scaling (long-duration utility buff):
    SKILLED(2): 30 minutes, mana 5
    EXPERT(3):  60 minutes, mana 10
    MASTER(4):  90 minutes, mana 15
    GM(5):      120 minutes, mana 20

Anti-stacking: can't recast while active (mana refunded).
Cooldown: 0 (duration-limited buff).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class TrueSight(Spell):
    key = "true_sight"
    aliases = ["ts"]
    name = "True Sight"
    school = skills.DIVINATION
    min_mastery = MasteryLevel.SKILLED
    mana_cost = {2: 5, 3: 10, 4: 15, 5: 20}
    target_type = "self"
    cooldown = 0
    description = "Grants magical sight that pierces physical concealment."
    mechanics = (
        "Self-buff — see HIDDEN entities and objects.\n"
        "Does NOT reveal them to others (only you can see them).\n"
        "Does NOT detect traps or see invisible entities.\n"
        "Duration: 30min (Skilled), 60min (Expert), 90min (Master), 120min (GM).\n"
        "No cooldown — duration-limited."
    )

    # Duration in minutes per tier
    _DURATION_MINUTES = {2: 30, 3: 60, 4: 90, 5: 120}

    def _execute(self, caster, target):
        # Anti-stacking — can't recast while active
        if caster.has_effect("true_sight"):
            tier = self.get_caster_tier(caster)
            caster.mana += self.mana_cost.get(tier, 0)
            return (False, {
                "first": "Your True Sight is already active.",
                "second": None,
                "third": None,
            })

        tier = self.get_caster_tier(caster)
        duration_minutes = self._DURATION_MINUTES.get(tier, 30)
        duration_seconds = duration_minutes * 60

        # No DETECT_INVIS — true sight only pierces physical concealment
        caster.apply_true_sight(duration_seconds, detect_invis=False)

        # Build message
        min_s = "minute" if duration_minutes == 1 else "minutes"
        return (True, {
            "first": (
                f"|MYour eyes tingle with magical energy. "
                f"You can now see hidden things! "
                f"({duration_minutes} {min_s})|n"
            ),
            "second": None,  # self-cast
            "third": (
                f"|M{caster.key}'s eyes begin to glow with a faint "
                f"magical light.|n"
            ),
        })
