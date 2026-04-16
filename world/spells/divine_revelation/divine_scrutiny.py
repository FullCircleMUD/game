"""
Divine Scrutiny — divine_revelation spell, available from BASIC mastery.

Cleric mirror of the mage's Augur spell. Reveals stats, abilities,
resistances, conditions, and effects of creatures and players via the
shared inspection templates in `utils/inspection_templates.py`.

For item identification, see Holy Insight (same school, same mastery
gates, but targets items via `target_type = "any_item"`).

Actor mastery gate is level-based (same thresholds as Augur):
    Levels 1-5:   BASIC (tier 1)
    Levels 6-15:  SKILLED (tier 2)
    Levels 16-25: EXPERT (tier 3)
    Levels 26-35: MASTER (tier 4)
    Levels 36+:   GM (tier 5)

Identifying other players requires a PvP room.

Scaling (mana cost):
    BASIC(1):  5 mana
    SKILLED(2): 8 mana
    EXPERT(3): 10 mana
    MASTER(4): 14 mana
    GM(5):     16 mana

Cooldown: 0 (utility spell, no combat advantage).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class DivineScrutiny(Spell):
    key = "divine_scrutiny"
    aliases = ["ds"]
    name = "Divine Scrutiny"
    school = skills.DIVINE_REVELATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "any_actor"
    cooldown = 0
    description = "Reveals the nature and capabilities of a creature through divine insight."
    mechanics = (
        "Utility spell — reveals information, no damage.\n"
        "Syntax: cast divine scrutiny <creature>\n"
        "Actor identification is level-gated:\n"
        "  Levels 1-5: Basic. Levels 6-15: Skilled.\n"
        "  Levels 16-25: Expert. Levels 26-35: Master. 36+: GM.\n"
        "Identifying other players requires a PvP area.\n"
        "For items, use Holy Insight instead.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        from utils.inspection_templates import inspect_actor
        tier = self.get_caster_tier(caster)

        result = inspect_actor(caster, target, tier)

        # If PvP gate returned a hard failure string, refund mana
        # (inspect_actor doesn't know the spell's cost table).
        if not result[0] and isinstance(result[1], str):
            caster.mana += self.mana_cost.get(tier, 0)

        return result
