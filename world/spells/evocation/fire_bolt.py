"""
Fire Bolt — evocation spell, available from BASIC mastery.

Hurls a single bolt of fire at a target. Unlike Magic Missile, this
requires a hit roll (d20 + INT mod + mastery hit bonus vs target AC)
but deals higher damage per tier.

Scaling (single bolt, must hit):
    BASIC(1):   1d8 fire,  mana 3
    SKILLED(2): 2d8 fire,  mana 5
    EXPERT(3):  3d8 fire,  mana 7
    MASTER(4):  4d8 fire,  mana 9
    GM(5):      5d8 fire,  mana 12

Hit roll: d20 + INT modifier + mastery hit bonus (same table as
weapon mastery). Can miss, can crit. Fire damage type — subject
to fire resistance/vulnerability.

No cooldown.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class FireBolt(Spell):
    key = "fire_bolt"
    aliases = ["fbolt", "fb"]
    name = "Fire Bolt"
    school = skills.EVOCATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "hostile"
    cooldown = 0
    description = "Hurls a bolt of fire at a target."
    mechanics = (
        "Single bolt — requires hit roll (d20 + INT mod + mastery bonus vs AC).\n"
        "Damage: 1d8 (Basic) to 5d8 (GM) fire.\n"
        "Can miss. Can crit (double damage dice).\n"
        "Fire damage — subject to resistance/vulnerability.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Fire Bolt implementation pending — needs hit roll using INT "
            "modifier + evocation mastery hit bonus vs target AC, "
            "(tier)d8 fire damage on hit, crit on nat 20, fire damage "
            "type through take_damage() pipeline."
        )
