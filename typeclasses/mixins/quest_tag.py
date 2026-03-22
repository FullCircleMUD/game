"""
QuestTagMixin — makes any object quest-relevant.

Mix into any typeclass (NPC, mob, item, room) to make it participate in the
quest system. Objects with non-empty ``quest_tags`` fire scoped events to
nearby characters' quest handlers.

Usage:
    class QuestRoom(QuestTagMixin, RoomBase):
        pass

    # Or just mix into RoomBase directly — zero overhead when quest_tags is [].
    # Then tag individual rooms via @set or seed scripts:
    #   @set Ancient Shrine/quest_tags = ["warrior_initiation"]
"""

from evennia.typeclasses.attributes import AttributeProperty


class QuestTagMixin:
    """Mix into any object to make it quest-relevant.

    Attributes:
        quest_tags: List of quest key strings this object is associated with.
                    Only quests with matching keys will receive events.
    """

    quest_tags = AttributeProperty([])

    def fire_quest_event(self, character, event_type, **kwargs):
        """Notify a character's quest handler about a quest-relevant event.

        Only fires if this object has quest_tags set. Only dispatches to
        quests matching the tags — not all active quests.

        Args:
            character: The character to notify (must have a quests handler).
            event_type: String identifying the event ("kill", "enter_room",
                        "pickup", "deliver", etc.).
            **kwargs: Extra data passed through to quest.progress().
        """
        if not self.quest_tags:
            return
        handler = getattr(character, "quests", None)
        if handler:
            handler.check_progress(
                event_type,
                quest_keys=self.quest_tags,
                source=self,
                **kwargs,
            )
