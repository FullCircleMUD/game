"""
Resist — abjuration spell, available from SKILLED mastery.

Grants resistance to a single damage type for a short duration.
The caster must specify which element when casting:
    cast resist fire
    cast resist cold bob

Valid elements: fire, cold, lightning, acid, poison.

Resistance scaling (percentage per tier):
    SKILLED(2): 20% resistance, mana 8
    EXPERT(3):  30% resistance, mana 10
    MASTER(4):  40% resistance, mana 14
    GM(5):      60% resistance, mana 16

Duration: 30 seconds flat at all tiers. Powerful spell, short window.
Parties will want to pre-buff tanks before fights.

Each element is a separate named effect (resist_fire, resist_cold, etc.)
so multiple elements can be resisted simultaneously at the cost of
multiple casts and mana.

At GM with 60% resistance, the target takes only 40% damage from that
type. System cap is 75% (from DamageResistanceMixin), so GM + racial
resistance could push close but never exceed cap.

Cooldown: 0 (spammable — need to buff quickly before the 30s window).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# Valid elements for resist — elemental damage types only
_VALID_ELEMENTS = {"fire", "cold", "lightning", "acid", "poison"}


@register_spell
class ResistElements(Spell):
    key = "resist"
    aliases = ["re"]
    name = "Resist"
    school = skills.ABJURATION
    min_mastery = MasteryLevel.SKILLED
    mana_cost = {2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "actor_friendly"
    has_spell_arg = True
    cooldown = 0
    description = "Grants resistance to a single damage type for a short duration."
    mechanics = (
        "Usage: cast resist <element> [target] "
        "(fire, cold, lightning, acid, poison).\n"
        "One casting = one damage type. Multiple castings for broad coverage.\n"
        "Skilled: 20%. Expert: 30%. Master: 40%. Grandmaster: 60%.\n"
        "Duration: 30 seconds at all tiers.\n"
        "Stacks with racial/gear resistances up to 75% cap.\n"
        "No cooldown."
    )

    # Resistance percentage per tier
    _SCALING = {
        2: 20,
        3: 30,
        4: 40,
        5: 60,
    }

    def _execute(self, caster, target, **kwargs):
        tier = self.get_caster_tier(caster)
        element = kwargs.get("spell_arg")

        # --- Validate element ---
        if not element or element not in _VALID_ELEMENTS:
            # Refund mana
            caster.mana += self.mana_cost.get(tier, 0)
            valid = ", ".join(sorted(_VALID_ELEMENTS))
            return (False, {
                "first": (
                    f"Resist what element? "
                    f"Usage: cast resist <{valid}> [target]"
                ),
                "second": None,
                "third": None,
            })

        effect_key = f"resist_{element}"

        # --- Anti-stacking ---
        if target.has_effect(effect_key):
            caster.mana += self.mana_cost.get(tier, 0)
            who = "You already have" if target == caster else f"{target.key} already has"
            return (False, {
                "first": f"{who} {element} resistance active.",
                "second": None,
                "third": None,
            })

        # --- Apply resistance via named effect ---
        resistance_pct = self._SCALING.get(tier, 20)

        target.apply_resist_element(element, resistance_pct, 30, source=caster)

        # --- Build messages ---
        if target == caster:
            first_msg = (
                f"|CYou weave a ward of {element} resistance around yourself! "
                f"({resistance_pct}% for 30 seconds)|n"
            )
            second_msg = None
        else:
            first_msg = (
                f"|CYou weave a ward of {element} resistance around {target.key}! "
                f"({resistance_pct}% for 30 seconds)|n"
            )
            second_msg = (
                f"|C{caster.key} weaves a ward of {element} resistance around you! "
                f"({resistance_pct}% for 30 seconds)|n"
            )

        third_msg = (
            f"|C{caster.key} weaves a shimmering ward around "
            f"{'themselves' if target == caster else target.key}.|n"
        )

        return (True, {
            "first": first_msg,
            "second": second_msg,
            "third": third_msg,
        })
