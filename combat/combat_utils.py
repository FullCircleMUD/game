"""
Combat utility functions — attack resolution, combat entry, side detection.

execute_attack()  — full attack resolution with all weapon hooks
enter_combat()    — shared entry point for all combat-initiating actions
get_sides()       — ally/enemy detection from a combatant's perspective
"""

import random

from combat.height_utils import can_reach_target, get_height_hit_modifier
from enums.actor_size import ActorSize
from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.unused_for_reference.damage_type import DamageType
from rules.damage_descriptors import get_descriptor, get_miss_verb
from utils.dice_roller import dice


# ================================================================== #
#  Protect — intercept chance by mastery
# ================================================================== #

INTERCEPT_CHANCE = {
    MasteryLevel.BASIC: 40,
    MasteryLevel.SKILLED: 50,
    MasteryLevel.EXPERT: 60,
    MasteryLevel.MASTER: 70,
    MasteryLevel.GRANDMASTER: 80,
}


# ================================================================== #
#  Actor Size Helper
# ================================================================== #

def get_actor_size(actor):
    """Get an actor's size as ActorSize enum.
    Checks race.size for PCs, .size for mobs (stored as string)."""
    # PC path: character.race.size (already ActorSize enum)
    race = getattr(actor, "race", None)
    if race and hasattr(race, "size"):
        return race.size
    # Mob path: direct .size attribute (stored as string)
    size = getattr(actor, "size", None)
    if size:
        if isinstance(size, ActorSize):
            return size
        try:
            return ActorSize(size)
        except ValueError:
            return ActorSize.MEDIUM
    return ActorSize.MEDIUM


# ================================================================== #
#  Weapon Lookup
# ================================================================== #

def get_weapon(actor):
    """
    Get actor's effective weapon — wielded weapon or unarmed fallback.

    Returns:
        WeaponNFTItem if wielded, UNARMED singleton if actor has wearslots
        but no weapon, or None for actors without wearslots (animal mobs).
    """
    if hasattr(actor, "get_slot"):
        weapon = actor.get_slot("WIELD")
        if weapon:
            return weapon
        from typeclasses.items.weapons.unarmed_weapon import UNARMED
        return UNARMED
    return None


def get_offhand_weapon(actor):
    """
    Get actor's off-hand weapon from the HOLD slot, if any.

    Only returns a weapon if the HOLD slot contains a weapon object
    (NFT or mob). Holdables (shields, torches) are NOT off-hand weapons.

    Returns:
        Weapon object or None
    """
    if not hasattr(actor, "get_slot"):
        return None
    from typeclasses.items.weapons.weapon_mechanics_mixin import WeaponMechanicsMixin
    held = actor.get_slot("HOLD")
    if held and isinstance(held, WeaponMechanicsMixin):
        return held
    return None


# ================================================================== #
#  Disarm — force-drop wielded weapon
# ================================================================== #

def force_drop_weapon(target, weapon=None):
    """
    Force a target to drop/unequip their wielded weapon.

    Mobs/NPCs: weapon drops to the room floor (can be picked up).
    Players (FCMCharacter): weapon unequipped to inventory (no item loss).

    Args:
        target: the actor being disarmed
        weapon: optional — the weapon to drop. If None, looks up wielded weapon.

    Returns:
        (True, weapon_key) if weapon was dropped/unequipped.
        (False, "") if target has no disarmable weapon.
    """
    if weapon is None:
        weapon = get_weapon(target)
    if not weapon or not hasattr(weapon, "weapon_type_key"):
        return (False, "")

    # UnarmedWeapon is a singleton — can't be dropped
    from typeclasses.items.weapons.unarmed_weapon import UnarmedWeapon
    if isinstance(weapon, UnarmedWeapon):
        return (False, "")

    weapon_name = weapon.key

    # Unequip via the character's remove method — weapon stays in inventory.
    success, _ = target.remove(weapon)
    if not success:
        return (False, "")

    return (True, weapon_name)


# ================================================================== #
#  Protect — intercept check
# ================================================================== #

