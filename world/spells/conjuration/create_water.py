"""
Create Water — conjuration spell, available from BASIC mastery.

Conjures clean drinking water directly into a held water container
(canteen or cask) up to the caster's mastery tier. Mastery scales both
the mana cost and the drinks produced so mastery genuinely matters —
a BASIC mage can't keep up with a sustained thirst load, a GM can.

Scaling (drinks added, capped at container max_capacity):
    BASIC(1):   +1 drink,  3 mana
    SKILLED(2): +2 drinks, 4 mana
    EXPERT(3):  +3 drinks, 6 mana
    MASTER(4):  +4 drinks, 8 mana
    GM(5):      +5 drinks, 10 mana

Mirrors forage's water credit (BASIC+1 → GM+5) so the caster/forager
economic pressure is symmetric across classes. Neither spell nor forage
creates a tradeable water resource — both top up containers the caller
already carries, preserving the canteen/cask supply chain.

Targets an inventory item — the cast command resolves the container
via spell_utils.resolve_spell_target, so the player types e.g.
`cast create water on canteen` and the resolver finds the named container.

Cooldown: 0 (utility spell, spammable).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# Drinks produced per mastery tier — aligns with forage's water credit.
_DRINKS = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}


@register_spell
class CreateWater(Spell):
    key = "create_water"
    aliases = ["cw", "createwater"]
    name = "Create Water"
    school = skills.CONJURATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 4, 3: 6, 4: 8, 5: 10}
    target_type = "inventory_item"
    cooldown = 0
    description = "Conjure clean drinking water into a container, scaled by mastery."
    mechanics = (
        "Targets a water container in your inventory (canteen, cask).\n"
        "Adds drinks equal to your Conjuration mastery tier:\n"
        "  BASIC +1, SKILLED +2, EXPERT +3, MASTER +4, GRANDMASTER +5.\n"
        "Capped at the container's max capacity — overflow is discarded.\n"
        "Refunds mana if the target is already full.\n"
        "No cooldown — utility spell."
    )

    def _execute(self, caster, target):
        if not getattr(target, "is_water_container", False):
            return (False, {
                "first": f"|rYou cannot conjure water into {target.key}.|n",
                "second": None,
                "third": None,
            })

        tier = self.get_caster_tier(caster)
        drinks = _DRINKS.get(tier, 1)

        room_left = target.max_capacity - target.current
        if room_left <= 0:
            # Already full — refund mana (it was deducted by cast() pre-dispatch).
            caster.mana += self.mana_cost.get(tier, 0)
            return (False, {
                "first": f"|y{target.key} is already full.|n",
                "second": None,
                "third": None,
            })

        added = min(drinks, room_left)
        target.current += added
        target._persist_water_state()

        plural = "s" if added != 1 else ""
        return (True, {
            "first": (
                f"|cYou trace a glyph in the air. Crystal-clear water "
                f"shimmers into {target.key}. (+{added} drink{plural})|n"
            ),
            "second": None,
            "third": (
                f"|c{caster.key} traces a glyph in the air. Water shimmers "
                f"into existence and pours into {target.key}.|n"
            ),
        })
