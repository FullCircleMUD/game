"""
Divine Light — divine revelation spell, available from BASIC mastery.

Conjures a hovering sphere of holy radiance that illuminates the room
for an extended duration. Replaces the need for torches/lanterns in
dark areas. No fuel, no held slot consumed.

Scaling (duration only — light is binary):
    BASIC(1):   30 min,  mana 3
    SKILLED(2): 1 hour,  mana 5
    EXPERT(3):  2 hours, mana 7
    MASTER(4):  3 hours, mana 9
    GM(5):      4 hours, mana 12

Attaches a temporary light source to the caster (follows them).
Recasting refreshes duration.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class DivineLight(Spell):
    key = "divine_light"
    aliases = ["dlight"]
    name = "Divine Light"
    school = skills.DIVINE_REVELATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "self"
    cooldown = 0
    description = "Conjures a sphere of holy radiance that follows the caster."
    mechanics = (
        "Creates a magical light source that follows the caster.\n"
        "Illuminates dark rooms without a torch or lantern.\n"
        "Duration: 30 min (Basic) to 4 hours (GM).\n"
        "Recasting refreshes the duration.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Divine Light implementation pending — needs a temporary light "
            "source object or effect attached to the caster, integration "
            "with the room darkness system (is_dark check)."
        )