def _check_intercept(target, target_allies=None):
    """
    Check if any ally is protecting this target and roll for intercept.

    Scans allies' combat handlers for anyone with protecting == target.id.
    Multiple protectors each roll independently; first success wins.

    Args:
        target: the defender being attacked
        target_allies: pre-computed allies list (avoids redundant get_sides call)

    Returns the intercepting protector, or None.
    """
    allies = target_allies if target_allies is not None else get_sides(target)[0]
    for ally in allies:
        if ally == target or ally.location != target.location:
            continue
        if getattr(ally, "hp", 0) <= 0:
            continue
        handlers = ally.scripts.get("combat_handler")
        if not handlers or handlers[0].protecting != target.id:
            continue
        mastery_int = ally.get_skill_mastery("protect") if hasattr(ally, 'get_skill_mastery') else 0
        mastery = MasteryLevel(mastery_int)
        if mastery == MasteryLevel.UNSKILLED:
            continue
        chance = INTERCEPT_CHANCE.get(mastery, 0)
        if random.randint(1, 100) <= chance:
            return ally
    return None


# ================================================================== #
#  Reach Counters — spear allies counter-attack when target is hit
# ================================================================== #

def _check_reach_counters(attacker, target, target_allies=None):
    """
    After a hit lands, check if the target's allies can counter-attack
    with reach weapons (spear mastery).

    Each ally with reach_counters_remaining > 0 fires a free attack
    against the attacker. Counter-attacks use _is_riposte=True to
    prevent parry and cascading counters.

    Args:
        attacker: the attacker who just landed a hit
        target: the defender who was hit
        target_allies: pre-computed allies list (avoids redundant get_sides call)
    """
    if getattr(attacker, "hp", 0) <= 0:
        return

    allies = target_allies if target_allies is not None else get_sides(target)[0]
    for ally in allies:
        if ally == target or ally.location != target.location:
            continue
        if getattr(ally, "hp", 0) <= 0:
            continue
        # Skip action-denied allies
        if (hasattr(ally, "has_effect") and (
                ally.has_effect("stunned") or ally.has_effect("prone")
                or ally.has_effect("paralysed") or ally.has_effect("entangled"))):
            continue
        handlers = ally.scripts.get("combat_handler")
        if not handlers or handlers[0].reach_counters_remaining <= 0:
            continue

        # Fire reach counter-attack
        handlers[0].reach_counters_remaining -= 1
        ally.msg(
            f"|g*REACH COUNTER* You thrust at {attacker.key} "
            f"as they strike {target.key}!|n"
        )
        attacker.msg(
            f"|y*REACH COUNTER* {ally.key} strikes at you "
            f"from behind {target.key}!|n"
        )
        if attacker.location:
            attacker.location.msg_contents(
                f"|y*REACH COUNTER* {ally.key} strikes at {attacker.key} "
                f"from behind {target.key}!|n",
                exclude=[ally, attacker],
            )
        execute_attack(ally, attacker, _is_riposte=True)

        # Stop if attacker died from counter
        if getattr(attacker, "hp", 0) <= 0:
            return


# ================================================================== #
#  Attack Resolution
# ================================================================== #

