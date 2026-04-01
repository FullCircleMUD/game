"""
NFTDistributor — places NFT items (scrolls, recipes, rare items) on targets.

Uses assign_to_blank_token() + spawn_into() for placement.
Supports at-or-below tier filtering for scrolls and recipes.
"""

import logging

from blockchain.xrpl.services.spawn.distributors.base import BaseDistributor
from blockchain.xrpl.services.spawn.headroom import count_nfts

logger = logging.getLogger("evennia")

# Tier hierarchy for at-or-below filtering.
TIER_ORDER = ["basic", "skilled", "expert", "master", "gm"]
TIER_RANK = {tier: i for i, tier in enumerate(TIER_ORDER)}


def _resolve_nft_item_type_name(type_key):
    """Resolve a SPAWN_CONFIG type_key to an NFTItemType.name.

    Reads the prototype_key from config, then looks up the NFTItemType
    by prototype_key to get its display name (used by assign_to_blank_token).
    """
    from blockchain.xrpl.services.spawn.config import SPAWN_CONFIG

    cfg = SPAWN_CONFIG.get(("knowledge", type_key), {})
    prototype_key = cfg.get("prototype_key")
    if not prototype_key:
        return None

    from blockchain.xrpl.models import NFTItemType
    try:
        item_type = NFTItemType.objects.get(prototype_key=prototype_key)
        return item_type.name
    except NFTItemType.DoesNotExist:
        return None


class ScrollDistributor(BaseDistributor):
    """Distributes spell scrolls to tagged targets with tier filtering."""

    tag_name = "spawn_scrolls"
    category = "scrolls"
    max_attr_name = "spawn_scrolls_max"

    def _get_max_for_key(self, target, type_key):
        """Get available slots for a scroll at its tier using at-or-below.

        A scroll can be placed in any slot of its tier or higher.
        Returns the number of open slots that accept this scroll's tier.
        """
        from blockchain.xrpl.services.spawn.config import SPAWN_CONFIG

        # Look up the scroll's tier from config
        cfg_key = ("knowledge", type_key)
        cfg = SPAWN_CONFIG.get(cfg_key, {})
        scroll_tier = cfg.get("tier", "basic")
        scroll_rank = TIER_RANK.get(scroll_tier, 0)

        # Get per-tier max dict
        max_dict = getattr(target.db, self.max_attr_name, None)
        if not max_dict:
            return 0

        # Sum slots at scroll's tier or higher (at-or-below: scroll fits
        # in any slot of equal or higher tier)
        total_slots = 0
        for tier, max_count in dict(max_dict).items():
            tier_rank = TIER_RANK.get(tier, 0)
            if tier_rank >= scroll_rank and max_count > 0:
                total_slots += max_count

        # Subtract current scrolls already placed
        current_scrolls = count_nfts(target, "scrolls")
        return max(0, total_slots - current_scrolls)

    def _place(self, target, type_key, amount):
        """Place scroll NFTs on a target.

        Resolves prototype_key from SPAWN_CONFIG, looks up the NFTItemType
        name, then assigns a blank token and spawns the item.
        """
        item_type_name = _resolve_nft_item_type_name(type_key)
        if not item_type_name:
            logger.warning(f"ScrollDistributor: no NFTItemType for {type_key}")
            return

        from typeclasses.items.base_nft_item import BaseNFTItem
        for _ in range(amount):
            try:
                token_id = BaseNFTItem.assign_to_blank_token(item_type_name)
                obj = BaseNFTItem.spawn_into(token_id, target)
                if obj:
                    obj.tags.add("loot", category="item")
            except Exception:
                logger.log_trace(
                    f"ScrollDistributor: failed to place {type_key} on {target}"
                )
                raise


class RecipeDistributor(BaseDistributor):
    """Distributes recipe scrolls to tagged targets with tier filtering."""

    tag_name = "spawn_recipes"
    category = "recipes"
    max_attr_name = "spawn_recipes_max"

    def _get_max_for_key(self, target, type_key):
        """Get available slots for a recipe at its tier using at-or-below."""
        from blockchain.xrpl.services.spawn.config import SPAWN_CONFIG

        cfg_key = ("knowledge", type_key)
        cfg = SPAWN_CONFIG.get(cfg_key, {})
        recipe_tier = cfg.get("tier", "basic")
        recipe_rank = TIER_RANK.get(recipe_tier, 0)

        max_dict = getattr(target.db, self.max_attr_name, None)
        if not max_dict:
            return 0

        total_slots = 0
        for tier, max_count in dict(max_dict).items():
            tier_rank = TIER_RANK.get(tier, 0)
            if tier_rank >= recipe_rank and max_count > 0:
                total_slots += max_count

        current_recipes = count_nfts(target, "recipes")
        return max(0, total_slots - current_recipes)

    def _place(self, target, type_key, amount):
        """Place recipe NFTs on a target."""
        item_type_name = _resolve_nft_item_type_name(type_key)
        if not item_type_name:
            logger.warning(f"RecipeDistributor: no NFTItemType for {type_key}")
            return

        from typeclasses.items.base_nft_item import BaseNFTItem
        for _ in range(amount):
            try:
                token_id = BaseNFTItem.assign_to_blank_token(item_type_name)
                obj = BaseNFTItem.spawn_into(token_id, target)
                if obj:
                    obj.tags.add("loot", category="item")
            except Exception:
                logger.log_trace(
                    f"RecipeDistributor: failed to place {type_key} on {target}"
                )
                raise


class RareNFTDistributor(BaseDistributor):
    """Distributes rare/legendary NFT items with exact-match capacity."""

    tag_name = "spawn_nfts"
    category = "nfts"
    max_attr_name = "spawn_nfts_max"

    def _place(self, target, type_key, amount):
        """Place rare NFT items on a target."""
        from typeclasses.items.base_nft_item import BaseNFTItem

        for _ in range(amount):
            try:
                token_id = BaseNFTItem.assign_to_blank_token(type_key)
                obj = BaseNFTItem.spawn_into(token_id, target)
                if obj:
                    obj.tags.add("loot", category="item")
            except Exception:
                logger.log_trace(
                    f"RareNFTDistributor: failed to place {type_key} on {target}"
                )
                raise
