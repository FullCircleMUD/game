"""
Wearslot enums — single source of truth for all valid slot names.

One enum per creature type. Items declare which slot(s) they fit using
these enum values. Wearslot mixins use them to define available slots.
This prevents typos and ensures items and mixins always agree on names.

Usage:
    from enums.wearslot import HumanoidWearSlot, DogWearSlot
"""

from enum import Enum


class HumanoidWearSlot(Enum):
    """Equipment slots for humanoid characters (players, humanoid NPCs/mobs)."""
    # Head to toe order — this order is used for display
    HEAD = "HEAD"
    FACE = "FACE"
    LEFT_EAR = "LEFT_EAR"
    RIGHT_EAR = "RIGHT_EAR"
    NECK = "NECK"
    CLOAK = "CLOAK"
    BODY = "BODY"
    LEFT_ARM = "LEFT_ARM"
    RIGHT_ARM = "RIGHT_ARM"
    HANDS = "HANDS"
    LEFT_WRIST = "LEFT_WRIST"
    RIGHT_WRIST = "RIGHT_WRIST"
    LEFT_RING_FINGER = "LEFT_RING_FINGER"
    RIGHT_RING_FINGER = "RIGHT_RING_FINGER"
    WAIST = "WAIST"
    LEGS = "LEGS"
    FEET = "FEET"
    WIELD = "WIELD"
    HOLD = "HOLD"


class DogWearSlot(Enum):
    """Equipment slots for dogs (collars, coats, etc.)."""
    DOG_NECK = "DOG_NECK"
    DOG_BODY = "DOG_BODY"


class MuleWearSlot(Enum):
    """Equipment slots mule pets."""
    PANNIER = "PANNIER"
    BRIDLE = "BRIDLE"
    HORSE_SHOES = "HORSE_SHOES"


class HorseWearSlot(Enum):
    """Equipment slots mule pets."""
    SADDLE_BAG = "SADDLE_BAG"
    SADDLE = "SADDLE"
    BRIDLE = "BRIDLE"
    HORSE_SHOES = "HORSE_SHOES"