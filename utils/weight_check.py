"""
Weight check utilities for commands that move items/fungibles into inventory.

Usage in commands:
    from utils.weight_check import check_can_carry, get_item_weight

    ok, msg = check_can_carry(caller, get_item_weight(item))
    if not ok:
        caller.msg(msg)
        return
"""

from django.conf import settings

from blockchain.xrpl.currency_cache import get_resource_type


def check_can_carry(carrier, additional_weight):
    """
    Check if carrier can take on additional weight.

    Returns (True, None) if OK, or (False, error_message) if overloaded.
    Gracefully handles objects without CarryingCapacityMixin.
    """
    if not hasattr(carrier, "can_carry"):
        return (True, None)
    if carrier.can_carry(additional_weight):
        return (True, None)
    remaining = carrier.get_remaining_capacity()
    return (
        False,
        f"You can't carry that much. "
        f"(Need: {additional_weight:.1f} kg, Available: {remaining:.1f} kg)",
    )


def get_item_weight(item):
    """Return the weight of an NFT item (0.0 if not set)."""
    return getattr(item, "weight", 0.0) or 0.0


def get_gold_weight(amount):
    """Return total weight for a given amount of gold."""
    return amount * settings.GOLD_WEIGHT_PER_UNIT_KG


def get_resource_weight(resource_id, amount):
    """Return total weight for a given amount of a resource type."""
    rt = get_resource_type(resource_id)
    return amount * rt["weight_per_unit_kg"] if rt else 0.0
