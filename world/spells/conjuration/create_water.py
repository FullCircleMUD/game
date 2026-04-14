"""
Create Water — conjuration spell, available from BASIC mastery.

A simple utility spell that conjures clean drinking water directly into a
held water container (canteen or cask), filling it to capacity. Mastery
tier doesn't change the refill amount — a full container is a full
container — only the mana cost. Future ambitious tiers could refill all
containers in inventory in one cast, but for now keep it minimal.

Targets an inventory item — the spell command resolves the target via
spell_utils.resolve_item_target, which means the player types e.g.
`cast create water on canteen` and the resolver finds the named container.

Scaling:
    BASIC(1):   1 mana
    SKILLED(2): 1 mana
    EXPERT(3):  1 mana
    MASTER(4):  1 mana
    GM(5):      1 mana

(Cheap utility — the spell is meant to make water effectively free for
mage parties, not a power lever. Higher tiers may unlock multi-container
fills in future.)

Cooldown: 0 (utility spell, spammable).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class CreateWater(Spell):
    key = "create_water"
    aliases = ["cw", "createwater"]
    name = "Create Water"
    school = skills.CONJURATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 1, 2: 1, 3: 1, 4: 1, 5: 1}
    target_type = "inventory_item"
    cooldown = 0
    description = "Conjure clean drinking water into a held container, filling it to capacity."
    mechanics = (
        "Targets a water container in your inventory (canteen, cask).\n"
        "Fills the target container to its maximum capacity.\n"
        "Mana cost: 1 at all mastery tiers.\n"
        "No cooldown — utility spell."
    )

    def _execute(self, caster, target):
        if not getattr(target, "is_water_container", False):
            return (False, {
                "first": f"|rYou cannot conjure water into {target.key}.|n",
                "second": "",
                "third": "",
            })

        success, msg = target.refill_to_full()
        if not success:
            # Already full, or zero capacity — surface the container's reason.
            return (False, {
                "first": f"|y{msg}|n",
                "second": "",
                "third": "",
            })

        return (True, {
            "first": (
                f"|cYou conjure crystal-clear water into {target.key}, "
                f"filling it to the brim.|n"
            ),
            "second": "",
            "third": (
                f"|c{caster.key} traces a glyph in the air. Water "
                f"shimmers into existence and pours into {target.key}.|n"
            ),
        })