def execute_attack(attacker, target, _is_riposte=False,
                   weapon_override=None, hit_modifier=0):
    """
    Full attack resolution with weapon hooks, parry, durability, and crit immunity.

    Args:
        attacker: the attacking combatant
        target: the defending combatant
        _is_riposte: if True, this is a riposte counter-attack — skip parry check
                      to prevent infinite recursion (ripostes cannot be parried)
        weapon_override: if set, use this weapon for damage/hooks instead of
                         the main hand (used for off-hand dual-wield attacks)
        hit_modifier: additional hit modifier (e.g. off-hand penalty)

    Flow:
        1. Pre-attack hooks (weapon mods)
        2. d20 roll (advantage/disadvantage)
        3. Parry check (defender may block melee attacks; skipped for ripostes)
        3b. Riposte (defender counter-attacks after successful parry, if weapon allows)
        3c. About-to-be-hit hook (reactive defence, e.g. Shield spell; crits bypass)
        4. Hit determination
        5. Damage roll + hit hooks
        6. CRIT_IMMUNE check (helmet may downgrade crit)
        7. Crit hooks (if not downgraded)
        8. Defender hit hooks
        9. Apply resistance & damage
       10. Durability loss (weapon, armor, helmet)
       11. Kill check
       12. Miss hooks (if missed)
       13. Post-attack hook (always fires)
    """
    if not attacker or not target:
        return
    if getattr(attacker, "hp", 0) <= 0 or getattr(target, "hp", 0) <= 0:
        return
    if attacker.location != target.location:
        return

    weapon = weapon_override if weapon_override else get_weapon(attacker)
    defender_weapon = get_weapon(target)

    # Break invisibility on auto-attack (mid-combat edge case)
    if (hasattr(attacker, "break_invisibility")
            and attacker.has_condition(Condition.INVISIBLE)):
        attacker.break_invisibility()
        handler = attacker.scripts.get("combat_handler")
        if handler:
            handler[0].set_advantage(target, rounds=1)

    # Sanctuary: target is protected — attack blocked entirely
    if (hasattr(target, "has_condition")
            and target.has_condition(Condition.SANCTUARY)):
        attacker.msg(f"|W{target.key} is protected by a divine sanctuary!|n")
        return

    # Sanctuary: attacker loses it on offensive action (attack still proceeds)
    if (hasattr(attacker, "has_condition")
            and attacker.has_condition(Condition.SANCTUARY)):
        attacker.break_sanctuary()
        attacker.msg("|WYour sanctuary fades as you take an offensive action!|n")
        if attacker.location:
            attacker.location.msg_contents(
                f"|W{attacker.key}'s divine sanctuary fades!|n",
                exclude=[attacker],
            )

    # --- Height reachability check (height can change mid-combat) ---
    if not can_reach_target(attacker, target, weapon):
        attacker.msg(
            f"|yYou can't reach {target.key} — "
            f"they are at a different height.|n"
        )
        return

    # --- 1. Pre-attack hooks ---
    hook_hit_mod = weapon.at_pre_attack(attacker, target) if weapon else 0
    hook_ac_mod = defender_weapon.at_pre_defend(target, attacker) if defender_weapon else 0

    # --- 2. Roll to hit ---
    advantage = False
    disadvantage = False
    handler = attacker.scripts.get("combat_handler")
    if handler:
        advantage = handler[0].has_advantage(target)
        disadvantage = handler[0].has_disadvantage(target)
        # Consume one round of advantage/disadvantage
        if advantage:
            handler[0].consume_advantage(target)
        if disadvantage:
            handler[0].consume_disadvantage(target)

    # --- Bonus attack dice (stab, etc.) — consume on this attack ---
    bonus_dice_str = ""
    if handler:
        bonus_dice_str = handler[0].bonus_attack_dice
        if bonus_dice_str:
            handler[0].bonus_attack_dice = ""

    d20 = dice.roll_with_advantage_or_disadvantage(
        advantage=advantage, disadvantage=disadvantage,
    )
    is_crit = d20 >= attacker.effective_crit_threshold

    # Attacker's total hit (self-contained — inspects own weapon)
    height_mod = get_height_hit_modifier(attacker, target, weapon)
    total_hit = d20 + attacker.effective_hit_bonus + hook_hit_mod + hit_modifier + height_mod
    total_ac = target.effective_ac + hook_ac_mod

    # --- 3. Parry check ---
    # Parry only works against melee weapon attacks (not unarmed/animal/missile).
    # Riposte attacks cannot be parried (prevents infinite recursion).
    from typeclasses.items.weapons.unarmed_weapon import UnarmedWeapon
    parried = False
    if (weapon and defender_weapon and not _is_riposte
            and not isinstance(weapon, UnarmedWeapon)):
        defender_handler = target.scripts.get("combat_handler")
        if defender_handler and defender_handler[0].parries_remaining > 0:
            # Roll parry: d20 + DEX mod + mastery hit bonus
            parry_adv = defender_handler[0].parry_advantage
            # Disadvantage against attacker cancels parry advantage
            parry_disadv = defender_handler[0].has_disadvantage(attacker) if parry_adv else False
            parry_d20 = dice.roll_with_advantage_or_disadvantage(
                advantage=parry_adv, disadvantage=parry_disadv,
            )
            dex_mod = target.get_attribute_bonus(target.dexterity)
            mastery_bonus = defender_weapon.get_mastery_hit_bonus(target)
            parry_roll = parry_d20 + dex_mod + mastery_bonus

            defender_handler[0].parries_remaining -= 1

            if parry_roll > total_hit:
                parried = True
                # Both weapons lose durability
                if hasattr(weapon, "reduce_durability"):
                    weapon.reduce_durability(1)
                if hasattr(defender_weapon, "reduce_durability"):
                    defender_weapon.reduce_durability(1)

                # Three-perspective parry messages
                attacker.msg(
                    f"|y{target.key} parries your attack with {defender_weapon.key}!|n"
                )
                target.msg(
                    f"|gYou parry {attacker.key}'s attack with {defender_weapon.key}!|n"
                )
                if attacker.location:
                    attacker.location.msg_contents(
                        f"|y{target.key} skillfully parries {attacker.key}'s attack!|n",
                        exclude=[attacker, target],
                    )

                # --- 3b. Disarm-on-parry (sai) ---
                if hasattr(defender_weapon, "_try_disarm"):
                    defender_weapon._try_disarm(target, attacker)

                # --- 3c. Riposte ---
                # After a successful parry, if the defender's weapon grants riposte,
                # fire a free counter-attack (which itself cannot be parried).
                if (defender_weapon.has_riposte(target)
                        and getattr(target, "hp", 0) > 0
                        and getattr(attacker, "hp", 0) > 0):
                    target.msg(f"|g*RIPOSTE* You strike back at {attacker.key}!|n")
                    attacker.msg(f"|y*RIPOSTE* {target.key} strikes back!|n")
                    if attacker.location:
                        attacker.location.msg_contents(
                            f"|y*RIPOSTE* {target.key} counter-attacks {attacker.key}!|n",
                            exclude=[attacker, target],
                        )
                    execute_attack(target, attacker, _is_riposte=True)

                # Post-attack hook still fires on parry
                if weapon:
                    weapon.at_post_attack(attacker, target, False, 0)
                return

    # Resolve damage type early — needed by both hit and miss message paths.
    dmg_type = DamageType.BLUDGEONING
    if weapon:
        dmg_type = weapon.damage_type

    hit = (total_hit >= total_ac) or is_crit
    damage_dealt = 0

    # --- 3c. About-to-be-hit hook (reactive defence, e.g. Shield spell) ---
    if hit and not is_crit and defender_weapon:
        ac_mod = defender_weapon.at_wielder_about_to_be_hit(
            target, attacker, total_hit, total_ac,
        )
        if ac_mod:
            total_ac += ac_mod
            hit = total_hit >= total_ac

    if hit:
        # --- 4. Roll damage ---
        mastery = MasteryLevel.UNSKILLED
        # Unarmed fallback — mobs may have damage_dice (e.g. "2d6"), PCs get "1d2"
        damage_dice_str = getattr(attacker, "damage_dice", "1d2")

        if weapon:
            mastery = weapon.get_wielder_mastery(attacker)
            damage_dice_str = weapon.get_damage_roll(mastery)

        damage = dice.roll(damage_dice_str) + attacker.effective_damage_bonus
        damage = max(1, damage)

        # --- 4b. Bonus attack dice (stab, etc.) ---
        if bonus_dice_str:
            damage += dice.roll(bonus_dice_str)

        # --- 5. Hit hook ---
        if weapon:
            damage = weapon.at_hit(attacker, target, damage, dmg_type)

        # --- 6. CRIT_IMMUNE check ---
        crit_was_resisted = False
        if is_crit and hasattr(target, "has_condition") and target.has_condition(Condition.CRIT_IMMUNE):
            is_crit = False
            crit_was_resisted = True
            if attacker.location:
                helmet = target.get_slot("HEAD") if hasattr(target, "get_slot") else None
                helmet_name = helmet.key if helmet else "helmet"
                attacker.location.msg_contents(
                    f"|c{target.key}'s {helmet_name} deflects the critical blow!|n",
                )

        # --- 7. Crit hooks (only if not downgraded) ---
        if is_crit:
            # Double dice on crit (extra roll added to damage)
            damage = dice.roll(damage_dice_str) + damage
            # Double bonus attack dice on crit too
            if bonus_dice_str:
                damage += dice.roll(bonus_dice_str)
            if weapon:
                damage = weapon.at_crit(attacker, target, damage, dmg_type)
            if defender_weapon:
                damage = defender_weapon.at_wielder_receive_crit(
                    target, attacker, damage, dmg_type,
                )

        # --- 8. Defender hit hook ---
        if defender_weapon:
            damage = defender_weapon.at_wielder_hit(
                target, attacker, damage, dmg_type,
            )

        # --- 8b. Protect intercept check ---
        # Pre-compute target's allies once — reused by intercept and reach counters
        _target_allies, _ = get_sides(target)
        protector = _check_intercept(target, target_allies=_target_allies)
        if protector:
            attacker.msg(
                f"|y{protector.key} jumps in front of {target.key}, "
                f"taking the blow!|n"
            )
            target.msg(
                f"|g{protector.key} intercepts the attack, "
                f"protecting you from harm!|n"
            )
            protector.msg(
                f"|r*PROTECT* You throw yourself in front of {target.key}, "
                f"intercepting {attacker.key}'s attack!|n"
            )
            if attacker.location:
                attacker.location.msg_contents(
                    f"|y{protector.key} leaps in front of {target.key}, "
                    f"intercepting {attacker.key}'s attack!|n",
                    exclude=[attacker, target, protector],
                )
            target = protector  # swap for damage, durability, kill check

        # Cache target name before damage — mob may be deleted by die()
        target_key = target.key

        # --- 9. Calculate damage (no side effects yet) ---
        damage_dealt = target.calculate_damage(
            damage, damage_type=dmg_type.value,
        )

        # --- 9b. Reactive Smite: bonus radiant damage on weapon hit ---
        if not _is_riposte:
            from combat.reactive_spells import check_reactive_smite
            smite_bonus = check_reactive_smite(attacker, target)
            if smite_bonus:
                damage_dealt += smite_bonus

        # --- 10. Durability loss ---
        # Attacker's weapon always loses durability on hit
        if weapon and hasattr(weapon, "reduce_durability"):
            weapon.reduce_durability(1)
        # Armor durability: helmet if crit was resisted, body armor otherwise
        if crit_was_resisted:
            helmet = target.get_slot("HEAD") if hasattr(target, "get_slot") else None
            if helmet and hasattr(helmet, "reduce_durability"):
                helmet.reduce_durability(1)
        else:
            body_armor = target.get_slot("BODY") if hasattr(target, "get_slot") else None
            if body_armor and hasattr(body_armor, "reduce_durability"):
                body_armor.reduce_durability(1)

        # Three-perspective hit message BEFORE applying damage (so it
        # appears before death/kill messages triggered by apply_damage)
        crit_prefix = "|y*CRITICAL*|n " if is_crit else ""
        if attacker.location:
            if weapon:
                second_verb, third_verb = get_descriptor(
                    dmg_type, damage_dealt,
                    getattr(target, "effective_hp_max", 1),
                )
                weapon_name = weapon.key
                punct = "!" if second_verb[0].isupper() else "."
                attacker.msg(
                    f"|r{crit_prefix}You {second_verb} {target_key} "
                    f"with your {weapon_name}{punct}|n"
                )
                target.msg(
                    f"|r{crit_prefix}{attacker.key} {third_verb} you "
                    f"with their {weapon_name}{punct}|n"
                )
                attacker.location.msg_contents(
                    f"|r{crit_prefix}{attacker.key} {third_verb} {target_key} "
                    f"with their {weapon_name}{punct}|n",
                    exclude=[attacker, target],
                )
            else:
                # Animal mob natural attack — use attack_message as-is
                atk_msg = getattr(attacker, "attack_message", "attacks")
                attacker.msg(
                    f"|r{crit_prefix}You {atk_msg} {target_key}!|n"
                )
                target.msg(
                    f"|r{crit_prefix}{attacker.key} {atk_msg} you!|n"
                )
                attacker.location.msg_contents(
                    f"|r{crit_prefix}{attacker.key} {atk_msg} {target_key}!|n",
                    exclude=[attacker, target],
                )

        # --- 9c. Apply damage (subtracts HP, triggers die/death) ---
        target.apply_damage(damage_dealt, cause="combat", killer=attacker)

        # Guard: target may have been deleted by die() in apply_damage.
        target_deleted = not getattr(target, "pk", None)
        target_dead = target_deleted or target.hp <= 0

        # --- 11. Kill hook (notification — die() already called by apply_damage) ---
        if target_dead:
            if weapon:
                weapon.at_kill(attacker, target)
            # Mob-level kill hook (e.g. gnoll rampage)
            if hasattr(attacker, "at_kill"):
                attacker.at_kill(target)

        # --- 11b. Reach counters from target's allies (spear mastery) ---
        if not _is_riposte:
            _check_reach_counters(attacker, target, target_allies=_target_allies)
    else:
        # --- 12. Miss hooks ---
        if weapon:
            weapon.at_miss(attacker, target)
        if defender_weapon:
            defender_weapon.at_wielder_missed(target, attacker)

        # Three-perspective miss message
        if attacker.location:
            if weapon:
                second_miss, third_miss = get_miss_verb(dmg_type)
                attacker.msg(
                    f"|yYou {second_miss} at {target.key} but miss.|n"
                )
                target.msg(
                    f"|y{attacker.key} {third_miss} at you but misses.|n"
                )
                attacker.location.msg_contents(
                    f"|y{attacker.key} {third_miss} at {target.key} but misses.|n",
                    exclude=[attacker, target],
                )
            else:
                atk_msg = getattr(attacker, "attack_message", "attacks")
                attacker.msg(
                    f"|yYou {atk_msg} {target.key} but miss.|n"
                )
                target.msg(
                    f"|y{attacker.key} {atk_msg} you but misses.|n"
                )
                attacker.location.msg_contents(
                    f"|y{attacker.key} {atk_msg} {target.key} but misses.|n",
                    exclude=[attacker, target],
                )

    # --- 13. Post-attack hook (always fires) ---
    if weapon:
        weapon.at_post_attack(attacker, target, hit, damage_dealt)


