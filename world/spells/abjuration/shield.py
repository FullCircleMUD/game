"""
Shield — abjuration spell, available from BASIC mastery.

The workhorse defensive spell for mages. Conjures a shimmering barrier
of force that boosts AC for a number of combat rounds.

REACTIVE ONLY — Shield cannot be cast manually via `cast shield`. It
triggers automatically via the at_wielder_about_to_be_hit weapon hook
when a mage with Shield memorised and toggled on is about to be hit by
a non-crit attack. The auto-cast logic lives in combat/reactive_spells.py.

Toggle via ``toggle shield``. Costs mana per trigger.

Mechanic:
    Timed AC buff via EffectsManagerMixin named effect system.
    apply_named_effect handles AC bonus, duration countdown, messaging,
    and cleanup on combat end. No condition flag needed — has_effect("shield")
    provides the anti-stacking check.

Scaling (AC bonus and duration alternate each tier):
    BASIC(1):   +4 AC, 1 round,  3 mana
    SKILLED(2): +4 AC, 2 rounds, 5 mana
    EXPERT(3):  +5 AC, 2 rounds, 7 mana
    MASTER(4):  +5 AC, 3 rounds, 9 mana
    GM(5):      +6 AC, 3 rounds, 12 mana

Cooldown: 0 (duration-limited — can't stack via has_effect anti-stacking,
and re-triggers automatically when the previous shield expires).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Shield(Spell):
    key = "shield"
    aliases = ["sh"]
    name = "Shield"
    school = skills.ABJURATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "self"
    range = "self"
    cooldown = 0
    description = "Conjures a shimmering barrier of force that deflects attacks."
    mechanics = (
        "Reactive only — triggers automatically when you are about to be hit.\n"
        "Requires Shield to be memorised and toggled on (toggle shield).\n"
        "Costs mana per trigger: 3/5/7/9/12 by tier.\n"
        "Basic: +4 AC / 1 round. Skilled: +4 / 2. Expert: +5 / 2.\n"
        "Master: +5 / 3. Grandmaster: +6 / 3.\n"
        "Cannot stack — re-triggers when previous shield expires."
    )

    # (AC bonus, duration in rounds) per tier
    _SCALING = {
        1: (4, 1),   # BASIC
        2: (4, 2),   # SKILLED
        3: (5, 2),   # EXPERT
        4: (5, 3),   # MASTER
        5: (6, 3),   # GRANDMASTER
    }

    def _execute(self, caster, target):
        """Shield is reactive-only — it cannot be cast manually."""
        return (False, {
            "first": (
                "Shield is a reactive spell — it triggers automatically "
                "when you are about to be hit in combat. Memorise it and "
                "use |wtoggle shield|n to turn it on."
            ),
            "second": None,
            "third": None,
        })
