"""
Cure Blindness — divine healing spell, available from BASIC mastery.

Removes the BLINDED condition from a target. At EXPERT+ also removes
DEAF. Refunds mana if the target is not affected.

Scaling:
    BASIC(1):   Cures BLINDED,            mana 4
    SKILLED(2): Cures BLINDED,            mana 6
    EXPERT(3):  Cures BLINDED + DEAF,     mana 8
    MASTER(4):  Cures BLINDED + DEAF,     mana 10
    GM(5):      Cures BLINDED + DEAF,     mana 12

No cooldown. Instant effect.
"""

from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class CureBlindness(Spell):
    key = "cure_blindness"
    aliases = ["cureblind", "cb"]
    name = "Cure Blindness"
    school = skills.DIVINE_HEALING
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 4, 2: 6, 3: 8, 4: 10, 5: 12}
    target_type = "friendly"
    cooldown = 0
    description = "Removes blindness and deafness through divine healing."
    mechanics = (
        "Removes BLINDED condition from target.\n"
        "Expert+: also removes DEAF.\n"
        "Refunds mana if target is not affected.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        is_blinded = target.has_condition(Condition.BLINDED)
        is_deaf = target.has_condition(Condition.DEAF) if tier >= 3 else False

        if not is_blinded and not is_deaf:
            # Nothing to cure — refund mana
            caster.mana += self.mana_cost.get(tier, 0)
            name = "You" if target == caster else target.key
            verb = "aren't" if target == caster else "isn't"
            return (False, f"{name} {verb} suffering from any ailment this spell can cure.")

        cured = []
        if is_blinded:
            target.remove_condition(Condition.BLINDED)
            cured.append("blindness")
        if is_deaf:
            target.remove_condition(Condition.DEAF)
            cured.append("deafness")

        cured_str = " and ".join(cured)

        if target == caster:
            return (True, {
                "first": f"|WDivine light washes over you, curing your {cured_str}!|n",
                "second": None,
                "third": f"|W{caster.key} glows with divine light as their {cured_str} is cured!|n",
            })
        return (True, {
            "first": f"|WYou lay hands on {target.key}, curing their {cured_str}!|n",
            "second": f"|W{caster.key} lays hands on you, curing your {cured_str}!|n",
            "third": f"|W{caster.key} lays hands on {target.key}, curing their {cured_str}!|n",
        })
