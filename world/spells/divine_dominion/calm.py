"""
Calm — divine dominion spell, available from BASIC mastery.

Forces all combatants in the room to stop fighting. Applies a
short-duration CALM effect that prevents re-engaging in combat.

Scaling (peace duration):
    BASIC(1):   10s,  mana 8
    SKILLED(2): 15s,  mana 12
    EXPERT(3):  20s,  mana 16
    MASTER(4):  25s,  mana 20
    GM(5):      30s,  mana 25

Unsafe AoE — affects ALL combatants in the room (enemies AND allies).
Contested WIS vs WIS save for each target. Mobs with HUGE+ size immune.
Caster must be in combat to use.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Calm(Spell):
    key = "calm"
    aliases = ["pacify"]
    name = "Calm"
    school = skills.DIVINE_DOMINION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 8, 2: 12, 3: 16, 4: 20, 5: 25}
    target_type = "none"
    cooldown = 0
    description = "Compels all combatants in the room to cease fighting."
    mechanics = (
        "Unsafe AoE — ends combat for all combatants in the room.\n"
        "Applies a CALM effect preventing re-engagement for 10s (Basic) to 30s (GM).\n"
        "Contested WIS vs WIS save — targets who save are unaffected.\n"
        "HUGE+ creatures are immune.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Calm implementation pending — needs to stop all combat handlers "
            "in the room, apply a timed CALM named effect preventing "
            "enter_combat(), contested WIS saves, size gating."
        )
