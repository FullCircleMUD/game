"""
Acid Arrow — conjuration spell, available from BASIC mastery.

The workhorse conjuration damage spell. Fires a bolt of acid that
burns and corrodes the target over multiple combat rounds.

Pure DoT — no upfront damage. Each tick deals 1d4+1 acid damage,
same per-tick formula as Magic Missile's per-missile damage. The
number of ticks equals the caster's mastery tier, so total damage
budget matches Magic Missile but is delivered over time.

Scaling:
    BASIC(1):   1d4+1 acid x 1 round,  mana 5
    SKILLED(2): 1d4+1 acid x 2 rounds, mana 8
    EXPERT(3):  1d4+1 acid x 3 rounds, mana 10
    MASTER(4):  1d4+1 acid x 4 rounds, mana 14
    GM(5):      1d4+1 acid x 5 rounds, mana 16

Anti-stacking: new cast replaces existing acid arrow on target.
Cooldown: 0 (spammable workhorse, same as Magic Missile).

Uses AcidDoTScript for per-tick damage (combat-round only).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class AcidArrow(Spell):
    key = "acid_arrow"
    aliases = ["aa"]
    name = "Acid Arrow"
    school = skills.CONJURATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "hostile"
    cooldown = 0
    description = "Fires a bolt of acid that burns on impact and continues to corrode."
    mechanics = (
        "Damage over time — 1d4+1 acid damage per combat round.\n"
        "Duration: 1 round (Basic) to 5 rounds (Grandmaster).\n"
        "Same total damage budget as Magic Missile, delivered over time.\n"
        "New cast replaces existing acid arrow on target.\n"
        "Acid resistance reduces each tick independently.\n"
        "No cooldown — spammable workhorse."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        dot_rounds = tier  # 1 at BASIC, 5 at GM

        # Replace existing acid arrow if any (fresh cast replaces old)
        if target.has_effect("acid_arrow"):
            target.remove_named_effect("acid_arrow")
        existing_scripts = target.scripts.get("acid_dot")
        if existing_scripts:
            existing_scripts[0].delete()

        # Apply named effect as marker (script manages lifecycle)
        target.apply_acid_arrow_dot(dot_rounds)

        # Create the damage-ticking script
        from evennia.utils.create import create_script
        from typeclasses.scripts.acid_dot_script import AcidDoTScript

        script = create_script(
            AcidDoTScript,
            obj=target,
            key="acid_dot",
            autostart=False,
        )
        script.db.remaining_ticks = dot_rounds
        script.db.source_name = caster.key
        script.start()

        s = "s" if dot_rounds > 1 else ""
        return (True, {
            "first": (
                f"|GYou fire a bolt of acid at {target.key}! "
                f"It sears into them, burning and corroding! "
                f"({dot_rounds} round{s} of acid damage)|n"
            ),
            "second": (
                f"|G{caster.key} fires a bolt of acid at you! "
                f"It sears into you, burning and corroding!|n"
            ),
            "third": (
                f"|G{caster.key} fires a bolt of acid at {target.key}! "
                f"It sears into them, burning and corroding!|n"
            ),
        })