# ================================================================== #
#  Initiative
# ================================================================== #


def roll_initiative(combatant):
    """Roll initiative for combat ordering.

    Returns d20 + effective_initiative + speed modifier.
    Speed comes from weapon (players) or initiative_speed (mobs).
    Higher = acts sooner.
    """
    weapon = get_weapon(combatant)
    if weapon:
        speed_mod = int(getattr(weapon, "speed", 0))
    else:
        # Animal mobs / unarmed NPCs — use mob's initiative_speed attribute
        speed_mod = int(getattr(combatant, "initiative_speed", 0))
    return dice.roll("1d20") + combatant.effective_initiative + speed_mod


def calculate_initiative_delays(initiative_rolls, tick_interval):
    """Convert initiative rolls to staggered ticker delays.

    Args:
        initiative_rolls: {combatant: roll_total} dict
        tick_interval: COMBAT_TICK_INTERVAL in seconds

    Returns:
        {combatant: delay_seconds} dict.  Highest roll gets delay 0,
        others are spread across the first 75% of the tick window.
    """
    if not initiative_rolls:
        return {}

    # Sort by roll descending — highest initiative acts first.
    # Use id() as tiebreaker to avoid comparing incomparable objects.
    sorted_combatants = sorted(
        initiative_rolls.keys(),
        key=lambda c: (initiative_rolls[c], id(c)),
        reverse=True,
    )

    total = len(sorted_combatants)
    max_delay = tick_interval * 0.75

    delays = {}
    for rank, combatant in enumerate(sorted_combatants):
        if total <= 1:
            delays[combatant] = 0
        else:
            delays[combatant] = rank * max_delay / (total - 1)
    return delays


