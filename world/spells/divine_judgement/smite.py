"""
Smite — divine judgement spell, available from BASIC mastery.
**Paladin only.**

REACTIVE ONLY — Smite cannot be cast manually via `cast smite`. It
triggers automatically via the execute_attack() pipeline when a paladin
with Smite memorised and toggled on lands a weapon hit. The auto-cast
logic lives in combat/reactive_spells.py.

Players toggle Smite on/off with the `smite` command. While on, every
successful weapon hit adds bonus radiant damage and costs mana. When
mana runs out, Smite stops firing automatically.

Scaling (bonus radiant dice and mana cost per hit):
    BASIC(1):   1d6 radiant, 3 mana
    SKILLED(2): 2d6 radiant, 5 mana
    EXPERT(3):  3d6 radiant, 7 mana
    MASTER(4):  4d6 radiant, 9 mana
    GM(5):      5d6 radiant, 12 mana

Cooldown: 0 (per-hit, throttled by mana cost).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Smite(Spell):
    key = "smite"
    aliases = ["sm"]
    name = "Smite"
    school = skills.DIVINE_JUDGEMENT
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "self"
    cooldown = 0
    description = (
        "Channels holy radiance through your weapon, adding bonus "
        "radiant damage to every hit."
    )
    mechanics = (
        "Reactive only — triggers automatically on weapon hits.\n"
        "Toggle with the 'smite' command. Requires Smite memorised.\n"
        "Bonus: 1d6 (Basic) to 5d6 (Grandmaster) radiant per hit.\n"
        "Costs mana per hit. Stops when mana runs out.\n"
        "No cooldown."
    )

    # Number of d6 bonus radiant dice per tier
    _SCALING = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}

    def _execute(self, caster, target):
        """Smite is reactive-only — it cannot be cast manually."""
        return (False, {
            "first": (
                "Smite is a reactive spell — it triggers automatically "
                "when you land a weapon hit in combat. Use the |wsmite|n "
                "command to toggle it on or off."
            ),
            "second": None,
            "third": None,
        })
