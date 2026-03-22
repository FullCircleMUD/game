"""
Retreat — order the group to withdraw from combat.

STRATEGY skill (warrior, paladin). Group leader command.

Single roll by the leader: d20 + INT mod + CHA mod + mastery bonus vs DC 10.
Success moves the entire group (leader + followers in same room) through the
chosen exit and ends combat for all of them. Failure means nobody moves and
enemies get advantage against the leader.

Compared to flee:
  - Whole group moves together (flee is individual)
  - Uses INT + CHA + mastery (flee uses DEX)
  - Can specify direction (flee is always random)
  - Single coordinated check (flee is per-person)

Usage:
    retreat [direction]    — retreat through specified exit
    retreat               — retreat through random exit
    ret                   — alias
"""

import random

from combat.combat_utils import get_sides
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from .cmd_skill_base import CmdSkillBase

RETREAT_DC = 10


def _get_open_exits(caller):
    """Return exits the caller can traverse (filters closed/locked doors)."""
    room = caller.location
    if not room:
        return []
    return [
        ex for ex in room.exits
        if ex.destination and ex.access(caller, "traverse")
    ]


class CmdRetreat(CmdSkillBase):
    """
    Order the group to retreat from combat.

    Usage:
        retreat [direction]
        ret [direction]

    A strategic withdrawal — the group leader rolls INT + CHA
    + mastery bonus to disengage the group. On success, everyone
    moves through the exit. On failure, nobody moves and enemies
    get advantage against the leader.

    Must be the group leader (or solo) and in combat.
    """

    key = "retreat"
    aliases = ["ret"]
    skill = skills.STRATEGY.value
    help_category = "Group Combat"

    def func(self):
        caller = self.caller

        # ── Mastery check ──
        mastery_dict = caller.db.skill_mastery_levels
        if not mastery_dict:
            return self.mob_func()

        mastery_int = mastery_dict.get(self.skill, MasteryLevel.UNSKILLED.value)
        mastery = MasteryLevel(mastery_int)

        if mastery == MasteryLevel.UNSKILLED:
            caller.msg("You need training in strategy before you can order a retreat.")
            return

        # ── Must be in combat ──
        handlers = caller.scripts.get("combat_handler")
        if not handlers:
            caller.msg("You're not in combat.")
            return

        # ── Must be leader or solo ──
        if caller.following:
            caller.msg("Only the group leader can order a retreat.")
            return

        # ── Determine exit ──
        exits = _get_open_exits(caller)
        if not exits:
            caller.msg("|rYou try to retreat but there's nowhere to go!|n")
            return

        chosen = None
        if self.args and self.args.strip():
            direction = self.args.strip().lower()
            for ex in exits:
                if ex.key.lower() == direction:
                    chosen = ex
                    break
            if not chosen:
                caller.msg(f"You can't retreat '{direction}' — no exit found.")
                return
        else:
            chosen = random.choice(exits)

        direction_name = chosen.key

        # ── Capture enemies before any movement ──
        _, enemies = get_sides(caller)

        # ── Gather group members in combat in same room ──
        group = [caller]
        if hasattr(caller, "get_followers"):
            for follower in caller.get_followers(same_room=True):
                if follower.scripts.get("combat_handler"):
                    group.append(follower)

        # ── Single roll: d20 + INT mod + CHA mod + mastery bonus vs DC ──
        roll = dice.roll("1d20")
        int_mod = caller.get_attribute_bonus(caller.intelligence)
        cha_mod = caller.get_attribute_bonus(caller.charisma)
        total = roll + int_mod + cha_mod + mastery.bonus

        if total >= RETREAT_DC:
            # ── Success — everyone retreats ──
            caller.msg(
                f"|g*RETREAT* You lead the group in an orderly withdrawal {direction_name}!|n "
                f"(Retreat: {roll} + {int_mod + cha_mod + mastery.bonus} = {total} "
                f"vs DC {RETREAT_DC})"
            )
            if caller.location:
                caller.location.msg_contents(
                    f"|y{caller.key} leads the group in an orderly retreat {direction_name}!|n",
                    exclude=[caller],
                )

            # Stop combat for all group members first
            for member in group:
                member_handlers = member.scripts.get("combat_handler")
                if member_handlers:
                    member_handlers[0].stop_combat()

            # Move all group members to the exit
            destination = chosen.destination
            for member in group:
                member.move_to(destination)

            # Check if remaining combatants should end combat
            for enemy in enemies:
                enemy_handlers = enemy.scripts.get("combat_handler")
                if enemy_handlers:
                    enemy_handlers[0]._check_stop_combat()
        else:
            # ── Failure — nobody moves, enemies get advantage on leader ──
            for enemy in enemies:
                enemy_handler = enemy.scripts.get("combat_handler")
                if enemy_handler:
                    enemy_handler[0].set_advantage(caller, rounds=1)

            caller.msg(
                f"|r*RETREAT FAILED* You try to organise a retreat but can't disengage!|n "
                f"(Retreat: {roll} + {int_mod + cha_mod + mastery.bonus} = {total} "
                f"vs DC {RETREAT_DC})"
            )
            if caller.location:
                caller.location.msg_contents(
                    f"|y{caller.key} tries to order a retreat but the group can't disengage!|n",
                    exclude=[caller],
                )

    # ── Mob fallback ──
    def mob_func(self):
        pass

    # Mastery stubs — not used (func overridden)
    def unskilled_func(self):
        pass

    def basic_func(self):
        pass

    def skilled_func(self):
        pass

    def expert_func(self):
        pass

    def master_func(self):
        pass

    def grandmaster_func(self):
        pass