# ================================================================== #
#  Combat Entry
# ================================================================== #

def enter_combat(combatant, target, instigator=None, instigator_advantage=False):
    """
    Shared entry point for all combat-initiating actions.

    Creates combat handlers on combatant, target, and their group members.
    Assigns combat sides dynamically: combatant and target are placed on
    opposite sides, group members inherit their leader's side.

    Args:
        combatant: the character initiating the action
        target: the target of the action
        instigator: if set, this character gets one free attack before
            tickers start.  Pass None for commands that already perform
            their own opening action (stab, bash, pummel).
        instigator_advantage: if True, instigator gets 1 round of
            advantage against target on the free attack (e.g. from stealth).

    Returns True if combat was successfully initiated, False otherwise.
    """
    room = combatant.location
    if not room:
        combatant.msg("You can't fight here.")
        return False

    if not getattr(room, "allow_combat", False):
        combatant.msg("Combat is not allowed here.")
        return False

    # ── Determine sides ──────────────────────────────────────────────
    # Check existing sides first (from active handlers)
    combatant_side = _get_combat_side(combatant)
    target_side = _get_combat_side(target)

    # Fill in from group membership
    if not combatant_side:
        combatant_side = _determine_side_from_group(combatant, room)
    if not target_side:
        target_side = _determine_side_from_group(target, room)

    # Assign defaults based on what's known
    if combatant_side and not target_side:
        target_side = _opposite_side(combatant_side)
    elif target_side and not combatant_side:
        combatant_side = _opposite_side(target_side)
    elif not combatant_side and not target_side:
        combatant_side = 1
        target_side = 2

    # If both ended up on the same side, flip the newcomer
    if target_side == combatant_side:
        # Prefer flipping whoever doesn't already have a handler
        if not _get_combat_side(combatant):
            combatant_side = _opposite_side(target_side)
        else:
            target_side = _opposite_side(combatant_side)

    # ── Create handlers with sides ───────────────────────────────────
    new_combatants = []

    handler, is_new = _get_or_create_handler(combatant, combat_side=combatant_side)
    if is_new:
        new_combatants.append(combatant)

    handler, is_new = _get_or_create_handler(target, combat_side=target_side)
    if is_new:
        new_combatants.append(target)

    # If target has combat capability (CombatMixin), trigger counter-attack.
    if hasattr(target, "initiate_attack") and getattr(target, "is_alive", False):
        target.initiate_attack(combatant)

    # Pull in combatant's group — inherit combatant's side
    if hasattr(combatant, "get_group_leader"):
        leader = combatant.get_group_leader()
        if leader:
            members = [leader] + leader.get_followers(same_room=True)
            for member in members:
                if member.location == room and getattr(member, "hp", 0) > 0:
                    _, is_new = _get_or_create_handler(
                        member, combat_side=combatant_side,
                    )
                    if is_new:
                        new_combatants.append(member)

    # Pull in target's group — inherit target's side
    if hasattr(target, "get_group_leader"):
        t_leader = target.get_group_leader()
        if t_leader:
            members = [t_leader] + t_leader.get_followers(same_room=True)
            for member in members:
                if member.location == room and getattr(member, "hp", 0) > 0:
                    _, is_new = _get_or_create_handler(
                        member, combat_side=target_side,
                    )
                    if is_new:
                        new_combatants.append(member)

    # --- Free instigator attack ---
    if instigator and getattr(target, "hp", 0) > 0:
        handler = instigator.scripts.get("combat_handler")
        if handler:
            if instigator_advantage:
                handler[0].set_advantage(target, rounds=1)
            execute_attack(instigator, target)

    # --- Roll initiative for all new combatants ---
    from django.conf import settings as django_settings
    tick_interval = getattr(django_settings, "COMBAT_TICK_INTERVAL", 4.0)

    initiative_rolls = {}
    for obj in new_combatants:
        # Guard: target may have been killed and deleted by the free attack above
        if not getattr(obj, "pk", None):
            continue
        handlers = obj.scripts.get("combat_handler")
        if handlers:
            init_roll = roll_initiative(obj)
            handlers[0].ndb.initiative_roll = init_roll
            initiative_rolls[obj] = init_roll

    delays = calculate_initiative_delays(initiative_rolls, tick_interval)

    # Store delays on handlers so commands that override queue_action
    # (stab, bash, pummel) can read their initiative delay.
    for obj, delay in delays.items():
        if not getattr(obj, "pk", None):
            continue
        handlers = obj.scripts.get("combat_handler")
        if handlers:
            handlers[0].ndb.initiative_delay = delay

    # --- Start tickers with initiative delays ---
    # Must happen after all handlers exist so get_sides() can see everyone.
    all_in_combat = [
        obj for obj in room.contents
        if getattr(obj, "hp", None) is not None
        and obj.hp > 0
        and obj.scripts.get("combat_handler")
    ]

    tick_dt = tick_interval  # reuse from above

    for obj in all_in_combat:
        handlers = obj.scripts.get("combat_handler")
        if not handlers:
            continue
        handler = handlers[0]
        delay = delays.get(obj, 0)

        if obj == combatant and target:
            # Combatant explicitly targets the specified target rather than
            # relying on get_sides() (which may not work in PvP or PC-vs-PC).
            if not (handler.action_dict and handler.action_dict.get("key") == "attack"):
                handler.queue_action({
                    "key": "attack",
                    "target": target,
                    "dt": tick_dt,
                    "repeat": True,
                    "initial_delay": delay,
                })
        else:
            handler.auto_attack_first_enemy(initiative_delay=delay)

    return True


