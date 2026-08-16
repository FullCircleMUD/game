"""
NFTDistributor — places NFT items (scrolls, recipes, rare items) on targets.

Uses assign_to_blank_token() + spawn_into() for placement.
Supports at-or-below tier filtering for scrolls and recipes.
"""

import logging

from blockchain.xrpl.services.spawn.distributors.base import BaseDistributor
from blockchain.xrpl.services.spawn.config import (
    SPAWN_CONFIG,
    populate_knowledge_config,
)

# The scroll and recipe entries are generated from the spell and recipe
# registries rather than written into the SPAWN_CONFIG literal, so something
# has to call this before the config is read. SpawnService does it on the
# router; shards run no spawn script but are the processes that actually
# place items, so it must also happen here. Module level, so it runs once per
# process on import rather than on every placement.
populate_knowledge_config(SPAWN_CONFIG)

logger = logging.getLogger("evennia")

def _resolve_nft_item_type_name(type_key):
    """Resolve a SPAWN_CONFIG type_key to an NFTItemType.name.

    Reads the prototype_key from config, then looks up the NFTItemType
    by prototype_key to get its display name (used by assign_to_blank_token).
    """
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
                BaseNFTItem.spawn_into(token_id, target)
            except Exception:
                logger.exception(
                    f"ScrollDistributor: failed to place {type_key} on {target}"
                )
                raise


class RecipeDistributor(BaseDistributor):
    """Distributes recipe scrolls to tagged targets with tier filtering."""

    tag_name = "spawn_recipes"
    category = "recipes"
    max_attr_name = "spawn_recipes_max"


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
                BaseNFTItem.spawn_into(token_id, target)
            except Exception:
                logger.exception(
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
                BaseNFTItem.spawn_into(token_id, target)
            except Exception:
                logger.exception(
                    f"RareNFTDistributor: failed to place {type_key} on {target}"
                )
                raise
