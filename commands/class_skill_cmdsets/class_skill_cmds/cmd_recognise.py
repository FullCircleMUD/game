"""
Recognise command — use bardic LORE to identify creatures and actors.

Class skill (LORE) — bard. No mana cost (knowledge-based, not arcane).
Reuses the Augur spell's template builder for consistent output.

For item identification, see ``identify``.

LORE mastery maps directly to identification tier:
    BASIC(1):       actors levels 1-5
    SKILLED(2):     actors levels 6-15
    EXPERT(3):      actors levels 16-25
    MASTER(4):      actors levels 26-35
    GRANDMASTER(5): actors levels 36+

Usage:
    recognise <target>
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see
from .cmd_skill_base import CmdSkillBase


class CmdRecognise(CmdSkillBase):
    """
    Identify a creature or character using your lore knowledge.

    Usage:
        recognise <target>

    Uses your LORE skill mastery to reveal stats and abilities
    of creatures. Higher mastery reveals more powerful creatures.
    For identifying items, use |widentify|n.
    """

    key = "recognise"
    aliases = []
    skill = skills.LORE.value
    help_category = "Performance"

    def func(self):
        """Override base dispatch — recognise works the same at all mastery levels."""
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
            caller.msg("You don't have enough lore knowledge to recognise anything.")
            return

        if not self.args:
            caller.msg("Recognise what? Usage: recognise <target>")
            return

        room = caller.location
        if not room:
            return

        # Darkness — can't see what you're studying
        if hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        target, _ = resolve_target(
            caller, self.args.strip(), "actor_hostile",
            extra_predicates=(p_can_see,),
        )
        if not target:
            return  # actor resolver already messaged

        # PvP room check for other players
        from typeclasses.actors.character import FCMCharacter
        if isinstance(target, FCMCharacter) and target != caller:
            if not getattr(room, "allow_pvp", False):
                caller.msg(
                    "You can only recognise other players in PvP areas."
                )
                return

        from utils.inspection_templates import inspect_actor

        success, result = inspect_actor(caller, target, tier)

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
