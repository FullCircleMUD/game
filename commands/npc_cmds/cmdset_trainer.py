"""
Trainer NPC commands — train skills/weapons and buy recipes.

These commands live on the TrainerNPC object's CmdSet. When a player is in the
same room as a trainer, these commands become available. self.obj is the trainer.

Training flow:
    1. Validate access (enum-driven: class skills, weapon restrictions)
    2. Check trainer mastery > character mastery (can teach)
    3. Check skill points + gold
    4. Check no cooldown from a prior failure with this trainer
    5. Y/N confirmation with cost breakdown and success chance
    6. Deduct gold (non-refundable)
    7. Progress bar with delay
    8. Roll success/failure
    9. Success -> deduct skill points, advance mastery
       Failure -> gold lost, points kept, 1-hour cooldown with this trainer
"""

import time
from random import randint

from evennia import CmdSet, Command
from evennia.utils import delay

from commands.command import FCMCommandMixin
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills, _CLASS_MAPPINGS_LOOKUP
from enums.weapon_type import WeaponType


# ═══════════════════════════════════════════════════════════════════════
#  Configurable constants
# ═══════════════════════════════════════════════════════════════════════

# Gold cost per TARGET mastery level
_TRAINING_GOLD_COST = {
    1: 10,     # BASIC
    2: 25,     # SKILLED
    3: 50,     # EXPERT
    4: 100,    # MASTER
    5: 200,    # GRANDMASTER
}

# Training time in seconds per TARGET mastery level
_TRAINING_TIME = {
    1: 10,     # BASIC
    2: 15,     # SKILLED
    3: 20,     # EXPERT
    4: 25,     # MASTER
    5: 30,     # GRANDMASTER
}

# Success chance (%) based on (trainer mastery - character current mastery)
_SUCCESS_CHANCE = {
    1: 50,     # 1 level higher -> 50%
    2: 75,     # 2 levels higher -> 75%
    3: 90,     # 3 levels higher -> 90%
}
# 4+ levels higher = 100%

# Cooldown on failure (seconds) -- per trainer
_FAILURE_COOLDOWN = 3600  # 1 hour

# Progress bar display
_BAR_WIDTH = 10
_TICK_SECONDS = 5

# CHA discount: 5% per charisma modifier point
_CHA_DISCOUNT_PER_MODIFIER = 0.05


# ═══════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════

def _get_skill_enum(skill_key):
    """Return the skills enum member for a skill value string, or None."""
    for s in skills:
        if s.value == skill_key:
            return s
    return None


def _get_weapon_type_enum(weapon_key):
    """Return the WeaponType enum member for a value string, or None."""
    for wt in WeaponType:
        if wt.value == weapon_key:
            return wt
    return None


def _is_general_skill(skill_enum):
    """True if this skill is available to all classes (general/production)."""
    classes = _CLASS_MAPPINGS_LOOKUP.get(skill_enum, set())
    return classes == {"all"}


def _get_skill_classes(skill_enum):
    """Return the set of class keys that can learn this skill."""
    return _CLASS_MAPPINGS_LOOKUP.get(skill_enum, set())


def _get_current_mastery(character, skill_key, is_general):
    """Get the character's current mastery int for a skill."""
    if is_general:
        return (character.db.general_skill_mastery_levels or {}).get(skill_key, 0)
    else:
        entry = (character.db.class_skill_mastery_levels or {}).get(skill_key)
        if entry is None:
            return 0
        return entry.get("mastery", 0)


def _get_weapon_mastery(character, weapon_key):
    """Get the character's current weapon mastery int."""
    return (character.db.weapon_skill_mastery_levels or {}).get(weapon_key, 0)


def _mastery_name(value):
    """Return the display name for a mastery int value."""
    try:
        return MasteryLevel(value).name
    except ValueError:
        return "???"


def _get_success_chance(mastery_gap):
    """Return success chance (0-100) based on trainer-trainee mastery gap."""
    if mastery_gap <= 0:
        return 0
    if mastery_gap >= 4:
        return 100
    return _SUCCESS_CHANCE.get(mastery_gap, 100)


def _calculate_gold_cost(target_mastery, cha_score):
    """Calculate gold cost with CHA discount/surcharge."""
    import math
    base = _TRAINING_GOLD_COST.get(target_mastery, 50)
    cha_mod = math.floor((cha_score - 10) / 2)
    discount = cha_mod * _CHA_DISCOUNT_PER_MODIFIER
    return max(1, round(base * (1 - discount)))


