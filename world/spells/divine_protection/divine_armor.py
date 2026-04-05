"""
Divine Armor — divine protection spell, available from BASIC mastery.

Long-duration AC buff for clerics/paladins. The divine equivalent of
Mage Armor — a maintenance buff cast before combat.

Scaling:
    BASIC(1):   +2 AC, 1 hour,  mana 4
    SKILLED(2): +2 AC, 2 hours, mana 6
    EXPERT(3):  +3 AC, 2 hours, mana 8
    MASTER(4):  +3 AC, 3 hours, mana 10
    GM(5):      +4 AC, 3 hours, mana 14

Cannot stack with itself. Stacks with Sanctuary.
Slightly weaker AC than Mage Armor (+2/+4 vs +3/+5) but clerics have
shields and heavier base equipment to compensate.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class DivineArmor(Spell):
    key = "divine_armor"
    aliases = ["da", "darmor"]
    name = "Divine Armor"
    school = skills.DIVINE_PROTECTION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 4, 2: 6, 3: 8, 4: 10, 5: 14}
    target_type = "self"
    cooldown = 0
    description = "Wraps the caster in a shimmering layer of divine protection."
    mechanics = (
        "Self-buff — grants AC bonus for an extended duration.\n"
        "Basic: +2 AC / 1 hour. Skilled: +2 / 2 hours. Expert: +3 / 2 hours.\n"
        "Master: +3 / 3 hours. Grandmaster: +4 / 3 hours.\n"
        "Cannot stack with itself. Stacks with Sanctuary.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Divine Armor implementation pending — needs DIVINE_ARMORED "
            "NamedEffect entry, apply_divine_armor() convenience method, "
            "and anti-stacking check."
        )
