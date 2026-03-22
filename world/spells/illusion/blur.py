"""
Blur — illusion spell, available from BASIC mastery.

The workhorse illusion defensive spell. Distorts the caster's image,
making them harder to hit. Each combat round, sets 1 disadvantage on
all enemies currently in combat with the caster.

Multi-attackers only lose accuracy on 1 attack per round — subsequent
attacks proceed without disadvantage. This makes Blur proportionally
stronger against single-attackers and weaker against multi-attackers.

Scaling:
    BASIC(1):   3 rounds disadvantage, mana 5
    SKILLED(2): 4 rounds,              mana 8
    EXPERT(3):  5 rounds,              mana 10
    MASTER(4):  6 rounds,              mana 14
    GM(5):      7 rounds,              mana 16

Anti-stacking: new cast replaces existing blur (mana refunded).
Cooldown: 0 (spammable workhorse, same as Magic Missile).
Requires combat — no pre-buffing.

Uses BlurScript for per-round disadvantage application (combat-round only).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Blur(Spell):
    key = "blur"
    aliases = []
    name = "Blur"
    school = skills.ILLUSION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "self"
    cooldown = 0
    description = "Distorts your image, making you harder to hit in combat."
    mechanics = (
        "Self-buff — enemies have disadvantage on 1 attack per round.\n"
        "Duration: 3 rounds (Basic) to 7 rounds (Grandmaster).\n"
        "Same mana costs as Magic Missile.\n"
        "New cast replaces existing blur.\n"
        "Must be in combat. No cooldown."
    )

    # Rounds of disadvantage per tier
    _ROUNDS = {1: 3, 2: 4, 3: 5, 4: 6, 5: 7}

    def _execute(self, caster, target):
        from combat.combat_utils import get_sides

        tier = self.get_caster_tier(caster)
        rounds = self._ROUNDS.get(tier, 3)

        # Must be in combat
        handler = caster.scripts.get("combat_handler")
        if not handler:
            caster.mana += self.mana_cost.get(tier, 0)
            return (False, {
                "first": "You need to be in combat to blur.",
                "second": None,
                "third": None,
            })

        # Anti-stacking: replace existing blur (refresh)
        if caster.has_effect("blurred"):
            caster.remove_named_effect("blurred")
        existing_scripts = caster.scripts.get("blur_effect")
        if existing_scripts:
            existing_scripts[0].delete()

        # Apply named effect as marker (combat_rounds for auto-cleanup)
        caster.apply_blurred(rounds)

        # Set immediate disadvantage on all enemies (no gap before first tick)
        _, enemies = get_sides(caster)
        for enemy in enemies:
            enemy_handler = enemy.scripts.get("combat_handler")
            if enemy_handler:
                enemy_handler[0].set_disadvantage(caster, rounds=1)

        # Create the per-round disadvantage script
        from evennia.utils.create import create_script
        from typeclasses.scripts.blur_script import BlurScript

        script = create_script(
            BlurScript,
            obj=caster,
            key="blur_effect",
            autostart=False,
        )
        script.db.remaining_ticks = rounds
        script.start()

        s = "s" if rounds > 1 else ""
        return (True, {
            "first": (
                f"|CYour image shimmers and distorts! "
                f"Enemies will have a harder time hitting you. "
                f"({rounds} round{s})|n"
            ),
            "second": None,  # self-cast, no second person
            "third": (
                f"|C{caster.key}'s image shimmers and distorts, "
                f"making them harder to hit!|n"
            ),
        })
