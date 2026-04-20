"""
Holy Sight — Divine Revelation flavour of True Sight.

Functionally identical to True Sight: single capability (see HIDDEN),
same mana cost, same duration scaling, same `true_sight` named effect
(so anti-stacking and visibility checks work uniformly across both).
Only differences are school, name, and flavour wording.
"""

from enums.skills_enum import skills
from world.spells.divination.true_sight import TrueSight
from world.spells.registry import register_spell


@register_spell
class HolySight(TrueSight):
    key = "holy_sight"
    aliases = ["hs"]
    name = "Holy Sight"
    school = skills.DIVINE_REVELATION
    description = "Grants divine sight that pierces physical concealment."
    mechanics = (
        "Self-buff — see HIDDEN entities and objects.\n"
        "Does NOT reveal them to others (only you can see them).\n"
        "Duration: 30min (Skilled), 60min (Expert), 90min (Master), 120min (GM).\n"
        "No cooldown — duration-limited."
    )

    _ALREADY_ACTIVE_MSG = "Your Holy Sight is already active."
    _CAST_FIRST_MSG = (
        "|YDivine light fills your vision. "
        "You can now see hidden things! "
        "({duration_minutes} {min_s})|n"
    )
    _CAST_THIRD_MSG = (
        "|Y{caster_key}'s eyes begin to glow with a warm divine light.|n"
    )
