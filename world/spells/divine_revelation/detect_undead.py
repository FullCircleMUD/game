"""
Detect Undead — divine_revelation spell, available from BASIC mastery.

Area-of-effect room scan that senses all living undead creatures in the
room. No single target needed — the caster prays and the divine answer
reveals any unholy presence.

This is the base implementation. Thin subclasses in other divine schools
(Divine Healing, Divine Protection, Divine Dominion) inherit this logic
and override only key/name/school so clerics can access the spell
regardless of which domain they've trained.

Mana cost: 3 (flat across all tiers — cheap utility).
Cooldown: 0.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class DetectUndead(Spell):
    key = "detect_undead"
    aliases = ["du"]
    name = "Detect Undead"
    school = skills.DIVINE_REVELATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 3, 3: 3, 4: 3, 5: 3}
    target_type = "none"
    cooldown = 0
    description = "Senses all undead creatures in the room."
    mechanics = (
        "Utility spell — room scan, no damage.\n"
        "Syntax: cast detect undead\n"
        "Reveals the names of all living undead in your room.\n"
        "Reports 'no undead presence' if the room is clear.\n"
        "Mana cost: 3 (flat). No cooldown."
    )

    def _execute(self, caster, target):
        room = caster.location
        if not room:
            return (True, {
                "first": "|YYou sense no undead presence.|n",
                "second": None,
                "third": None,
            })

        undead = []
        for obj in room.contents:
            if obj == caster:
                continue
            if getattr(obj, "hp", None) is None or obj.hp <= 0:
                continue
            if obj.tags.has("undead", category="creature_type"):
                undead.append(obj.key)

        if not undead:
            return (True, {
                "first": "|YYou sense no undead presence.|n",
                "second": None,
                "third": (
                    f"|Y{caster.key} murmurs a prayer and opens their eyes, "
                    f"looking relieved.|n"
                ),
            })

        names = ", ".join(undead)
        plural = "presences" if len(undead) > 1 else "presence"
        return (True, {
            "first": (
                f"|r** You sense undead {plural}: {names} **|n"
            ),
            "second": None,
            "third": (
                f"|Y{caster.key} murmurs a prayer and opens their eyes, "
                f"looking alarmed.|n"
            ),
        })