def _get_or_create_handler(combatant, combat_side=0):
    """Create combat handler on combatant if they don't have one.

    Args:
        combatant: the actor entering combat.
        combat_side: int (1 or 2) — which side this combatant is on.
            If 0 and a handler already exists, the existing side is kept.

    Returns:
        (handler, is_new) tuple.  is_new=True if a handler was just created.
    """
    from evennia.utils.create import create_script
    from combat.combat_handler import CombatHandler

    existing = combatant.scripts.get("combat_handler")
    if existing:
        handler = existing[0]
        # Update side if explicitly provided and handler had no side yet
        if combat_side and handler.combat_side == 0:
            handler.combat_side = combat_side
        return handler, False

    handler = create_script(
        CombatHandler,
        obj=combatant,
        key="combat_handler",
        autostart=False,
    )
    handler.combat_side = combat_side
    handler.start()
    handler.start_combat()
    return handler, True


# ================================================================== #
#  Side Detection
# ================================================================== #

def _opposite_side(side):
    """Return the opposing side number. Side 1 ↔ Side 2."""
    return 2 if side == 1 else 1


def _get_combat_side(obj):
    """Read combat_side from an object's combat handler. Returns 0 if none."""
    handlers = obj.scripts.get("combat_handler")
    if handlers:
        return handlers[0].combat_side
    return 0


