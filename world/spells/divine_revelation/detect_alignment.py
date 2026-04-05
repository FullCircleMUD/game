"""
Detect Alignment — divine revelation spell, available from BASIC mastery.

Reveals the alignment of a target creature. At higher tiers, also
reveals alignment intensity and detects undead/fiendish aura.

Scaling:
    BASIC(1):   Broad alignment (good/neutral/evil), mana 2
    SKILLED(2): Axis alignment (lawful good, chaotic neutral, etc.), mana 3
    EXPERT(3):  + detects undead aura, mana 4
    MASTER(4):  + detects fiendish/celestial aura, mana 5
    GM(5):      + reveals alignment of all creatures in room, mana 8

No cooldown. Instant effect (no duration).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class DetectAlignment(Spell):
    key = "detect_alignment"
    aliases = ["dalign", "detect align"]
    name = "Detect Alignment"
    school = skills.DIVINE_REVELATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 2, 2: 3, 3: 4, 4: 5, 5: 8}
    target_type = "any"
    cooldown = 0
    description = "Divinely reveals the alignment of a creature."
    mechanics = (
        "Reveals target's alignment.\n"
        "Basic: broad (good/neutral/evil). Skilled: full axis.\n"
        "Expert: + undead aura. Master: + fiendish/celestial aura.\n"
        "GM: reveals alignment of all creatures in room.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Detect Alignment implementation pending — needs alignment "
            "display logic, tier-based detail scaling, and GM-tier "
            "room-wide variant."
        )
