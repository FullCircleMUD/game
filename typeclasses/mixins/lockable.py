"""
LockableMixin — adds lock/unlock state to any closeable Evennia object.

Depends on CloseableMixin via duck typing (expects is_open, can_open).
Supports key items (matched by tag, consumed on use), lockpicking via
SUBTERFUGE skill, and auto-relock timers.

Usage:
    class WorldChest(CloseableMixin, LockableMixin, WorldFixture):
        def at_object_creation(self):
            super().at_object_creation()
            self.at_closeable_init()
            self.at_lockable_init()
"""

from evennia.typeclasses.attributes import AttributeProperty


class LockableMixin:
    """
    Mixin that tracks locked state with key and lockpicking support.

    Child classes MUST:
        1. Also inherit CloseableMixin (or equivalent duck type)
        2. Call at_lockable_init() from at_object_creation()
    """

    is_locked = AttributeProperty(False)
    lock_dc = AttributeProperty(15)         # difficulty class for lockpicking
    key_tag = AttributeProperty(None)       # matches key items by tag
    relock_seconds = AttributeProperty(0)   # 0 = no auto-relock

    def at_lockable_init(self):
        """
        Initialize lockable state. Call from at_object_creation().
        Safe to call multiple times.
        """
        pass  # defaults set via AttributeProperty

    def can_open(self, opener):
        """
        Override CloseableMixin.can_open() — blocks opening when locked.
        """
        if self.is_locked:
            return False, f"{self.key} is locked."
        # Chain to parent (CloseableMixin or further mixins)
        if hasattr(super(), "can_open"):
            return super().can_open(opener)
        return True, None

    def unlock(self, character, key_item):
        """
        Attempt to unlock this object using a key item.

        Args:
            character: The character attempting to unlock.
            key_item: A KeyItem to try against this lock.

        Returns:
            (bool, str): Success flag and message.
        """
        if not self.is_locked:
            return False, f"{self.key} is not locked."

        item_key_tag = getattr(key_item, "key_tag", None)
        if item_key_tag and item_key_tag == self.key_tag:
            # Key matches — consume it and unlock
            key_name = key_item.key
            key_item.delete()
            self.is_locked = False
            self.at_unlock(character)
            self._start_relock_timer()
            return True, (
                f"You use {key_name} to unlock {self.key}. "
                f"The key crumbles to dust."
            )
        else:
            return False, f"That key doesn't fit {self.key}."

    def picklock(self, character):
        """
        Attempt to pick the lock using SUBTERFUGE skill.

        Skill bonus = mastery bonus + DEX modifier.
        Called by the picklock skill command.

        Returns:
            (bool, str): Success flag and message.
        """
        if not self.is_locked:
            return False, f"{self.key} is not locked."

        from enums.mastery_level import MasteryLevel
        from enums.skills_enum import skills

        # Look up SUBTERFUGE mastery from class skills
        class_mastery = getattr(character.db, "class_skill_mastery_levels", None) or {}
        mastery_entry = class_mastery.get(skills.SUBTERFUGE.value)
        if mastery_entry:
            if hasattr(mastery_entry, "get"):
                mastery_int = int(mastery_entry.get("mastery", 0))
            else:
                mastery_int = int(mastery_entry)
        else:
            mastery_int = 0

        if mastery_int <= 0:
            return False, "You don't have the skill to pick locks."

        mastery_bonus = MasteryLevel(mastery_int).bonus

        # Add DEX modifier
        dex_mod = 0
        if hasattr(character, "dexterity") and hasattr(character, "get_attribute_bonus"):
            dex_mod = character.get_attribute_bonus(character.dexterity)

        skill_bonus = mastery_bonus + dex_mod

        # d20 + skill bonus vs lock_dc (non-combat advantage/disadvantage aware)
        from utils.dice_roller import dice
        has_adv = getattr(character.db, "non_combat_advantage", False)
        has_dis = getattr(character.db, "non_combat_disadvantage", False)
        roll = dice.roll_with_advantage_or_disadvantage(advantage=has_adv, disadvantage=has_dis)
        character.db.non_combat_advantage = False
        character.db.non_combat_disadvantage = False
        total = roll + skill_bonus

        if total >= self.lock_dc:
            self.is_locked = False
            self.at_unlock(character)
            self._start_relock_timer()
            return True, (
                f"You deftly pick the lock on {self.key}. "
                f"(Roll: {roll} + {skill_bonus} = {total} vs DC {self.lock_dc})"
            )
        else:
            return False, (
                f"You fail to pick the lock on {self.key}. "
                f"(Roll: {roll} + {skill_bonus} = {total} vs DC {self.lock_dc})"
            )

    def lock(self, character):
        """
        Attempt to lock this object. Must be closed first.

        Args:
            character: The character locking this object.

        Returns:
            (bool, str): Success flag and message.
        """
        if self.is_locked:
            return False, f"{self.key} is already locked."

        if hasattr(self, "is_open") and self.is_open:
            return False, f"You need to close {self.key} first."

        self.is_locked = True
        self.at_lock(character)
        return True, f"You lock {self.key}."

    def _start_relock_timer(self):
        """Start a relock timer script if relock_seconds > 0."""
        if self.relock_seconds and self.relock_seconds > 0:
            from typeclasses.scripts.relock_timer import RelockTimerScript

            # Remove any existing relock timer
            self.scripts.delete("relock_timer")

            script = self.scripts.add(
                RelockTimerScript,
                autostart=False,
            )
            script.db.relock_seconds = self.relock_seconds
            script.interval = self.relock_seconds
            script.start()

    def at_unlock(self, character):
        """Hook called after successfully unlocking. Override for custom behaviour."""
        pass

    def at_lock(self, character):
        """Hook called after successfully locking. Override for custom behaviour."""
        pass
