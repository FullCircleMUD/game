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

from combat.combat_utils import RetreatWording, retreat_group
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase


RETREAT_WORDING = RetreatWording(
    to_leader=(
        "|g*RETREAT* You lead the group in an orderly withdrawal {direction}!|n"
    ),
    in_room=(
        "|y$You() $conj(lead) the group in an orderly retreat {direction}!|n"
    ),
    failed_to_leader=(
        "|r*RETREAT FAILED* You try to organise a retreat but can't disengage!|n"
    ),
    failed_in_room=(
        "|y$You() $conj(try) to order a retreat but the group can't disengage!|n"
    ),
    no_exits="|rYou try to retreat but there's nowhere to go!|n",
    exhausted="You are too exhausted to lead a retreat.",
    room_msgs={
        "msg_from": "{name}'s group withdraws {direction} in good order.",
        "msg_to": "{name}'s group arrives {direction}, withdrawing in good order.",
    },
)


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
    aliases = []
    skill = skills.STRATEGY.value
    help_category = "Group Combat"

    def func(self):
        caller = self.caller

        # ── Mastery check ──
        if not (getattr(caller.db, "general_skill_mastery_levels", None)
                or getattr(caller.db, "class_skill_mastery_levels", None)
                or getattr(caller.db, "weapon_skill_mastery_levels", None)):
            return self.mob_func()

        mastery_int = caller.get_skill_mastery(self.skill)
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

        # ── The withdrawal itself ──
        retreat_group(
            caller,
            RETREAT_WORDING,
            direction=self.args.strip() if self.args else None,
            bonus=mastery.bonus,
        )

    # ── Mob fallback ──
    def mob_func(self):
        """Not implemented — mobs cannot order a retreat yet.

        When implementing: call ``combat_utils.retreat_group()`` with wording
        of your own rather than writing the process again. It already handles
        exit choice, the leader's roll, the movement cost, gathering the
        group, traversing, ending combat and cleaning up the enemies. Only
        the words and the skill bonus differ.
        """
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
