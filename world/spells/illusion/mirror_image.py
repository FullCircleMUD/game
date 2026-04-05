"""
Mirror Image — illusion spell, available from BASIC mastery.

Creates illusory duplicates of the caster. Each duplicate absorbs
one attack before vanishing. No concentration — fire and forget.

Scaling (number of images):
    BASIC(1):   1 image,  mana 4
    SKILLED(2): 2 images, mana 6
    EXPERT(3):  3 images, mana 8
    MASTER(4):  4 images, mana 10
    GM(5):      5 images, mana 14

Each incoming attack has a chance to hit an image instead of the
caster. When an image is hit, it vanishes. Lasts until all images
are destroyed or combat ends.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class MirrorImage(Spell):
    key = "mirror_image"
    aliases = ["mirror", "mi"]
    name = "Mirror Image"
    school = skills.ILLUSION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 4, 2: 6, 3: 8, 4: 10, 5: 14}
    target_type = "self"
    cooldown = 0
    description = "Creates illusory duplicates that absorb attacks."
    mechanics = (
        "Creates 1-5 mirror images (scales with tier).\n"
        "Each incoming attack may hit an image instead of the caster.\n"
        "Images vanish when hit. Lasts until all destroyed or combat ends.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Mirror Image implementation pending — needs image count "
            "tracking on CombatHandler or ndb, intercept check in "
            "execute_attack() before hit roll, image destruction on hit."
        )
