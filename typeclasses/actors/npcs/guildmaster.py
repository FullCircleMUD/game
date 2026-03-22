"""
GuildmasterNPC — manages multiclassing and class level advancement.

Placed in guild headquarters. Players interact via commands injected by this
NPC's CmdSet (available to characters in the same room):
    guild     — show guild info, class requirements, character's progress
    quest     — view/accept/abandon the guild quest (via QuestGiverMixin)
    join      — begin multiclassing into this guild's class
    advance   — spend a pending level on this guild's class
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.npc import BaseNPC
from typeclasses.mixins.quest_giver import QuestGiverMixin


class GuildmasterNPC(QuestGiverMixin, BaseNPC):
    """
    Guild leader — manages multiclassing and class level advancement.

    Inherits quest-giving from QuestGiverMixin. The ``quest_key`` property
    delegates to ``multi_class_quest_key`` for backward compatibility.

    Configuration (set per instance via @set or seed script):
        guild_class: character class key this guild serves
            e.g. "warrior"
        multi_class_quest_key: quest key that must be completed to join
            as a multiclass (None for first class / no quest required)
        max_advance_level: highest class level this guildmaster can grant
            (default 40 = no practical cap)
        next_guildmaster_hint: flavour text pointing to the next guildmaster
            e.g. "the War Marshal in the Capital"
    """

    guild_class = AttributeProperty(None)           # e.g. "warrior"
    multi_class_quest_key = AttributeProperty(None)  # quest gate for multiclass
    max_advance_level = AttributeProperty(40)        # level cap for this guildmaster
    next_guildmaster_hint = AttributeProperty(None)  # redirect hint text

    @property
    def quest_key(self):
        """Delegate to multi_class_quest_key for backward compatibility."""
        return self.multi_class_quest_key

    @quest_key.setter
    def quest_key(self, value):
        self.multi_class_quest_key = value

    def at_object_creation(self):
        super().at_object_creation()
        from commands.npc_cmds.cmdset_guildmaster import GuildmasterCmdSet
        self.cmdset.add(GuildmasterCmdSet, persistent=True)

    def get_quest_completion_message(self, caller, quest):
        """Guild-specific completion message."""
        class_key = self.guild_class
        classes = caller.db.classes or {}
        if class_key and class_key in classes:
            return (
                "|gCongratulations! You have completed the quest and been "
                "inducted into the guild. When you are ready, type "
                "|wadvance|g to continue your training.|n"
            )
        return "|gQuest completed!|n Type |wjoin|n to join the guild."
