"""
Holy Insight — divine revelation spell, available from BASIC mastery.

Divine version of Identify. Inherits all template builder methods from
the Divination school's Identify spell but registers as a separate spell
under DIVINE_REVELATION. Additionally detects evil alignment and undead
nature on actor targets.

Divine Sight appendix (actors only):
    - Alignment detection: shows the target's moral alignment
    - Undead detection: flags targets tagged as undead

Scaling (mana cost):
    BASIC(1):  5 mana
    SKILLED(2): 8 mana
    EXPERT(3): 10 mana
    MASTER(4): 14 mana
    GM(5):     16 mana

Cooldown: 0 (utility spell, no combat advantage).
"""

from enums.alignment import Alignment
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.divination.identify import Identify
from world.spells.registry import register_spell


# Alignment display names — evil alignments get a red highlight
_EVIL_ALIGNMENTS = {
    Alignment.LAWFUL_EVIL,
    Alignment.NEUTRAL_EVIL,
    Alignment.CHAOTIC_EVIL,
}


def _format_alignment(alignment):
    """Format an Alignment enum value for display."""
    if alignment is None:
        return "|wUnknown|n"
    name = alignment.value.replace("_", " ").title()
    if alignment in _EVIL_ALIGNMENTS:
        return f"|r{name}|n"
    return f"|w{name}|n"


@register_spell
class HolyInsight(Identify):
    key = "holy_insight"
    aliases = []
    name = "Holy Insight"
    school = skills.DIVINE_REVELATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "any"
    cooldown = 0
    description = (
        "Reveals the divine truth of items and creatures, "
        "including evil and undead nature."
    )
    mechanics = (
        "Utility spell — reveals information, no damage.\n"
        "Syntax: cast holy insight <item or creature>\n"
        "Functions like Identify but also detects evil/undead.\n"
        "Actor identification is level-gated (same as Identify).\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        # Delegate to Identify's full implementation
        success, result = super()._execute(caster, target)

        if not success:
            return (success, result)

        # Only append divine sight for actors
        from typeclasses.actors.base_actor import BaseActor
        if not isinstance(target, BaseActor):
            return (success, result)

        # If result is a message dict (not a string), append to the "first" key
        if not isinstance(result, dict) or "first" not in result:
            return (success, result)

        divine_lines = self._build_divine_sight(target)
        if divine_lines:
            result["first"] = result["first"] + "\n" + "\n".join(divine_lines)

        return (success, result)

    def _build_divine_sight(self, target):
        """Build the divine sight appendix for an actor."""
        lines = ["|Y--- Divine Sight ---|n"]

        # Alignment detection
        alignment = getattr(target, "alignment", None)
        if alignment and isinstance(alignment, Alignment):
            lines.append(f"|YAlignment:|n {_format_alignment(alignment)}")
        else:
            lines.append("|YAlignment:|n |wUnknown|n")

        # Undead detection — check for "undead" tag
        is_undead = target.tags.has("undead", category="creature_type")
        if is_undead:
            lines.append("|Y** This creature is UNDEAD **|n")

        # Evil detection summary
        if alignment and alignment in _EVIL_ALIGNMENTS:
            lines.append("|r** You sense evil intent **|n")

        return lines
