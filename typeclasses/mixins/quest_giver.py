"""
QuestGiverMixin — gives any NPC the ability to offer, track, and turn in quests.

Mix into any NPC typeclass to add quest-giving capabilities. Provides:
- ``quest_key`` attribute: the quest this NPC offers
- ``QuestGiverCmdSet`` with ``quest`` command: accept, abandon, view, turn-in
- ``get_quest_completion_message()`` hook for custom completion text

The ``quest`` command reads ``quest_key`` from ``self.obj`` (the NPC),
looks up the quest class from the registry, and handles the full lifecycle.

Usage::

    class MyQuestNPC(QuestGiverMixin, BaseNPC):
        quest_key = AttributeProperty("my_quest")

        def get_quest_completion_message(self, caller, quest):
            return "|gWell done, adventurer!|n"
"""

from evennia import CmdSet, Command
from evennia.typeclasses.attributes import AttributeProperty


# ── CmdNPCQuest ──────────────────────────────────────────────────────

class CmdNPCQuest(Command):
    """
    View, accept, or abandon a quest from this NPC.

    Usage:
        quest           — show quest info and your progress
        quest accept    — accept the quest
        quest abandon   — abandon the quest

    Available when in the same room as an NPC that offers a quest.
    """

    key = "quest"
    aliases = ["qu"]
    locks = "cmd:all()"
    help_category = "Quests"

    def func(self):
        caller = self.caller
        npc = self.obj

        if npc.location != caller.location:
            caller.msg("There is nobody here offering a quest.")
            return

        quest_key = getattr(npc, "quest_key", None)
        if not quest_key:
            caller.msg(f"{npc.key} has no quest for you.")
            return

        from world.quests import get_quest
        quest_class = get_quest(quest_key)
        if not quest_class:
            caller.msg("Quest not found.")
            return

        args = self.args.strip().lower()

        if args == "accept":
            self._handle_accept(caller, quest_key, quest_class)
            return

        if args == "abandon":
            self._handle_abandon(caller, quest_key)
            return

        # Default: show quest info (and attempt turn-in for active quests)
        self._handle_view(caller, npc, quest_key, quest_class)

    def _handle_accept(self, caller, quest_key, quest_class):
        """Accept the quest."""
        if caller.quests.has(quest_key):
            quest = caller.quests.get(quest_key)
            if quest.is_completed:
                caller.msg("You have already completed this quest.")
            else:
                caller.msg("You are already on this quest.")
            return
        can_accept, reason = quest_class.can_accept(caller)
        if not can_accept:
            if reason:
                caller.msg(f"|r{reason}|n")
            return
        quest = caller.quests.add(quest_class)
        caller.msg(f"|gYou have accepted the quest: {quest_class.name}|n")
        caller.msg(quest.help())

    def _handle_abandon(self, caller, quest_key):
        """Abandon the quest."""
        if not caller.quests.has(quest_key):
            caller.msg("You are not on this quest.")
            return
        quest = caller.quests.get(quest_key)
        if quest.is_completed:
            caller.msg("This quest is already completed.")
            return
        caller.quests.remove(quest_key)
        caller.msg("You have abandoned the quest.")

    def _handle_view(self, caller, npc, quest_key, quest_class):
        """Show quest info and attempt turn-in."""
        lines = [f"|w=== {quest_class.name} ===|n", quest_class.desc, ""]

        if caller.quests.has(quest_key):
            quest = caller.quests.get(quest_key)
            # Try to advance the quest (NPC is the turn-in point)
            if not quest.is_completed and not quest.is_failed:
                quest.progress()
            # Re-check status after progress
            if quest.is_completed:
                completion_msg = npc.get_quest_completion_message(
                    caller, quest
                )
                lines.append(completion_msg)
            elif quest.is_failed:
                lines.append(f"|r{quest.help()}|n")
            else:
                lines.append(f"|wStatus:|n In Progress")
                lines.append(quest.help())
        else:
            can_accept, reason = quest_class.can_accept(caller)
            if can_accept:
                lines.append("Type |wquest accept|n to begin this quest.")
            elif reason:
                # Empty reason = silently suppressed (e.g. account cap reached)
                lines.append(f"|r{reason}|n")

        caller.msg("\n".join(lines))


# ── CmdSet ───────────────────────────────────────────────────────────

class QuestGiverCmdSet(CmdSet):
    """Quest command available from any NPC with QuestGiverMixin."""

    key = "QuestGiverCmdSet"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        self.add(CmdNPCQuest())


# ── Mixin ────────────────────────────────────────────────────────────

class QuestGiverMixin:
    """
    Mix into any NPC to give it quest-giving capabilities.

    Adds a ``quest`` command (accept/abandon/view/turn-in) and a
    ``quest_key`` attribute identifying the quest this NPC offers.

    Override ``get_quest_completion_message()`` for custom completion text.
    """

    quest_key = AttributeProperty(None)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(QuestGiverCmdSet, persistent=True)

    def get_quest_completion_message(self, caller, quest):
        """
        Return the message shown when a player completes this NPC's quest.

        Override in subclasses for custom completion text.

        Args:
            caller: The character who completed the quest.
            quest: The completed quest instance.

        Returns:
            str: The completion message.
        """
        return f"|gQuest completed: {quest.name}|n"
