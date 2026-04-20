"""
Greater Invisibility — illusion spell, available from MASTER mastery.

Superior invisibility that does NOT break on attacking or casting.
Can be cast on self or an ally. Uses the existing INVISIBLE condition
but with different removal logic (no break-on-action).

Scaling:
    MASTER(4):  5 minutes duration,  mana 56
    GM(5):      10 minutes duration, mana 64

Cooldown: 0 (duration-limited buff).

DEPENDENCY: Needs INVISIBLE condition with a flag or separate tracking
to distinguish "breaks on action" (standard) from "persistent" (greater).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class GreaterInvisibility(Spell):
    key = "greater_invisibility"
    aliases = ["gi"]
    name = "Greater Invisibility"
    school = skills.ILLUSION
    min_mastery = MasteryLevel.MASTER
    mana_cost = {4: 56, 5: 64}
    target_type = "actor_friendly"
    cooldown = 0
    description = "Renders you or an ally invisible — persists even while attacking."
    mechanics = (
        "Cast on self or ally. Uses INVISIBLE condition.\n"
        "Unlike standard Invisibility, does NOT break on attack or cast.\n"
        "Target remains invisible while fighting, casting, and moving.\n"
        "Duration: 5min (Master), 10min (GM).\n"
        "Mass Revelation at Master+ tier strips this.\n"
        "No cooldown."
    )

    # Duration in minutes per tier
    _DURATION = {
        4: 5,
        5: 10,
    }

    def _execute(self, caster, target):
        # SCAFFOLD: Implementation pending.
        #
        # When implemented:
        #   1. Apply INVISIBLE condition to target (self or ally)
        #   2. Set db.greater_invisibility = True on target
        #      (flag tells attack/cast hooks NOT to break invisibility)
        #   3. Start timer script for duration
        #      - On expiry: remove INVISIBLE condition, clear greater_invisibility flag
        #   4. Return multi-perspective messages
        #
        # Note: Uses existing INVISIBLE condition. The db.greater_invisibility
        # flag differentiates from standard Invisibility. When attack/cast
        # hooks check whether to break invisibility, they skip if this flag
        # is set.
        #
        # Needs:
        #   - db.greater_invisibility flag on characters
        #   - Attack/cast hooks to check flag before breaking INVISIBLE
        #   - Timer script for duration
        raise NotImplementedError(
            "Greater Invisibility implementation pending — needs "
            "greater_invisibility flag and attack hook integration."
        )
