"""
Cure Poison — divine healing spell, available from BASIC mastery.

Removes poison effects from a target. At EXPERT+ also grants
temporary poison resistance via the existing Resist Elements system.

Scaling:
    BASIC(1):   Removes poison,                     mana 4
    SKILLED(2): Removes poison,                     mana 6
    EXPERT(3):  Removes poison + 25% resist 5 min,  mana 8
    MASTER(4):  Removes poison + 50% resist 5 min,  mana 10
    GM(5):      Removes poison + 75% resist 10 min, mana 12

No cooldown. Instant effect (resistance is a timed buff).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# (resistance_pct, duration_seconds) per tier — None for tiers without resist
_RESIST_SCALING = {
    1: None,
    2: None,
    3: (25, 300),   # 25% for 5 min
    4: (50, 300),   # 50% for 5 min
    5: (75, 600),   # 75% for 10 min
}


@register_spell
class CurePoison(Spell):
    key = "cure_poison"
    aliases = ["cpois", "cp"]
    name = "Cure Poison"
    school = skills.DIVINE_HEALING
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 4, 2: 6, 3: 8, 4: 10, 5: 12}
    target_type = "actor_friendly"
    cooldown = 0
    description = "Purges poison from the target's body through divine power."
    mechanics = (
        "Removes all poison effects from target.\n"
        "Expert+: also grants temporary poison resistance.\n"
        "Expert: 25% / 5 min. Master: 50% / 5 min. GM: 75% / 10 min.\n"
        "Refunds mana if target is not poisoned (and no resist would apply).\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        is_poisoned = target.has_effect("poisoned")
        resist_info = _RESIST_SCALING.get(tier)

        if not is_poisoned and not resist_info:
            # Nothing to do — refund mana
            caster.mana += self.mana_cost.get(tier, 0)
            name = "You" if target == caster else target.key
            verb = "aren't" if target == caster else "isn't"
            return (False, f"{name} {verb} poisoned.")

        effects = []

        # Remove poison
        if is_poisoned:
            target.remove_named_effect("poisoned")
            # Also clean up the PoisonDoTScript
            existing_scripts = target.scripts.get("poison_dot")
            if existing_scripts:
                existing_scripts[0].delete()
            effects.append("purged the poison")

        # Apply resistance at EXPERT+
        if resist_info:
            pct, dur = resist_info
            target.apply_resist_element("poison", pct, dur)
            minutes = dur // 60
            effects.append(f"granted {pct}% poison resistance for {minutes} min")

        effect_str = " and ".join(effects)

        if target == caster:
            return (True, {
                "first": f"|WDivine energy courses through you — {effect_str}!|n",
                "second": None,
                "third": f"|W{caster.key} glows with divine energy as poison is purged from their body!|n",
            })
        return (True, {
            "first": f"|WYou channel divine energy into {target.key} — {effect_str}!|n",
            "second": f"|W{caster.key} channels divine energy into you — {effect_str}!|n",
            "third": f"|W{caster.key} channels divine energy into {target.key}, purging poison!|n",
        })
