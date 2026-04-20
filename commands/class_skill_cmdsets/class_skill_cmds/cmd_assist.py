"""
CmdAssist — help an ally, granting them advantage.

BATTLESKILLS general skill, available to all characters.

In combat: gives an ally advantage against all enemies. Costs the
assister their next attack (skip_next_action). Mastery scales the
number of advantage rounds granted.

Out of combat: sets non_combat_advantage on the target for their
next skill check (picklock, search, hide, etc.). No mastery scaling.

Usage:
    assist <ally>
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see
from .cmd_skill_base import CmdSkillBase

ASSIST_ROUNDS = {
    MasteryLevel.BASIC: 1,
    MasteryLevel.SKILLED: 2,
    MasteryLevel.EXPERT: 3,
    MasteryLevel.MASTER: 4,
    MasteryLevel.GRANDMASTER: 5,
}


class CmdAssist(CmdSkillBase):
    """
    Assist an ally, granting them advantage.

    Usage:
        assist <ally>

    In combat: give up your next attack to grant an ally advantage
    against all enemies. Higher mastery grants more rounds.

    Out of combat: give an ally advantage on their next skill check.
    """

    key = "assist"
    skill = skills.BATTLESKILLS.value
    help_category = "Combat"

    def _find_target(self):
        """Parse and validate the assist target. Returns target or None."""
        caller = self.caller

        if not self.args or not self.args.strip():
            caller.msg("Assist who?")
            return None

        room = caller.location
        if not room:
            return None

        # Darkness — can't see who you're assisting
        if hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return None

        target, _ = resolve_target(
            caller, self.args.strip(), "actor_friendly",
            extra_predicates=(p_can_see,),
        )
        if not target:
            return None  # actor resolver already messaged

        if target == caller:
            caller.msg("You can't assist yourself.")
            return None

        return target

    def _do_assist_combat(self, target, rounds):
        """
        Combat assist: give ally advantage against all enemies.

        Returns True on success, False on failure.
        """
        caller = self.caller
        from combat.combat_utils import get_sides

        handler = caller.scripts.get("combat_handler")
        if not handler:
            caller.msg("You're not in combat.")
            return False
        handler = handler[0]

        # Target must be in combat
        target_handler = target.scripts.get("combat_handler")
        if not target_handler:
            caller.msg(f"{target.key} is not in combat.")
            return False
        target_handler = target_handler[0]

        # Target must be an ally
        allies, enemies = get_sides(caller)
        if target not in allies:
            caller.msg(f"{target.key} is not an ally.")
            return False

        # Give ally advantage against all enemies
        for enemy in enemies:
            target_handler.set_advantage(enemy, rounds=rounds)

        # Cost: skip assister's next attack
        handler.skip_next_action = True

        return True

    def _do_assist_noncombat(self, target):
        """
        Non-combat assist: set non_combat_advantage on the target.

        Returns True on success.
        """
        caller = self.caller

        # Must not be in combat
        if caller.scripts.get("combat_handler"):
            # Shouldn't reach here — combat path handles this
            return False

        # Check target has db (is an actor)
        if not hasattr(target, "db"):
            caller.msg("You can't assist that.")
            return False

        target.db.non_combat_advantage = True
        return True

    # ── Mastery dispatch ──

    def unskilled_func(self):
        self.caller.msg("You don't have the battle skills to assist effectively.")

    def basic_func(self):
        self._dispatch_assist(MasteryLevel.BASIC)

    def skilled_func(self):
        self._dispatch_assist(MasteryLevel.SKILLED)

    def expert_func(self):
        self._dispatch_assist(MasteryLevel.EXPERT)

    def master_func(self):
        self._dispatch_assist(MasteryLevel.MASTER)

    def grandmaster_func(self):
        self._dispatch_assist(MasteryLevel.GRANDMASTER)

    def _dispatch_assist(self, mastery):
        """Shared logic for all trained mastery levels."""
        caller = self.caller

        target = self._find_target()
        if not target:
            return

        in_combat = bool(caller.scripts.get("combat_handler"))

        if in_combat:
            rounds = ASSIST_ROUNDS[mastery]
            if self._do_assist_combat(target, rounds):
                caller.msg(
                    f"|yYou assist {target.key}, giving them the edge! "
                    f"(+{rounds} round{'s' if rounds > 1 else ''} advantage)|n"
                )
                if caller.location:
                    caller.location.msg_contents(
                        f"|y{caller.key} assists {target.key} in combat!|n",
                        exclude=[caller],
                    )
        else:
            if self._do_assist_noncombat(target):
                caller.msg(
                    f"|yYou assist {target.key}, giving them an edge "
                    f"on their next task.|n"
                )
                if caller.location:
                    caller.location.msg_contents(
                        f"|y{caller.key} assists {target.key}.|n",
                        exclude=[caller],
                    )

    # ── Mob fallback ──

    def mob_func(self):
        """Mobs don't use assist."""
        pass
