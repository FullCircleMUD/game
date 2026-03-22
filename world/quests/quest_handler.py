"""
FCMQuestHandler — manages all quests on a character.

Sits on FCMCharacter as a lazy_property:
    @lazy_property
    def quests(self):
        return FCMQuestHandler(self)

Quest classes and per-quest data are stored in Evennia attributes on the
character. No migrations needed.
"""


class FCMQuestHandler:
    """
    Manages quest state for a single character.

    Storage:
        _quests (category=fcm_quests): dict of {quest_key: quest_class}
        _quest_data_{key} (category=fcm_quests): dict of per-quest data
    """

    quest_attr_key = "_quests"
    quest_attr_category = "fcm_quests"
    quest_data_template = "_quest_data_{quest_key}"
    quest_data_category = "fcm_quests"

    def __init__(self, obj):
        self.obj = obj
        self.quests = {}
        self.quest_classes = {}
        self._load()

    def _load(self):
        """Load quest classes from character attributes and instantiate."""
        self.quest_classes = self.obj.attributes.get(
            self.quest_attr_key,
            category=self.quest_attr_category,
            default={},
        )
        for quest_key, quest_class in self.quest_classes.items():
            self.quests[quest_key] = quest_class(self.obj, handler=self)

    def _save(self):
        """Persist quest class references to character attribute."""
        self.obj.attributes.add(
            self.quest_attr_key,
            self.quest_classes,
            category=self.quest_attr_category,
        )

    # ── Queries ──

    def has(self, quest_key):
        """Check if character has this quest (any status)."""
        return quest_key in self.quests

    def get(self, quest_key):
        """Get quest instance by key, or None."""
        return self.quests.get(quest_key)

    def all(self):
        """Get all quest instances."""
        return list(self.quests.values())

    def active(self):
        """Get quests with status 'started'."""
        return [q for q in self.quests.values() if q.status == "started"]

    def completed(self):
        """Get quests with status 'completed'."""
        return [q for q in self.quests.values() if q.is_completed]

    def is_completed(self, quest_key):
        """Convenience: check if a specific quest is completed."""
        quest = self.quests.get(quest_key)
        return quest.is_completed if quest else False

    # ── Add / Remove ──

    def add(self, quest_class):
        """Accept a new quest.

        Args:
            quest_class: The quest CLASS (not instance) to start.

        Returns:
            FCMQuest: The newly created quest instance.
        """
        self.quest_classes[quest_class.key] = quest_class
        quest = quest_class(self.obj, handler=self)
        self.quests[quest_class.key] = quest
        self._save()
        quest.on_accept()
        return quest

    def remove(self, quest_key):
        """Remove a quest. If not completed, it will be abandoned."""
        quest = self.quests.get(quest_key)
        if quest:
            if not quest.is_completed:
                quest.abandon()
            quest.cleanup()
        self.quest_classes.pop(quest_key, None)
        self.quests.pop(quest_key, None)
        self._save()
        # Clean up quest data attribute
        self.obj.attributes.remove(
            self.quest_data_template.format(quest_key=quest_key),
            category=self.quest_data_category,
        )

    # ── Event dispatch ──

    def check_progress(self, event_type, quest_keys=None, **kwargs):
        """Check progress on matching active quests.

        Called by QuestTagMixin.fire_quest_event() when a quest-relevant
        event occurs (kill, enter_room, pickup, etc.).

        Args:
            event_type: String identifying the event ("kill", "enter_room", etc.)
            quest_keys: List of quest key strings to check. If None, checks
                        ALL active quests.
            **kwargs: Extra data passed to quest.progress() (source object, etc.)
        """
        for quest in self.active():
            if quest_keys and quest.key not in quest_keys:
                continue
            quest.progress(event_type=event_type, **kwargs)

    # ── Persistence ──

    def save_quest_data(self, quest_key):
        """Save per-quest data dict to character attribute."""
        quest = self.quests.get(quest_key)
        if quest:
            self.obj.attributes.add(
                self.quest_data_template.format(quest_key=quest_key),
                quest.data,
                category=self.quest_data_category,
            )

    def load_quest_data(self, quest_key):
        """Load per-quest data dict from character attribute."""
        return self.obj.attributes.get(
            self.quest_data_template.format(quest_key=quest_key),
            category=self.quest_data_category,
            default={},
        )
