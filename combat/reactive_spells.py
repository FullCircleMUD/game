"""
Reactive spell checks — auto-cast spells triggered by combat events.

These utility functions are called from weapon hooks or combat_utils to
check if a combatant has reactive spells memorised/toggled and trigger
them automatically when conditions are met.

Reactive spells are gated by:
    1. Toggle state (player preference) — player must opt in via ``toggle``
    2. Memorisation — spell must be in memorised_spells
    3. Mastery — caster needs sufficient school mastery
    4. Resources — mana (for spells that cost mana per trigger)
"""

from enums.damage_type import DamageType
from utils.dice_roller import dice
from world.spells.spell_utils import apply_spell_damage


def check_reactive_shield(wielder):
    """
    Auto-cast Shield if wielder has it toggled on, memorised, and has mana.

    Called from at_wielder_about_to_be_hit on both WeaponNFTItem and
    UnarmedWeapon. Returns AC bonus applied (0 if not triggered).

    Shield is reactive-only — it cannot be cast manually. It triggers
    automatically when a mage with Shield toggled on is about to be hit
    (non-crit only, since crits bypass the hook entirely).

    Gates: toggle ON + memorised + sufficient mana + mastery >= BASIC.
    Deducts mana on trigger. AC bonus and duration scale with mastery tier.
    """
    # Check toggle (unified player preference)
    if not getattr(wielder, "shield_active", False):
        return 0

    # Check memorised
    if not hasattr(wielder, "is_memorised") or not wielder.is_memorised("shield"):
        return 0

    # Check if Shield is already active (anti-stacking via named effects)
    if wielder.has_effect("shield"):
        return 0

    # Look up spell scaling from the Shield spell class
    from world.spells.registry import get_spell
    shield_spell = get_spell("shield")
    if not shield_spell:
        return 0

    tier = shield_spell.get_caster_tier(wielder)
    if tier < 1:
        return 0  # need at least BASIC mastery

    scaling = shield_spell._SCALING.get(tier)
    if not scaling:
        return 0
    ac_bonus, duration = scaling

    # Check mana
    cost = shield_spell.mana_cost.get(tier, 0)
    if wielder.mana < cost:
        return 0

    # Deduct mana
    wielder.mana -= cost

    # Apply Shield via convenience method (AC bonus + combat round countdown)
    applied = wielder.apply_shield_buff(ac_bonus, duration, mana_cost=cost)

    return ac_bonus if applied else 0


def check_reactive_smite(attacker, target):
    """
    Auto-apply Smite bonus radiant damage after a successful weapon hit.

    Called from execute_attack() in combat_utils after weapon damage is
    dealt. Returns actual radiant damage dealt (0 if not triggered).

    Gates: toggle ON + memorised + sufficient mana + mastery >= BASIC.
    Deducts mana on trigger. Damage applied via apply_spell_damage()
    so radiant resistance/vulnerability is respected.
    """
    # Check toggle (unified player preference)
    if not getattr(attacker, "smite_active", False):
        return 0

    # Check memorised
    if not hasattr(attacker, "is_memorised") or not attacker.is_memorised("smite"):
        return 0

    # Look up spell scaling from the Smite spell class
    from world.spells.registry import get_spell
    smite_spell = get_spell("smite")
    if not smite_spell:
        return 0

    tier = smite_spell.get_caster_tier(attacker)
    if tier < 1:
        return 0

    # Check mana
    cost = smite_spell.mana_cost.get(tier, 0)
    if attacker.mana < cost:
        return 0

    # Roll bonus radiant damage
    num_dice = smite_spell._SCALING.get(tier, 1)
    bonus_damage = dice.roll(f"{num_dice}d6")

    # Apply as radiant damage (respects resistance/vulnerability)
    actual = apply_spell_damage(target, bonus_damage, DamageType.RADIANT, caster=attacker)

    # Deduct mana
    attacker.mana -= cost

    # Messages
    attacker.msg(
        f"|Y*SMITE* Holy radiance surges through your weapon! "
        f"+{actual} radiant damage! ({cost} mana)|n"
    )
    if attacker.location:
        attacker.location.msg_contents(
            f"|Y{attacker.key}'s weapon blazes with holy light!|n",
            exclude=[attacker],
        )

    return actual