def _match_in_list(item_list, user_input):
    """
    Match user input against a list of keys.
    Tries exact, then prefix, then substring.
    """
    user_input = user_input.replace(" ", "_").lower()

    if user_input in item_list:
        return user_input

    matches = [s for s in item_list if s.startswith(user_input)]
    if len(matches) == 1:
        return matches[0]

    matches = [
        s for s in item_list
        if user_input in s or user_input in s.replace("_", " ")
    ]
    if len(matches) == 1:
        return matches[0]

    return None


def _check_cooldown(caller, trainer):
    """
    Check if the caller has an active cooldown with this trainer.
    Returns (is_blocked, seconds_remaining).
    Lazily cleans up expired entries.
    """
    cooldowns = caller.db.training_cooldowns
    if not cooldowns:
        return False, 0

    trainer_key = str(trainer.dbref)
    last_failed = cooldowns.get(trainer_key)
    if last_failed is None:
        return False, 0

    elapsed = time.time() - last_failed
    if elapsed >= _FAILURE_COOLDOWN:
        # Expired -- clean up
        del cooldowns[trainer_key]
        caller.db.training_cooldowns = cooldowns
        return False, 0

    remaining = _FAILURE_COOLDOWN - elapsed
    return True, remaining


def _set_cooldown(caller, trainer):
    """Record a failed training attempt timestamp for cooldown."""
    cooldowns = caller.db.training_cooldowns or {}
    cooldowns[str(trainer.dbref)] = time.time()
    caller.db.training_cooldowns = cooldowns


def _format_time(seconds):
    """Format seconds as 'Xm Ys' or 'Xs'."""
    if seconds >= 60:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s" if secs else f"{mins}m"
    return f"{int(seconds)}s"


# ═══════════════════════════════════════════════════════════════════════
#  CmdTrain
# ═══════════════════════════════════════════════════════════════════════

