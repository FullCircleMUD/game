"""
Soul Harvest — necromancy spell, available from EXPERT mastery.

The "Fireball of necromancy" — drains HP from ALL living entities in
the room (including allies), and the caster heals for the TOTAL amount
drained across all targets. The ultimate selfish spell.

Unsafe AoE with self-benefit: your party takes the hit, but YOU get
healed for everything. The party necro better warn people before
casting this one.

Damage scales with mastery tier (big spell scaling: +3d6/tier):
    EXPERT(3):  8d6 cold  (avg 28, mana 28)
    MASTER(4): 11d6 cold  (avg 39, mana 39)
    GM(5):     14d6 cold  (avg 49, mana 49)

Mana costs match Fireball tier-for-tier. Heal = sum of ALL damage
dealt to ALL targets (after resistance). Caster is NOT a target
(they're the one draining, not being drained).

Unlike Fireball, the caster is NOT hit — but allies ARE. This makes
it tactically different: the caster benefits while allies suffer.
Worse than Fireball for allies (no self-damage accountability), but
the caster gets massive healing in return.

Cooldown: uses default tier-based (EXPERT=1).
"""

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell
from world.spells.spell_utils import apply_spell_damage, get_room_all


@register_spell
class SoulHarvest(Spell):
    key = "soul_harvest"
    aliases = ["soh"]
    name = "Soul Harvest"
    school = skills.NECROMANCY
    min_mastery = MasteryLevel.EXPERT
    mana_cost = {3: 28, 4: 39, 5: 49}
    target_type = "none"
    description = "Drains the life from everything in the room, healing yourself."
    mechanics = (
        "Unsafe AoE — drains ALL living entities in the room EXCEPT you.\n"
        "Allies take full damage. You heal for the TOTAL damage dealt.\n"
        "Damage: 8d6 (Expert), 11d6 (Master), 14d6 (Grandmaster) cold.\n"
        "Cold resistance reduces damage (and therefore your healing).\n"
        "Heal cannot exceed your maximum HP."
    )

    # Dice per tier: base 8d6 at EXPERT, +3d6 per tier above
    _DICE = {3: 8, 4: 11, 5: 14}

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        num_dice = self._DICE.get(tier, 8)
        raw_damage = dice.roll(f"{num_dice}d6")

        # Get all living entities EXCEPT caster and undead
        all_targets = [
            e for e in get_room_all(caster)
            if e != caster
            and not e.tags.get("undead", category="creature_type")
        ]
        if not all_targets:
            return (True, {
                "first": "You unleash a wave of necrotic energy but there's nothing to drain!",
                "second": None,
                "third": f"{caster.key} unleashes a wave of dark energy that dissipates harmlessly.",
            })

        # Apply damage to every entity except caster, track total for healing
        total_drained = 0
        damage_results = []
        for entity in all_targets:
            actual = apply_spell_damage(entity, raw_damage, DamageType.COLD)
            total_drained += actual
            damage_results.append((entity, actual))
            entity.msg(
                f"|r{caster.key}'s soul harvest drains you for "
                f"{actual} cold damage!|n"
            )

        # Heal caster for total drained, capped at max HP
        heal_amount = min(total_drained, caster.hp_max - caster.hp)
        caster.hp = min(caster.hp_max, caster.hp + total_drained)

        # Build caster summary
        parts = [f"{e.key} ({d})" for e, d in damage_results]
        target_summary = ", ".join(parts)

        if heal_amount > 0:
            heal_msg = f" You drain |g{heal_amount}|n HP from their life force!"
        else:
            heal_msg = " You are already at full health."

        return (True, {
            "first": (
                f"|rYou unleash a wave of necrotic energy! "
                f"It drains {target_summary}.{heal_msg}|n"
            ),
            "second": None,
            "third": (
                f"|r{caster.key} unleashes a terrible wave of dark energy "
                f"that drains the life from everything nearby!|n"
            ),
        })
