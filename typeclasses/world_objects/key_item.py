"""
KeyItem — a consumable key that unlocks LockableMixin objects.

Matched to a lock by the key_tag attribute. Consumed (deleted) on
successful use by LockableMixin.unlock().

Usage:
    # In a build script or prototype:
    key = create_object(KeyItem, key="rusty iron key")
    key.key_tag = "iron_chest_01"
"""

from evennia import AttributeProperty

from typeclasses.world_objects.base_world_item import WorldItem


class KeyItem(WorldItem):
    """
    A key that unlocks a specific lock. Consumed on use.

    Attributes:
        key_tag: Matches against LockableMixin.key_tag on the lock.
        can_bank: Keys cannot be banked — must be carried to use.
    """

    key_tag = AttributeProperty(None)
    can_bank = AttributeProperty(False)
