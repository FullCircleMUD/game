"""
Identify command — use bardic LORE to identify items.

Class skill (LORE) — bard. No mana cost (knowledge-based, not arcane).
Reuses the Identify spell's template builder for consistent output.

For creature/actor identification, see ``recognise``.

LORE mastery maps directly to identification tier:
    BASIC(1):       basic items
    SKILLED(2):     uncommon items
    EXPERT(3):      rare items
    MASTER(4):      legendary items
    GRANDMASTER(5): all items

Usage:
    identify <target>
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see
from .cmd_skill_base import CmdSkillBase


class CmdIdentify(CmdSkillBase):
    """
    Identify an item using your lore knowledge.

    Usage:
        identify <target>

    Uses your LORE skill mastery to reveal properties of items.
    Higher mastery reveals more powerful items. For identifying
    creatures, use |wrecognise|n.
    """

    key = "identify"
    aliases = []
    skill = skills.LORE.value
    help_category = "Performance"
    allow_while_sleeping = True

    def func(self):
        """Override base dispatch — identify works the same at all mastery levels."""
        caller = self.caller

        # Get LORE mastery tier from class skills
        class_mastery = (
            getattr(caller.db, "class_skill_mastery_levels", None) or {}
        )
        mastery_entry = class_mastery.get(self.skill)
        if mastery_entry:
            if hasattr(mastery_entry, "get"):
                tier = int(mastery_entry.get("mastery", 0))
            else:
                tier = int(mastery_entry)
        else:
            tier = 0

        if tier < MasteryLevel.BASIC.value:
            caller.msg("You don't have enough lore knowledge to identify anything.")
            return

        if not self.args:
            caller.msg("Identify what? Usage: identify <target>")
            return

        room = caller.location
        if not room:
            return

        # Darkness — can't see what you're identifying
        if hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        target, _ = resolve_target(
            caller, self.args.strip(), "items_inventory_then_room_all",
            extra_predicates=(p_can_see,),
        )
        if not target:
            caller.msg(f"You don't see '{self.args.strip()}' here.")
            return

        from utils.inspection_templates import inspect_item

        success, result = inspect_item(caller, target, tier)

        # Display result
        if isinstance(result, str):
            caller.msg(result)
        elif isinstance(result, dict):
            if result.get("first"):
                caller.msg(result["first"])
            if result.get("third") and caller.location:
                caller.location.msg_contents(
                    result["third"], exclude=[caller],
                )

    # Mastery stubs — not used (func() overridden above)
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