def _determine_side_from_group(actor, room):
    """Check if any of actor's group members are already in combat in this room.

    Returns their combat_side if found, 0 otherwise.
    """
    if not hasattr(actor, "get_group_leader"):
        return 0
    leader = actor.get_group_leader()
    if not leader:
        return 0
    # Check leader first
    if leader != actor and leader.location == room:
        side = _get_combat_side(leader)
        if side:
            return side
    # Check all followers
    followers = leader.get_followers(same_room=True)
    for member in followers:
        if member != actor and member.location == room:
            side = _get_combat_side(member)
            if side:
                return side
    return 0


def get_sides(combatant):
    """
    Returns (allies, enemies) from combatant's perspective.

    Single-pass implementation via the targeting library's
    ``bucket_contents`` primitive. A local ``classify`` closure
    reads each candidate's ``combat_handler`` exactly once per
    object and uses the already-fetched handler reference for both
    the in-combat existence check and the ``combat_side`` read —
    eliminating the double script-handler lookup that the previous
    three-loop implementation did in its enemy comprehension.

    Loops: 1 (bucket_contents walks room.contents once, and classify
    runs inline per object as the filter and dispatch). Down from 3
    loops in the pre-rewrite implementation and 2 loops in the
    walk_contents + bucket loop intermediate.

    Script-handler lookups: R + C (one hp check per room object via
    p_living, one script.get per living object inside classify).
    Down from R + 3C in the pre-rewrite implementation.

    Sides are assigned dynamically at combat entry time based on
    who attacked who and group membership. Each combatant's handler
    stores a combat_side (1 or 2).

    In PvP rooms: everyone is an enemy except the combatant themselves.
    """
    from utils.targeting.helpers import bucket_contents
    from utils.targeting.predicates import p_living

    room = combatant.location
    if not room:
        return [], []

    pvp = getattr(room, "allow_pvp", False)
    my_side = _get_combat_side(combatant) if not pvp else 0

    if not pvp and not my_side:
        # Combatant has no side assigned and no PvP fallback —
        # nothing to return.
        return [], []

    def classify(obj, _caller):
        # Read the combat_handler ONCE and reuse for both the
        # in-combat check and the side read. Previously the
        # enemy comprehension called _get_combat_side twice per
        # object (once for != my_side, once for != 0), doubling
        # the script-handler lookups on that pass. Reading
        # handlers[0].combat_side directly here eliminates the
        # redundancy.
        handlers = obj.scripts.get("combat_handler")
        if not handlers:
            return None
        if pvp:
            # PvP short-circuit: caller is their own ally, everyone
            # else in combat is an enemy. Side values are ignored.
            return "allies" if obj is combatant else "enemies"
        side = handlers[0].combat_side
        if side == my_side:
            return "allies"
        if side != 0:
            return "enemies"
        # Side-zero combatants (handler attached but no side
        # assigned — a weird edge state) fall through both
        # branches and are excluded from both lists, matching
        # the previous implementation.
        return None

    buckets = bucket_contents(combatant, room, classify, p_living)
    return buckets.get("allies", []), buckets.get("enemies", [])
