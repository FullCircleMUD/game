"""
Combat utility functions — attack resolution, combat entry, side detection.

execute_attack()  — full attack resolution with all weapon hooks
enter_combat()    — shared entry point for all combat-initiating actions
get_sides()       — ally/enemy detection from a combatant's perspective
"""

import random

from enums.actor_size import ActorSize
from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.unused_for_reference.damage_type import DamageType
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

    Only returns a weapon if the HOLD slot contains a WeaponNFTItem.
    Holdables (shields, torches) are NOT off-hand weapons.

    Returns:
        WeaponNFTItem or None
    """
    if not hasattr(actor, "get_slot"):
        return None
    from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
    held = actor.get_slot("HOLD")
    if held and isinstance(held, WeaponNFTItem):
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

    # Unequip via the character's remove method
    success, _ = target.remove(weapon)
    if not success:
        return (False, "")

    # Mobs/NPCs: drop weapon to room floor. Players: stays in inventory.
    from typeclasses.actors.character import FCMCharacter
    if not isinstance(target, FCMCharacter) and target.location:
        weapon.move_to(target.location, quiet=True)

    return (True, weapon_name)


# ================================================================== #
#  Protect — intercept check
# ================================================================== #

def _check_intercept(target):
    """
    Check if any ally is protecting this target and roll for intercept.

    Scans allies' combat handlers for anyone with protecting == target.id.
    Multiple protectors each roll independently; first success wins.

    Returns the intercepting protector, or None.
    """
    allies, _ = get_sides(target)
    for ally in allies:
        if ally == target or ally.location != target.location:
            continue
        if getattr(ally, "hp", 0) <= 0:
            continue
        handlers = ally.scripts.get("combat_handler")
        if not handlers or handlers[0].protecting != target.id:
            continue
        mastery_dict = ally.db.skill_mastery_levels
        if not mastery_dict:
            continue
        mastery_int = mastery_dict.get("protect", MasteryLevel.UNSKILLED.value)
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

def _check_reach_counters(attacker, target):
    """
    After a hit lands, check if the target's allies can counter-attack
    with reach weapons (spear mastery).

    Each ally with reach_counters_remaining > 0 fires a free attack
    against the attacker. Counter-attacks use _is_riposte=True to
    prevent parry and cascading counters.
    """
    if getattr(attacker, "hp", 0) <= 0:
        return

    allies, _ = get_sides(target)
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
    total_hit = d20 + attacker.effective_hit_bonus + hook_hit_mod + hit_modifier
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

                # --- 3b. Riposte ---
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
        dmg_type = DamageType.BLUDGEONING

        if weapon:
            mastery = weapon.get_wielder_mastery(attacker)
            damage_dice_str = weapon.get_damage_roll(mastery)
            dmg_type = weapon.damage_type

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
        protector = _check_intercept(target)
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

        # --- 9. Apply resistance & deal damage ---
        damage_dealt = target.take_damage(
            damage, damage_type=dmg_type.value, cause="combat",
            killer=attacker,
        )

        # --- 9b. Reactive Smite: bonus radiant damage on weapon hit ---
        if not _is_riposte and target.hp > 0:
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

        # Broadcast hit message
        crit_str = " |y*CRITICAL*|n" if is_crit else ""
        if attacker.location:
            attacker.location.msg_contents(
                f"|r{attacker.key} hits {target.key}{crit_str} "
                f"for {damage_dealt} damage!|n",
                from_obj=attacker,
            )

        # --- 11. Kill hook (notification — die() already called by take_damage) ---
        if target.hp <= 0:
            if weapon:
                weapon.at_kill(attacker, target)
            # Mob-level kill hook (e.g. gnoll rampage)
            if hasattr(attacker, "at_kill"):
                attacker.at_kill(target)

        # --- 11b. Reach counters from target's allies (spear mastery) ---
        if not _is_riposte:
            _check_reach_counters(attacker, target)
    else:
        # --- 12. Miss hooks ---
        if weapon:
            weapon.at_miss(attacker, target)
        if defender_weapon:
            defender_weapon.at_wielder_missed(target, attacker)

        # Broadcast miss message
        if attacker.location:
            attacker.location.msg_contents(
                f"|y{attacker.key} attacks {target.key} but misses!|n",
                from_obj=attacker,
            )

    # --- 13. Post-attack hook (always fires) ---
    if weapon:
        weapon.at_post_attack(attacker, target, hit, damage_dealt)


# ================================================================== #
#  Combat Entry
# ================================================================== #

def enter_combat(combatant, target):
    """
    Shared entry point for all combat-initiating actions.

    Creates combat handlers on combatant, target, and their group members.
    Returns True if combat was successfully initiated, False otherwise.
    """
    room = combatant.location
    if not room:
        combatant.msg("You can't fight here.")
        return False

    if not getattr(room, "allow_combat", False):
        combatant.msg("Combat is not allowed here.")
        return False

    # Create handler on combatant and target
    _get_or_create_handler(combatant)
    _get_or_create_handler(target)

    # If target is a CombatMob, trigger counter-attack against the aggressor.
    # mob_attack() → execute_cmd("attack ...") → queues repeating attack on
    # the mob's handler. Safe to call even if handler already has an action.
    from typeclasses.actors.mob import CombatMob
    if isinstance(target, CombatMob) and getattr(target, "is_alive", False):
        target.mob_attack(combatant)

    # Pull in combatant's group
    if hasattr(combatant, "get_group_leader"):
        leader = combatant.get_group_leader()
        if leader:
            members = [leader] + leader.get_followers(same_room=True)
            for member in members:
                if member.location == room and getattr(member, "hp", 0) > 0:
                    _get_or_create_handler(member)

    # Pull in target's group
    if hasattr(target, "get_group_leader"):
        t_leader = target.get_group_leader()
        if t_leader:
            members = [t_leader] + t_leader.get_followers(same_room=True)
            for member in members:
                if member.location == room and getattr(member, "hp", 0) > 0:
                    _get_or_create_handler(member)

    return True


def _get_or_create_handler(combatant):
    """Create combat handler on combatant if they don't have one."""
    from evennia.utils.create import create_script
    from combat.combat_handler import CombatHandler

    existing = combatant.scripts.get("combat_handler")
    if existing:
        return existing[0]

    handler = create_script(
        CombatHandler,
        obj=combatant,
        key="combat_handler",
        autostart=False,
    )
    handler.start()
    handler.start_combat()
    return handler


# ================================================================== #
#  Side Detection
# ================================================================== #

def get_sides(combatant):
    """
    Returns (allies, enemies) from combatant's perspective.

    In non-PvP rooms: PCs ally with PCs, NPCs ally with NPCs.
    In PvP rooms: everyone is an enemy except the combatant themselves.
    """
    room = combatant.location
    if not room:
        return [], []

    # Everyone in the room who is in combat and alive
    in_combat = [
        obj for obj in room.contents
        if getattr(obj, "hp", None) is not None
        and obj.hp > 0
        and obj.scripts.get("combat_handler")
    ]

    if getattr(room, "allow_pvp", False):
        allies = [combatant]
        enemies = [c for c in in_combat if c != combatant]
    else:
        from typeclasses.actors.character import FCMCharacter
        pcs = [c for c in in_combat if isinstance(c, FCMCharacter)]
        npcs = [c for c in in_combat if c not in pcs]
        if combatant in pcs:
            allies, enemies = pcs, npcs
        else:
            allies, enemies = npcs, pcs

    return allies, enemies