class CmdTrain(FCMCommandMixin, Command):
    """
    Train skills at a trainer NPC.

    Usage:
        train                -- list available skills, weapons, and costs
        train <skill>        -- train a general or class skill
        train weapon <name>  -- train a weapon skill

    Training costs gold (adjusted by your Charisma) and skill points.
    Success depends on the trainer's mastery vs your current level.
    On failure, gold is lost but skill points are kept.
    """

    key = "train"
    aliases = ["tr"]
    locks = "cmd:all()"
    help_category = "Guild"

    def func(self):
        caller = self.caller
        trainer = self.obj
        args = self.args.strip().lower()

        if trainer.location != caller.location:
            caller.msg("There is no trainer here.")
            return

        if caller.ndb.is_processing:
            caller.msg(
                "You are already busy. Wait until your current task finishes."
            )
            return

        if not args:
            self._show_trainable(caller, trainer)
            return

        if args.startswith("weapon "):
            weapon_input = args[7:].strip()
            yield from self._train_weapon(caller, trainer, weapon_input)
            return

        # Try skill first, fall through to weapon if no match
        skill_key = _match_in_list(trainer.trainable_skills, args)
        if skill_key:
            yield from self._train_skill(caller, trainer, args)
        else:
            weapon_key = _match_in_list(trainer.trainable_weapons or [], args)
            if weapon_key:
                yield from self._train_weapon(caller, trainer, args)
            else:
                caller.msg(
                    f"'{args}' is not available at this trainer. "
                    f"Type |wtrain|n to see available skills."
                )

    # ── Listing ──

    def _show_trainable(self, caller, trainer):
        """Display all trainable skills and weapons with costs and success chances."""
        lines = []
        cha_score = getattr(caller, "charisma", 10)

        # ── Skills ──
        if trainer.trainable_skills:
            lines.append("|w=== Trainable Skills ===|n")
            lines.append(
                f"{'Skill':<20} {'Type':<9} {'Current':<13} "
                f"{'Next':<13} {'Pts':<6} {'Gold':<7} {'Success':<9} {'Status'}"
            )
            lines.append("-" * 95)

            for skill_key in trainer.trainable_skills:
                line = self._format_skill_line(
                    caller, trainer, skill_key, cha_score
                )
                if line:
                    lines.append(line)

        # ── Weapons ──
        if trainer.trainable_weapons:
            lines.append("")
            lines.append("|w=== Trainable Weapons ===|n")
            lines.append(
                f"{'Weapon':<20} {'Current':<13} "
                f"{'Next':<13} {'Pts':<6} {'Gold':<7} {'Success':<9} {'Status'}"
            )
            lines.append("-" * 88)

            for weapon_key in trainer.trainable_weapons:
                line = self._format_weapon_line(
                    caller, trainer, weapon_key, cha_score
                )
                if line:
                    lines.append(line)

        # ── Recipes ──
        if trainer.recipes_for_sale:
            lines.append("")
            lines.append("|w=== Recipes for Sale ===|n")
            lines.append("Use |wbuy recipe <name>|n to purchase.")
            for recipe_key, gold_cost in trainer.recipes_for_sale.items():
                display_name = recipe_key.replace("_", " ").title()
                lines.append(f"  {display_name:<30} {gold_cost} gold")

        if not lines:
            caller.msg("This trainer has nothing to teach right now.")
            return

        caller.msg("\n".join(lines))

    def _format_skill_line(self, caller, trainer, skill_key, cha_score):
        """Format one skill line for the training listing."""
        skill_enum = _get_skill_enum(skill_key)
        if skill_enum is None:
            return None

        is_general = _is_general_skill(skill_enum)
        current = _get_current_mastery(caller, skill_key, is_general)
        trainer_mastery = trainer.trainer_masteries.get(skill_key, 1)

        if is_general:
            pool_name = "General"
            pool_available = caller.general_skill_pts_available
            accessible = True
        else:
            pool_name = (trainer.trainer_class or "Class").capitalize()
            class_data = (caller.db.classes or {}).get(
                trainer.trainer_class, {}
            )
            pool_available = class_data.get("skill_pts_available", 0)
            accessible = trainer.trainer_class in (caller.db.classes or {})

        current_name = _mastery_name(current)

        if current >= MasteryLevel.GRANDMASTER.value:
            return (
                f"{skill_key:<20} {pool_name:<9} {current_name:<13} "
                f"{'MAXED':<13} {'-':<6} {'-':<7} {'-':<9} |gMaxed|n"
            )

        target = current + 1
        next_name = _mastery_name(target)
        pts_cost = MasteryLevel(target).training_points_required
        gold_cost = _calculate_gold_cost(target, cha_score)
        mastery_gap = trainer_mastery - current
        success = _get_success_chance(mastery_gap)

        if not accessible:
            status = f"|r(no {pool_name.lower()} class)|n"
        elif mastery_gap <= 0:
            status = "|r(trainer can't teach)|n"
        else:
            is_blocked, remaining = _check_cooldown(caller, trainer)
            if is_blocked:
                status = f"|y(cooldown {_format_time(remaining)})|n"
            elif pool_available < pts_cost:
                status = f"|y({pool_available} pts avail)|n"
            else:
                status = f"|g({pool_available} pts avail)|n"

        return (
            f"{skill_key:<20} {pool_name:<9} {current_name:<13} "
            f"{next_name:<13} {pts_cost:<6} {gold_cost:<7} "
            f"{success}%{'':<7} {status}"
        )

    def _format_weapon_line(self, caller, trainer, weapon_key, cha_score):
        """Format one weapon line for the training listing."""
        weapon_enum = _get_weapon_type_enum(weapon_key)
        current = _get_weapon_mastery(caller, weapon_key)
        trainer_mastery = trainer.trainer_masteries.get(weapon_key, 1)

        # Enum validation: character must have at least one class that
        # can train this weapon
        accessible = True
        if weapon_enum:
            weapon_classes = weapon_enum.classes
            char_classes = set((caller.db.classes or {}).keys())
            accessible = bool(char_classes & weapon_classes)

        current_name = _mastery_name(current)
        display_name = weapon_key.replace("_", " ")

        if current >= MasteryLevel.GRANDMASTER.value:
            return (
                f"{display_name:<20} {current_name:<13} "
                f"{'MAXED':<13} {'-':<6} {'-':<7} {'-':<9} |gMaxed|n"
            )

        target = current + 1
        next_name = _mastery_name(target)
        pts_cost = MasteryLevel(target).training_points_required
        gold_cost = _calculate_gold_cost(target, cha_score)
        mastery_gap = trainer_mastery - current
        success = _get_success_chance(mastery_gap)
        pool_available = caller.weapon_skill_pts_available

        if not accessible:
            status = "|r(no qualifying class)|n"
        elif mastery_gap <= 0:
            status = "|r(trainer can't teach)|n"
        else:
            is_blocked, remaining = _check_cooldown(caller, trainer)
            if is_blocked:
                status = f"|y(cooldown {_format_time(remaining)})|n"
            elif pool_available < pts_cost:
                status = f"|y({pool_available} pts avail)|n"
            else:
                status = f"|g({pool_available} pts avail)|n"

        return (
            f"{display_name:<20} {current_name:<13} "
            f"{next_name:<13} {pts_cost:<6} {gold_cost:<7} "
            f"{success}%{'':<7} {status}"
        )

    # ── Skill Training ──

    def _train_skill(self, caller, trainer, skill_input):
        """Train a general or class skill."""
        skill_key = _match_in_list(trainer.trainable_skills, skill_input)
        if skill_key is None:
            caller.msg(
                f"'{skill_input}' is not available at this trainer. "
                f"Type |wtrain|n to see available skills."
            )
            return

        skill_enum = _get_skill_enum(skill_key)
        if skill_enum is None:
            caller.msg("Unknown skill.")
            return

        is_general = _is_general_skill(skill_enum)

        # ── Enum-driven access validation ──
        if not is_general:
            skill_classes = _get_skill_classes(skill_enum)
            # Character must have the trainer's class
            if trainer.trainer_class not in (caller.db.classes or {}):
                caller.msg(
                    f"You are not a "
                    f"{(trainer.trainer_class or 'unknown').capitalize()}. "
                    f"You cannot train class skills here."
                )
                return
            # Sanity: skill must be available to the trainer's class
            if trainer.trainer_class not in skill_classes:
                caller.msg(
                    f"{skill_key} is not a "
                    f"{(trainer.trainer_class or 'unknown').capitalize()} "
                    f"skill."
                )
                return

        # ── Current mastery and cap check ──
        current = _get_current_mastery(caller, skill_key, is_general)
        if current >= MasteryLevel.GRANDMASTER.value:
            caller.msg(
                f"You have already achieved {_mastery_name(current)} "
                f"mastery in {skill_key}. There is nothing more to learn."
            )
            return

        target = current + 1

        # ── Trainer mastery check ──
        trainer_mastery = trainer.trainer_masteries.get(skill_key, 1)
        mastery_gap = trainer_mastery - current
        if mastery_gap <= 0:
            caller.msg(
                f"This trainer is not skilled enough in {skill_key} "
                f"to teach you further. Find a more experienced trainer."
            )
            return

        # ── Skill points check ──
        pts_cost = MasteryLevel(target).training_points_required
        if is_general:
            pool_available = caller.general_skill_pts_available
            pool_name = "general skill"
        else:
            class_data = (caller.db.classes or {})[trainer.trainer_class]
            pool_available = class_data.get("skill_pts_available", 0)
            pool_name = f"{trainer.trainer_class} class skill"

        if pool_available < pts_cost:
            caller.msg(
                f"You need {pts_cost} {pool_name} points to advance "
                f"{skill_key} to {_mastery_name(target)}, "
                f"but you only have {pool_available}."
            )
            return

        # ── Gold cost ──
        cha_score = getattr(caller, "charisma", 10)
        gold_cost = _calculate_gold_cost(target, cha_score)

        if not hasattr(caller, "get_gold") or caller.get_gold() < gold_cost:
            caller.msg(
                f"You need {gold_cost} gold to train {skill_key}, "
                f"but you only have "
                f"{caller.get_gold() if hasattr(caller, 'get_gold') else 0}."
            )
            return

        # ── Cooldown check ──
        is_blocked, remaining = _check_cooldown(caller, trainer)
        if is_blocked:
            caller.msg(
                f"You cannot train with this trainer for another "
                f"{_format_time(remaining)}."
            )
            return

        # ── Success chance ──
        success_chance = _get_success_chance(mastery_gap)
        training_time = _TRAINING_TIME.get(target, 10)

        # ── Y/N Confirmation ──
        answer = yield (
            f"\n|y--- Train {skill_key} ---|n"
            f"\nAdvance: {_mastery_name(current)} -> {_mastery_name(target)}"
            f"\nSkill points: {pts_cost} {pool_name} points"
            f"\nGold cost: {gold_cost} gold (non-refundable)"
            f"\nSuccess chance: {success_chance}%"
            f"\nTraining time: {training_time} seconds"
            f"\n\nProceed? Y/[N]"
        )

        if answer.lower() not in ("y", "yes"):
            caller.msg("Training cancelled.")
            return

        # ── Re-validate after confirmation ──
        if is_general:
            if caller.general_skill_pts_available < pts_cost:
                caller.msg("You no longer have enough skill points.")
                return
        else:
            class_data = (caller.db.classes or {}).get(
                trainer.trainer_class, {}
            )
            if class_data.get("skill_pts_available", 0) < pts_cost:
                caller.msg("You no longer have enough skill points.")
                return

        if not hasattr(caller, "get_gold") or caller.get_gold() < gold_cost:
            caller.msg("You no longer have enough gold.")
            return

        # ── Deduct gold (non-refundable) ──
        caller.return_gold_to_sink(gold_cost)

        # ── Start training with progress bar ──
        caller.ndb.is_processing = True
        num_ticks = max(1, training_time // _TICK_SECONDS)
        skill_display = skill_key.replace("_", " ")

        caller.msg(f"You begin training {skill_display}...")
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} begins training with {trainer.key}.",
                exclude=[caller],
                from_obj=caller,
            )

        def _tick(step):
            if step < num_ticks:
                filled = _BAR_WIDTH * step // num_ticks
                bar = "#" * filled + "-" * (_BAR_WIDTH - filled)
                caller.msg(f"Training {skill_display}... [{bar}]")
                delay(_TICK_SECONDS, _tick, step + 1)
            else:
                bar = "#" * _BAR_WIDTH
                caller.msg(f"Training {skill_display}... [{bar}] Done!")
                _resolve_skill_training(
                    caller, trainer, skill_key, is_general,
                    current, target, pts_cost, success_chance,
                )
                caller.ndb.is_processing = False

        delay(_TICK_SECONDS, _tick, 1)

    # ── Weapon Training ──

    def _train_weapon(self, caller, trainer, weapon_input):
        """Train a weapon skill."""
        weapon_key = _match_in_list(trainer.trainable_weapons, weapon_input)
        if weapon_key is None:
            caller.msg(
                f"'{weapon_input}' is not available at this trainer. "
                f"Type |wtrain|n to see available weapons."
            )
            return

        # ── Enum-driven access validation ──
        weapon_enum = _get_weapon_type_enum(weapon_key)
        if weapon_enum:
            weapon_classes = weapon_enum.classes
            char_classes = set((caller.db.classes or {}).keys())
            if not (char_classes & weapon_classes):
                allowed = ", ".join(
                    c.capitalize() for c in sorted(weapon_classes)
                )
                caller.msg(
                    f"None of your classes can train "
                    f"{weapon_key.replace('_', ' ')}. "
                    f"Available to: {allowed}."
                )
                return

        # ── Current mastery and cap check ──
        current = _get_weapon_mastery(caller, weapon_key)
        if current >= MasteryLevel.GRANDMASTER.value:
            caller.msg(
                f"You have already achieved {_mastery_name(current)} "
                f"mastery with {weapon_key.replace('_', ' ')}. "
                f"There is nothing more to learn."
            )
            return

        target = current + 1

        # ── Trainer mastery check ──
        trainer_mastery = trainer.trainer_masteries.get(weapon_key, 1)
        mastery_gap = trainer_mastery - current
        if mastery_gap <= 0:
            caller.msg(
                f"This trainer is not skilled enough with "
                f"{weapon_key.replace('_', ' ')} to teach you further. "
                f"Find a more experienced trainer."
            )
            return

        # ── Skill points check ──
        pts_cost = MasteryLevel(target).training_points_required
        pool_available = caller.weapon_skill_pts_available
        if pool_available < pts_cost:
            caller.msg(
                f"You need {pts_cost} weapon skill points to advance "
                f"{weapon_key.replace('_', ' ')} to "
                f"{_mastery_name(target)}, "
                f"but you only have {pool_available}."
            )
            return

        # ── Gold cost ──
        cha_score = getattr(caller, "charisma", 10)
        gold_cost = _calculate_gold_cost(target, cha_score)

        if not hasattr(caller, "get_gold") or caller.get_gold() < gold_cost:
            caller.msg(
                f"You need {gold_cost} gold to train "
                f"{weapon_key.replace('_', ' ')}, "
                f"but you only have "
                f"{caller.get_gold() if hasattr(caller, 'get_gold') else 0}."
            )
            return

        # ── Cooldown check ──
        is_blocked, remaining = _check_cooldown(caller, trainer)
        if is_blocked:
            caller.msg(
                f"You cannot train with this trainer for another "
                f"{_format_time(remaining)}."
            )
            return

        # ── Success chance ──
        success_chance = _get_success_chance(mastery_gap)
        training_time = _TRAINING_TIME.get(target, 10)
        weapon_display = weapon_key.replace("_", " ")

        # ── Y/N Confirmation ──
        answer = yield (
            f"\n|y--- Train {weapon_display} ---|n"
            f"\nAdvance: {_mastery_name(current)} -> {_mastery_name(target)}"
            f"\nSkill points: {pts_cost} weapon skill points"
            f"\nGold cost: {gold_cost} gold (non-refundable)"
            f"\nSuccess chance: {success_chance}%"
            f"\nTraining time: {training_time} seconds"
            f"\n\nProceed? Y/[N]"
        )

        if answer.lower() not in ("y", "yes"):
            caller.msg("Training cancelled.")
            return

        # ── Re-validate after confirmation ──
        if caller.weapon_skill_pts_available < pts_cost:
            caller.msg("You no longer have enough skill points.")
            return

        if not hasattr(caller, "get_gold") or caller.get_gold() < gold_cost:
            caller.msg("You no longer have enough gold.")
            return

        # ── Deduct gold (non-refundable) ──
        caller.return_gold_to_sink(gold_cost)

        # ── Start training with progress bar ──
        caller.ndb.is_processing = True
        num_ticks = max(1, training_time // _TICK_SECONDS)

        caller.msg(f"You begin training {weapon_display}...")
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} begins training with {trainer.key}.",
                exclude=[caller],
                from_obj=caller,
            )

        def _tick(step):
            if step < num_ticks:
                filled = _BAR_WIDTH * step // num_ticks
                bar = "#" * filled + "-" * (_BAR_WIDTH - filled)
                caller.msg(f"Training {weapon_display}... [{bar}]")
                delay(_TICK_SECONDS, _tick, step + 1)
            else:
                bar = "#" * _BAR_WIDTH
                caller.msg(f"Training {weapon_display}... [{bar}] Done!")
                _resolve_weapon_training(
                    caller, trainer, weapon_key,
                    current, target, pts_cost, success_chance,
                )
                caller.ndb.is_processing = False

        delay(_TICK_SECONDS, _tick, 1)


