"""
Identify — divination spell, available from BASIC mastery.

Item-only identification spell. Reveals stats and properties of NFT items
(weapons, armor, holdables, consumables, containers) via dynamic templates
from `utils/inspection_templates.py`.

For actor identification, see the Augur spell (same school, same mastery
gates, but targets actors via `target_type = "actor_any"`).

Item mastery gate is per-item via the `identify_mastery_gate` attribute
(default BASIC). Some rare or powerful items require higher mastery to
reveal their properties.

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
class Identify(Spell):
    key = "identify"
    aliases = ["id"]
    name = "Identify"
    school = skills.DIVINATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "items_inventory_then_all_room"
    cooldown = 0
    description = "Reveals hidden properties of items."
    mechanics = (
        "Utility spell — reveals information, no damage.\n"
        "Syntax: cast identify <item>\n"
        "Targets items in the room or your inventory.\n"
        "Some items require higher Divination mastery to identify.\n"
        "For creatures, use the Augur spell instead.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        from utils.inspection_templates import inspect_item
        tier = self.get_caster_tier(caster)
        return inspect_item(caster, target, tier)
