"""
Locate Object — divination spell, available from BASIC mastery.

Reveals the location of a named object or type of object within
range. At higher tiers, range and detail increase.

Scaling:
    BASIC(1):   Same room/inventory only,      mana 3
    SKILLED(2): Same district,                  mana 5
    EXPERT(3):  Same zone,                      mana 8
    MASTER(4):  Any zone + room name,           mana 12
    GM(5):      Any zone + room name + holder,  mana 16

No cooldown. Instant effect.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class LocateObject(Spell):
    key = "locate_object"
    aliases = ["locate", "loc"]
    name = "Locate Object"
    school = skills.DIVINATION
    min_mastery = MasteryLevel.BASIC
    has_spell_arg = True
    mana_cost = {1: 3, 2: 5, 3: 8, 4: 12, 5: 16}
    target_type = "none"
    cooldown = 0
    description = "Magically senses the location of a named object."
    mechanics = (
        "Searches for an object by name within range.\n"
        "Basic: same room/inventory. Skilled: same district.\n"
        "Expert: same zone. Master: any zone + room name.\n"
        "GM: any zone + room name + who is holding it.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Locate Object implementation pending — needs spell_arg for "
            "object name, ObjectDB search scoped by tier range, "
            "district/zone tag filtering."
        )