# ═══════════════════════════════════════════════════════════════════════
#  Training resolution (module-level for delayed callback)
# ═══════════════════════════════════════════════════════════════════════

def _resolve_skill_training(
    caller, trainer, skill_key, is_general,
    current, target, pts_cost, success_chance,
):
    """Roll success/failure after progress bar completes."""
    roll = randint(1, 100)

    if roll <= success_chance:
        # ── SUCCESS ──
        if is_general:
            caller.general_skill_pts_available -= pts_cost
        else:
            class_data = (caller.db.classes or {})[trainer.trainer_class]
            class_data["skill_pts_available"] -= pts_cost
            caller.db.classes[trainer.trainer_class] = class_data

        # Advance mastery
        if is_general:
            levels = caller.db.general_skill_mastery_levels or {}
            levels[skill_key] = target
            caller.db.general_skill_mastery_levels = levels
        else:
            levels = caller.db.class_skill_mastery_levels or {}
            entry = levels.get(skill_key)
            if entry is None:
                entry = {
                    "mastery": target,
                    "classes": [
                        (trainer.trainer_class or "").capitalize()
                    ],
                }
            else:
                entry["mastery"] = target
            levels[skill_key] = entry
            caller.db.class_skill_mastery_levels = levels

        caller.msg(
            f"|g*** You have advanced to {_mastery_name(target)} "
            f"mastery in {skill_key}! ***|n"
        )
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} completes training with {trainer.key}.",
                exclude=[caller],
                from_obj=caller,
            )
    else:
        # ── FAILURE ──
        _set_cooldown(caller, trainer)
        caller.msg(
            f"|rTraining failed!|n You were unable to grasp the technique."
            f"\nYour gold has been spent, but your skill points are intact."
            f"\nYou cannot train with {trainer.key} again for 1 hour."
        )


