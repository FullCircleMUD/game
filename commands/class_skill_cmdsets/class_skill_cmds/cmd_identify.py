"""
Identify command — use bardic LORE to identify items and creatures.

Class skill (LORE) — bard. No mana cost (knowledge-based, not arcane).
Reuses the Identify spell's template builders for consistent output.

LORE mastery maps directly to identification tier:
    BASIC(1):       actors levels 1-5, basic items
    SKILLED(2):     actors levels 6-15
    EXPERT(3):      actors levels 16-25
    MASTER(4):      actors levels 26-35
    GRANDMASTER(5): actors levels 36+

Usage:
    identify <target>
    id <target>
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase


class CmdIdentify(CmdSkillBase):
    """
    Identify an item or creature using your lore knowledge.

    Usage:
        identify <target>
        id <target>

    Uses your LORE skill mastery to reveal properties of items
    and creatures. Higher mastery reveals more powerful targets.
    """

    key = "identify"
    aliases = ["id"]
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

        target = caller.search(self.args.strip())
        if not target:
            return  # caller.search already sent error message

        # Classify and identify — shared inspection templates used by
        # both the Identify/Augur spells and this bard LORE command.
        from typeclasses.actors.base_actor import BaseActor
        from utils.inspection_templates import inspect_actor, inspect_item

        if isinstance(target, BaseActor):
            # PvP room check for other players
            from typeclasses.actors.character import FCMCharacter
            if isinstance(target, FCMCharacter) and target != caller:
                room = caller.location
                if not getattr(room, "allow_pvp", False):
                    caller.msg(
                        "You can only identify other players in PvP areas."
                    )
                    return

            success, result = inspect_actor(caller, target, tier)
        else:
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
