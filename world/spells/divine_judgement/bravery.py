"""
Bravery — divine judgement spell, available from BASIC mastery.

Self-buff that steels the paladin for battle, granting an AC bonus
and bonus max HP (healed immediately). The paladin's pre-combat
preparation spell.

Scaling:
    BASIC(1):   +1 AC, +5 HP,  5 min,  mana 5
    SKILLED(2): +1 AC, +10 HP, 10 min, mana 8
    EXPERT(3):  +2 AC, +15 HP, 10 min, mana 12
    MASTER(4):  +2 AC, +20 HP, 15 min, mana 16
    GM(5):      +3 AC, +25 HP, 15 min, mana 20

Cannot stack with itself. On expiry, hp_max drops and current HP is
clamped (handled automatically by _recalculate_stats).
"""

from enums.mastery_level import MasteryLevel
from enums.named_effect import NamedEffect
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# (ac_bonus, hp_bonus, duration_minutes) per tier
_SCALING = {
    1: (1, 5, 5),
    2: (1, 10, 10),
    3: (2, 15, 10),
    4: (2, 20, 15),
    5: (3, 25, 15),
}


@register_spell
class Bravery(Spell):
    key = "bravery"
    aliases = ["brave"]
    name = "Bravery"
    school = skills.DIVINE_JUDGEMENT
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 12, 4: 16, 5: 20}
    target_type = "self"
    cooldown = 0
    description = "Steels the caster with divine courage, bolstering armour and vitality."
    mechanics = (
        "Self-buff — grants AC bonus and bonus max HP (healed immediately).\n"
        "Basic: +1 AC, +5 HP / 5 min. Skilled: +1 AC, +10 / 10 min.\n"
        "Expert: +2 AC, +15 / 10 min. Master: +2 AC, +20 / 15 min.\n"
        "Grandmaster: +3 AC, +25 / 15 min.\n"
        "Cannot stack with itself.\n"
        "On expiry, bonus HP is lost and current HP is clamped.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)

        # Anti-stacking — can't recast while active
        if caster.has_effect("bravery"):
            caster.mana += self.mana_cost.get(tier, 0)
            return (False, {
                "first": "Your Bravery is already active.",
                "second": None,
                "third": None,
            })

        ac_bonus, hp_bonus, duration_minutes = _SCALING.get(tier, (1, 5, 5))
        duration_seconds = duration_minutes * 60

        caster.apply_named_effect(
            NamedEffect.BRAVERY,
            effects=[
                {"type": "stat_bonus", "stat": "armor_class", "value": ac_bonus},
                {"type": "stat_bonus", "stat": "hp_max", "value": hp_bonus},
            ],
            duration=duration_seconds,
        )

        # Heal by the HP bonus amount (up to new effective max)
        eff_max = caster.effective_hp_max
        heal = min(hp_bonus, eff_max - caster.hp)
        if heal > 0:
            caster.hp += heal

        min_s = "minute" if duration_minutes == 1 else "minutes"
        return (True, {
            "first": (
                f"|WDivine courage fills you! "
                f"(+{ac_bonus} AC, +{hp_bonus} HP, {duration_minutes} {min_s})|n"
            ),
            "second": None,
            "third": (
                f"|W{caster.key} straightens with divine courage, "
                f"looking tougher and more resolute.|n"
            ),
        })