def _resolve_weapon_training(
    caller, trainer, weapon_key,
    current, target, pts_cost, success_chance,
):
    """Roll success/failure for weapon training."""
    roll = randint(1, 100)
    weapon_display = weapon_key.replace("_", " ")

    if roll <= success_chance:
        # ── SUCCESS ──
        caller.weapon_skill_pts_available -= pts_cost
        levels = caller.db.weapon_skill_mastery_levels or {}
        levels[weapon_key] = target
        caller.db.weapon_skill_mastery_levels = levels

        caller.msg(
            f"|g*** You have advanced to {_mastery_name(target)} "
            f"mastery with {weapon_display}! ***|n"
        )
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} completes training with {trainer.key}.",
                exclude=[caller],
                from_obj=caller,
            )
    else:
        # ── FAILURE ──
        _set_cooldown(caller, trainer)
        caller.msg(
            f"|rTraining failed!|n You were unable to master the technique."
            f"\nYour gold has been spent, but your skill points are intact."
            f"\nYou cannot train with {trainer.key} again for 1 hour."
        )


# ═══════════════════════════════════════════════════════════════════════
#  CmdBuyRecipe
# ═══════════════════════════════════════════════════════════════════════

class CmdBuyRecipe(FCMCommandMixin, Command):
    """
    Buy a recipe from a trainer NPC.

    Usage:
        buy recipe              -- list recipes for sale
        buy recipe <name>       -- purchase a recipe (learns it directly)

    Requires gold. The recipe is learned immediately -- no scroll item.
    """

    key = "buy"
    aliases = []
    locks = "cmd:all()"
    help_category = "Guild"

    def func(self):
        caller = self.caller
        trainer = self.obj
        args = self.args.strip().lower()

        if trainer.location != caller.location:
            caller.msg("There is no trainer here.")
            return

        if not args.startswith("recipe"):
            caller.msg("Usage: buy recipe [<name>]")
            return

        recipe_name = args[6:].strip()

        if not trainer.recipes_for_sale:
            caller.msg("This trainer has no recipes for sale.")
            return

        if not recipe_name:
            lines = ["|w=== Recipes for Sale ===|n"]
            for recipe_key, gold_cost in trainer.recipes_for_sale.items():
                display_name = recipe_key.replace("_", " ").title()
                lines.append(f"  {display_name:<30} {gold_cost} gold")
            lines.append("\nUse |wbuy recipe <name>|n to purchase.")
            caller.msg("\n".join(lines))
            return

        recipe_key = _match_in_list(
            list(trainer.recipes_for_sale.keys()), recipe_name
        )
        if recipe_key is None:
            caller.msg(
                f"'{recipe_name}' is not available. "
                f"Type |wbuy recipe|n to see available recipes."
            )
            return

        gold_cost = trainer.recipes_for_sale[recipe_key]

        if not hasattr(caller, "get_gold"):
            caller.msg("You cannot purchase recipes.")
            return

        if caller.get_gold() < gold_cost:
            caller.msg(
                f"You need {gold_cost} gold to buy that recipe, "
                f"but you only have {caller.get_gold()}."
            )
            return

        if hasattr(caller, "knows_recipe") and caller.knows_recipe(recipe_key):
            caller.msg("You already know that recipe.")
            return

        if not hasattr(caller, "learn_recipe"):
            caller.msg("You cannot learn recipes.")
            return

        success, msg = caller.learn_recipe(recipe_key)
        if not success:
            caller.msg(msg)
            return

        # Deduct gold -- returns to the reserve (economy sink)
        caller.return_gold_to_sink(gold_cost)

        caller.msg(
            f"|gYou pay {gold_cost} gold and learn the recipe!|n\n{msg}"
        )


# ═══════════════════════════════════════════════════════════════════════
#  CmdSet
# ═══════════════════════════════════════════════════════════════════════

class TrainerCmdSet(CmdSet):
    """Commands available from a TrainerNPC."""

    key = "TrainerCmdSet"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        self.add(CmdTrain())
        self.add(CmdBuyRecipe())
