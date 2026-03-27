"""
Headroom calculation — get_current_count() and count_nfts().

Provides a uniform way to answer "how much of X does this target
currently hold?" for headroom = spawn_<cat>_max[key] - current.
"""

import logging

logger = logging.getLogger("evennia")

# Typeclass path fragments for category matching in count_nfts.
_CATEGORY_TYPECLASS_FRAGMENTS = {
    "scrolls": "spell_scroll_nft_item",
    "recipes": "crafting_recipe_nft_item",
}


def get_current_count(target, category, key):
    """Get how much of item (category, key) a target currently holds.

    Args:
        target: Evennia object (room, mob, container)
        category: "resources", "gold", "scrolls", "recipes", or "nfts"
        key: resource_id (int/str), "gold", or item_type_name (str)

    Returns:
        int — current count of the item on this target
    """
    if category == "resources":
        # Harvest room exception — uses db.resource_count, not db.resources
        if hasattr(target.db, "resource_count") and target.db.resource_count is not None:
            return target.db.resource_count or 0
        # Mob/container — FungibleInventoryMixin
        resources = getattr(target.db, "resources", None) or {}
        # Handle both int and string keys (Evennia serialization)
        return resources.get(key, resources.get(str(key), 0))

    elif category == "gold":
        return getattr(target.db, "gold", 0) or 0

    elif category in ("scrolls", "recipes", "nfts"):
        return count_nfts(target, category, key)

    return 0


def count_nfts(target, category, key=None):
    """Count matching NFT items in a target's contents + equipped slots.

    For scrolls/recipes: counts all items of that category (by typeclass).
    For nfts (rare): counts items matching the specific key (by prototype_key
    or item_type_name from NFTItemType).

    Args:
        target: Evennia object with contents
        category: "scrolls", "recipes", or "nfts"
        key: For "nfts", the specific item_type_name to match.
             For "scrolls"/"recipes", not used (counts all of category).

    Returns:
        int — count of matching NFT items
    """
    count = 0

    # Gather all items: contents + equipped (wearslots)
    items = list(target.contents)
    wearslots = getattr(target.db, "wearslots", None)
    if wearslots:
        # wearslots is a dict of {slot_name: item_or_None}
        for slot_item in dict(wearslots).values():
            if slot_item and slot_item not in items:
                items.append(slot_item)

    if category in ("scrolls", "recipes"):
        # Match by typeclass path fragment
        fragment = _CATEGORY_TYPECLASS_FRAGMENTS.get(category)
        if not fragment:
            return 0
        for item in items:
            tc_path = getattr(item, "typeclass_path", "") or ""
            if fragment in tc_path:
                count += 1

    elif category == "nfts":
        # Exact match on prototype_key or key attribute
        if not key:
            return 0
        for item in items:
            proto = getattr(item.db, "prototype_key", None)
            if proto and proto == key:
                count += 1

    return count
