"""
Distract — illusion spell, available from BASIC mastery.

Creates an illusory distraction targeting a specific enemy. All allies
of the caster gain advantage against that target for N rounds.

In combat: all allies get set_advantage(target, tier) — 1 round at
BASIC, 5 at GM. Multi-attack targets burn through advantage faster.

Out of combat: grants non-combat advantage to the caster.

Scaling:
    BASIC(1):   1 round advantage,  mana 3
    SKILLED(2): 2 rounds advantage, mana 4
    EXPERT(3):  3 rounds advantage, mana 6
    MASTER(4):  4 rounds advantage, mana 8
    GM(5):      5 rounds advantage, mana 10

No cooldown. Hostile target type (in combat), self-buff (out of combat).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Distract(Spell):
    key = "distract"
    aliases = ["dist"]
    name = "Distract"
    school = skills.ILLUSION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 4, 3: 6, 4: 8, 5: 10}
    target_type = "actor_hostile"
    cooldown = 0
    description = "Creates an illusory distraction, giving allies an opening."
    mechanics = (
        "In combat: all allies gain advantage against the target.\n"
        "Advantage rounds: 1 (Basic) to 5 (GM).\n"
        "Out of combat: grants non-combat advantage to caster.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        rounds = tier  # 1 at BASIC, 5 at GM

        # Check if caster is in combat
        handler = caster.scripts.get("combat_handler")
        if handler:
            return self._distract_in_combat(caster, target, rounds)
        else:
            return self._distract_out_of_combat(caster, target)

    def _distract_in_combat(self, caster, target, rounds):
        """Grant all allies advantage against the target."""
        from combat.combat_utils import get_sides

        allies, _ = get_sides(caster)
        granted = 0

        for ally in allies:
            ally_handler = ally.scripts.get("combat_handler")
            if ally_handler:
                ally_handler[0].set_advantage(target, rounds)
                granted += 1

        s = "s" if rounds != 1 else ""
        ally_str = f"{granted} {'ally' if granted == 1 else 'allies'}"

        return (True, {
            "first": (
                f"|MYou conjure an illusory distraction around {target.key}! "
                f"{ally_str} gain advantage ({rounds} round{s}).|n"
            ),
            "second": (
                f"|M{caster.key} conjures an illusory distraction around you! "
                f"Your enemies seem to find an opening...|n"
            ),
            "third": (
                f"|M{caster.key} conjures an illusory distraction around "
                f"{target.key}!|n"
            ),
        })

    def _distract_out_of_combat(self, caster, target):
        """Grant non-combat advantage to the caster."""
        caster.db.non_combat_advantage = True

        return (True, {
            "first": (
                f"|MYou conjure a brief illusory distraction. "
                f"You feel ready to seize the moment!|n"
            ),
            "second": None,
            "third": (
                f"|M{caster.key} conjures a brief illusory shimmer.|n"
            ),
        })
