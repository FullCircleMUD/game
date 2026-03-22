"""
CmdDodge — dodge incoming attacks, giving enemies disadvantage.

Costs the dodger their next attack. All enemies in combat get
disadvantage on their next attack against the dodger.

Mastery scaling (future): more attacks dodged / longer duration.
Mob fallback: innate dodge with room-visible flavor message.
"""

from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase


class CmdDodge(CmdSkillBase):
    """
    Dodge incoming attacks.

    Usage:
        dodge

    Gives up your next attack to focus on evasion. All enemies
    attacking you have disadvantage on their next attack.

    Must be in combat to use.
    """
    key = "dodge"
    skill = skills.BATTLESKILLS.value
    help_category = "Combat"

    def _do_dodge(self):
        """
        Shared dodge logic for both mastery and mob paths.

        Applies disadvantage to all enemies against the dodger,
        and queues a hold action (skipping the dodger's attack).
        """
        caller = self.caller
        from combat.combat_utils import get_sides

        # Must be in combat
        handler = caller.scripts.get("combat_handler")
        if not handler:
            caller.msg("You're not in combat.")
            return False

        handler = handler[0]
        _, enemies = get_sides(caller)

        # Give all enemies disadvantage against the dodger
        for enemy in enemies:
            enemy_handler = enemy.scripts.get("combat_handler")
            if enemy_handler:
                enemy_handler[0].set_disadvantage(caller, rounds=1)

        # Skip the dodger's next attack but keep the action queue intact.
        # The repeating attack will resume on the following tick.
        handler.skip_next_action = True

        return True

    # ── Mastery dispatch (players / humanoid NPCs with mastery) ──

    def unskilled_func(self):
        if self._do_dodge():
            self.caller.msg("|yYou clumsily try to dodge!|n")
            if self.caller.location:
                self.caller.location.msg_contents(
                    f"|y{self.caller.key} stumbles around, trying to dodge!|n",
                    exclude=[self.caller],
                )

    def basic_func(self):
        if self._do_dodge():
            self.caller.msg("|yYou dodge, weaving defensively!|n")
            if self.caller.location:
                self.caller.location.msg_contents(
                    f"|y{self.caller.key} weaves defensively, trying to dodge!|n",
                    exclude=[self.caller],
                )

    def skilled_func(self):
        self.basic_func()

    def expert_func(self):
        self.basic_func()

    def master_func(self):
        self.basic_func()

    def grandmaster_func(self):
        self.basic_func()

    # ── Mob fallback (animals, creatures without mastery) ──

    def mob_func(self):
        """Innate dodge for animal mobs — flavor text and disadvantage."""
        if self._do_dodge():
            if self.caller.location:
                self.caller.location.msg_contents(
                    f"|y{self.caller.key} dodges, leaping and twisting "
                    f"in the air, making it hard to hit!|n",
                )
