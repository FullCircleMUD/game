"""
Protect — intercept attacks aimed at an ally.

PROTECT skill (warrior, paladin). Toggle-based defensive ability.

When active, the protector has a flat percentage chance to intercept
attacks aimed at their protected ally, taking the full damage instead.

Intercept chance scales with mastery:
  BASIC 40%, SKILLED 50%, EXPERT 60%, MASTER 70%, GRANDMASTER 80%

Usage:
    protect <target>  — toggle protection on an ally (in combat)
    protect           — cancel protection (in combat)
"""

from combat.combat_utils import get_sides, INTERCEPT_CHANCE
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase


class CmdProtect(CmdSkillBase):
    """
    Protect an ally from attacks by intercepting blows.

    Usage:
        protect <target>
        protect

    When protecting an ally, you have a chance to intercept attacks
    aimed at them, taking the full damage yourself. The intercept
    chance scales with your mastery of the protect skill.

    Use 'protect' with no argument to stop protecting.
    """

    key = "protect"
    aliases = ["rescue", "prot", "resc"]
    skill = skills.PROTECT.value
    help_category = "Combat"

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
            caller.msg("You need training in protect before you can use it.")
            return

        # ── Must be in combat ──
        handlers = caller.scripts.get("combat_handler")
        if not handlers:
            caller.msg("You must be in combat to protect someone.")
            return
        handler = handlers[0]

        # ── No args: cancel protection ──
        if not self.args or not self.args.strip():
            if handler.protecting is not None:
                protected = None
                for obj in caller.location.contents:
                    if getattr(obj, "id", None) == handler.protecting:
                        protected = obj
                        break
                handler.protecting = None
                name = protected.key if protected else "your ally"
                caller.msg(f"|yYou stop protecting {name}.|n")
                if protected:
                    protected.msg(f"|y{caller.key} is no longer protecting you.|n")
                if caller.location:
                    caller.location.msg_contents(
                        f"|y{caller.key} stops protecting {name}.|n",
                        exclude=[caller] + ([protected] if protected else []),
                    )
            else:
                caller.msg("You aren't protecting anyone.")
            return

        # ── Parse target ──
        target = caller.search(self.args.strip())
        if not target:
            return

        # ── Validation ──
        if target == caller:
            caller.msg("You can't protect yourself.")
            return

        if not hasattr(target, "hp") or target.hp is None:
            caller.msg("You can't protect that.")
            return

        if target.hp <= 0:
            caller.msg(f"{target.key} is already dead.")
            return

        if target.location != caller.location:
            caller.msg("They're not here.")
            return

        # ── Must be an ally ──
        allies, _ = get_sides(caller)
        if target not in allies:
            caller.msg(f"{target.key} is not an ally.")
            return

        # ── Target must be in combat ──
        target_handlers = target.scripts.get("combat_handler")
        if not target_handlers:
            caller.msg(f"{target.key} is not in combat.")
            return

        # ── Toggle: same target → cancel ──
        if handler.protecting == target.id:
            handler.protecting = None
            caller.msg(f"|yYou stop protecting {target.key}.|n")
            target.msg(f"|y{caller.key} is no longer protecting you.|n")
            if caller.location:
                caller.location.msg_contents(
                    f"|y{caller.key} stops protecting {target.key}.|n",
                    exclude=[caller, target],
                )
            return

        # ── Activate protection (or switch target) ──
        old_protected_id = handler.protecting
        handler.protecting = target.id

        # Notify old target if switching
        if old_protected_id is not None:
            for obj in caller.location.contents:
                if getattr(obj, "id", None) == old_protected_id:
                    obj.msg(f"|y{caller.key} is no longer protecting you.|n")
                    break

        chance = INTERCEPT_CHANCE[mastery]
        caller.msg(
            f"|g*PROTECT* You move to protect {target.key}! "
            f"({chance}% intercept chance)|n"
        )
        target.msg(f"|g{caller.key} moves to protect you!|n")
        if caller.location:
            caller.location.msg_contents(
                f"|y{caller.key} moves to protect {target.key}!|n",
                exclude=[caller, target],
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
