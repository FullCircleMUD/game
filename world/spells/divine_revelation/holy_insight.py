"""
Holy Insight — divine_revelation spell, available from BASIC mastery.

Cleric mirror of the mage's Identify spell. Reveals stats and properties
of items via the shared inspection templates in `utils/inspection_templates.py`.

For creature identification, see Divine Scrutiny (same school, same mastery
gates, but targets actors via `target_type = "actor_any"`).

Item mastery gate is per-item via the `identify_mastery_gate` attribute
(default BASIC).

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
class HolyInsight(Spell):
    key = "holy_insight"
    aliases = []
    name = "Holy Insight"
    school = skills.DIVINE_REVELATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "items_inventory_then_all_room"
    cooldown = 0
    description = "Reveals the divine truth of items through prayer."
    mechanics = (
        "Utility spell — reveals information, no damage.\n"
        "Syntax: cast holy insight <item>\n"
        "Targets items in the room or your inventory.\n"
        "Some items require higher Divine Revelation mastery to identify.\n"
        "For creatures, use Divine Scrutiny instead.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        from utils.inspection_templates import inspect_item
        tier = self.get_caster_tier(caster)
        return inspect_item(caster, target, tier)
