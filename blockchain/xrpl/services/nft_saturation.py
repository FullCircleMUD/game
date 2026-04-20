"""
NFT Saturation Service — hourly data collection for saturation-based
NFT item spawning.

Collects three inputs:
1. Active player count (7-day window) from PlayerSession
2. Knowledge counts — per spell/recipe, how many active players know it
3. NFT circulation counts — per item type, how many in player hands / world

Writes SaturationSnapshot rows (one per tracked item per hour). The loot
selection algorithm reads these snapshots to weight drops toward
undersaturated items.
"""

import logging
from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from blockchain.xrpl.models import (
    NFTGameState,
    NFTItemType,
    PlayerSession,
    SaturationSnapshot,
)

logger = logging.getLogger("blockchain.xrpl")

# Typeclass paths for scroll/recipe NFTs (used to identify unlearned copies)
SCROLL_TYPECLASS = "typeclasses.items.consumables.spell_scroll_nft_item.SpellScrollNFTItem"
RECIPE_TYPECLASS = "typeclasses.items.consumables.crafting_recipe_nft_item.CraftingRecipeNFTItem"

# Spell school keys — class skills that appear as spell.school on registered spells.
# Stored in db.class_skill_mastery_levels as {key: {"mastery": int, "classes": [...]}}.
SPELL_SCHOOL_KEYS = {
    "evocation", "conjuration", "divination", "abjuration",
    "necromancy", "illusion",
    "divine_healing", "divine_protection", "divine_judgement",
    "divine_revelation", "divine_dominion",
    "nature_magic",
}

# Crafting skill keys — skills that appear as recipe["skill"].
# Most are general skills stored in db.general_skill_mastery_levels as {key: int}.
# Enchanting is a class skill (mage only) stored in db.class_skill_mastery_levels,
# but it uses the recipe system, so we treat it as a crafting skill for saturation.
CRAFTING_SKILL_KEYS = {
    "blacksmith", "jeweller", "carpenter", "alchemist",
    "tailor", "leatherworker", "enchanting",
}


def _players_at_or_above(distribution, min_level):
    """Sum players with mastery >= min_level from a {level: count} dict."""
    return sum(count for level, count in distribution.items() if level >= min_level)


class NFTSaturationService:
    """Stateless service — all methods are static, called hourly."""

    @staticmethod
    def take_snapshot():
        """Main entry point. Called hourly by NFTSaturationScript.

        Collects active player count, mastery distributions, knowledge
        counts, unlearned copy counts, and NFT circulation counts. Writes
        one SaturationSnapshot row per tracked spell, recipe, and item type.

        Saturation for knowledge items (spells/recipes) uses mastery-aware
        denominators — only players who could learn the spell/recipe count.
        """
        hour = timezone.now().replace(minute=0, second=0, microsecond=0)

        # 1. Active players
        active_count, active_char_keys = NFTSaturationService.get_active_player_count_7d()

        if active_count == 0:
            logger.info("NFTSaturation: no active players in 7d, skipping")
            return

        # 2. Knowledge counts (spells + recipes)
        spell_counts, recipe_counts = NFTSaturationService.get_knowledge_counts(
            active_char_keys
        )

        # 3. Unlearned copies in player hands
        unlearned_scroll_counts, unlearned_recipe_counts = (
            NFTSaturationService.get_unlearned_copy_counts()
        )

        # 4. NFT circulation per item type
        circulation_counts = NFTSaturationService.get_nft_circulation_counts()

        # 5. Mastery distributions (for mastery-aware denominators)
        spell_school_dist = NFTSaturationService.get_active_players_7d_by_spell_school(
            active_char_keys
        )
        recipe_skill_dist = NFTSaturationService.get_active_players_7d_by_recipe_skill(
            active_char_keys
        )

        # 6. Write snapshot rows
        rows_written = 0

        # 6a. All registered spells
        from world.spells.registry import SPELL_REGISTRY

        for spell_key, spell in SPELL_REGISTRY.items():
            known_by = spell_counts.get(spell_key, 0)
            unlearned = unlearned_scroll_counts.get(spell_key, 0)
            school_dist = spell_school_dist.get(spell.school_key, {})
            eligible = _players_at_or_above(school_dist, spell.min_mastery.value)
            sat = (known_by + unlearned) / eligible if eligible > 0 else 0.0
            # Prefixed key matches spawn config type_key (scroll_X)
            SaturationSnapshot.objects.update_or_create(
                hour=hour,
                item_key=f"scroll_{spell_key}",
                category=SaturationSnapshot.CATEGORY_SPELL,
                defaults={
                    "active_players_7d": active_count,
                    "eligible_players": eligible,
                    "known_by": known_by,
                    "unlearned_copies": unlearned,
                    "in_circulation": 0,
                    "saturation": sat,
                },
            )
            rows_written += 1

        # 6b. All registered recipes
        from world.recipes import RECIPES

        for recipe_key, recipe in RECIPES.items():
            known_by = recipe_counts.get(recipe_key, 0)
            unlearned = unlearned_recipe_counts.get(recipe_key, 0)
            skill_key = recipe["skill"].value
            skill_dist = recipe_skill_dist.get(skill_key, {})
            eligible = _players_at_or_above(skill_dist, recipe["min_mastery"].value)
            sat = (known_by + unlearned) / eligible if eligible > 0 else 0.0
            # Prefixed key matches spawn config type_key (recipe_X)
            SaturationSnapshot.objects.update_or_create(
                hour=hour,
                item_key=f"recipe_{recipe_key}",
                category=SaturationSnapshot.CATEGORY_RECIPE,
                defaults={
                    "active_players_7d": active_count,
                    "eligible_players": eligible,
                    "known_by": known_by,
                    "unlearned_copies": unlearned,
                    "in_circulation": 0,
                    "saturation": sat,
                },
            )
            rows_written += 1

        # 6c. NFT item types in circulation (non-scroll, non-recipe)
        for item_name, count in circulation_counts.items():
            SaturationSnapshot.objects.update_or_create(
                hour=hour,
                item_key=item_name,
                category=SaturationSnapshot.CATEGORY_ITEM,
                defaults={
                    "active_players_7d": active_count,
                    "eligible_players": 0,
                    "known_by": 0,
                    "unlearned_copies": 0,
                    "in_circulation": count,
                    "saturation": 0.0,  # needs rarity_divisor config (future)
                },
            )
            rows_written += 1

        logger.info(
            f"NFTSaturation: snapshot for {hour} — "
            f"{active_count} active players, "
            f"{len(spell_counts)} spells known, "
            f"{len(recipe_counts)} recipes known, "
            f"{len(circulation_counts)} item types circulating, "
            f"{rows_written} rows written"
        )

    @staticmethod
    def get_active_player_count_7d():
        """Count distinct active players over the past 7 days.

        Returns:
            (count, character_keys) — integer count and set of
            character_key strings for loading character objects.
        """
        cutoff = timezone.now() - timedelta(days=7)

        char_keys = set(
            PlayerSession.objects.filter(
                Q(ended_at__isnull=True) | Q(ended_at__gte=cutoff),
                started_at__lte=timezone.now(),
            )
            .values_list("character_key", flat=True)
            .distinct()
        )

        return len(char_keys), char_keys

    @staticmethod
    def get_knowledge_counts(active_character_keys):
        """Count how many active players know each spell and recipe
        AND have the mastery to use it.

        Characters who know a spell/recipe but lack the required mastery
        (e.g. after remorting away from a caster class) are excluded.
        This prevents inflating known_by relative to eligible_players,
        which would cause the gap-based spawn algorithm to under-spawn.

        Args:
            active_character_keys: set of character db_key strings

        Returns:
            (spell_counts, recipe_counts) — both defaultdict(int)
            mapping item_key to number of active players who know it
            and have the mastery to cast/craft it.
        """
        from evennia.objects.models import ObjectDB
        from world.recipes import RECIPES
        from world.spells.registry import SPELL_REGISTRY

        spell_counts = defaultdict(int)
        recipe_counts = defaultdict(int)

        if not active_character_keys:
            return spell_counts, recipe_counts

        characters = ObjectDB.objects.filter(
            db_key__in=active_character_keys,
            db_typeclass_path="typeclasses.actors.character.FCMCharacter",
        )

        for char in characters:
            class_levels = char.db.class_skill_mastery_levels or {}

            # Learned spells (permanent) — only count if mastery sufficient
            spellbook = char.db.spellbook or {}
            for key in spellbook:
                spell = SPELL_REGISTRY.get(key)
                if not spell:
                    continue
                entry = class_levels.get(spell.school_key, {})
                char_mastery = (
                    entry.get("mastery", 0) if hasattr(entry, "get") else int(entry)
                )
                if char_mastery >= spell.min_mastery.value:
                    spell_counts[key] += 1

            # Granted spells (class/quest abilities) — same mastery filter
            granted = char.db.granted_spells or {}
            for key in granted:
                if key in spellbook:
                    continue
                spell = SPELL_REGISTRY.get(key)
                if not spell:
                    continue
                entry = class_levels.get(spell.school_key, {})
                char_mastery = (
                    entry.get("mastery", 0) if hasattr(entry, "get") else int(entry)
                )
                if char_mastery >= spell.min_mastery.value:
                    spell_counts[key] += 1

            # Recipes — only count if crafting mastery sufficient
            general_levels = char.db.general_skill_mastery_levels or {}
            recipe_book = char.db.recipe_book or {}
            for key in recipe_book:
                recipe = RECIPES.get(key)
                if not recipe:
                    continue
                skill_key = recipe["skill"].value
                # Enchanting is a class skill; all others are general skills
                if skill_key in class_levels:
                    entry = class_levels.get(skill_key, {})
                    char_mastery = (
                        entry.get("mastery", 0)
                        if hasattr(entry, "get")
                        else int(entry)
                    )
                else:
                    char_mastery = int(general_levels.get(skill_key, 0))
                if char_mastery >= recipe["min_mastery"].value:
                    recipe_counts[key] += 1

        return spell_counts, recipe_counts

    @staticmethod
    def get_unlearned_copy_counts():
        """Count unlearned scroll/recipe NFTs reachable to players.

        Queries NFTGameState for scroll and recipe item types in any
        location a player can retrieve them from — CHARACTER/ACCOUNT
        (already held) plus SPAWNED (sitting in rooms waiting to be
        picked up). Without SPAWNED the spawn loop would re-fire every
        cycle on scrolls it already dropped last cycle, flooding the
        world with duplicates before any player picks one up.

        Returns:
            (scroll_counts, recipe_counts) — both defaultdict(int)
            mapping item_key to count of unlearned copies.
        """
        scroll_counts = defaultdict(int)
        recipe_counts = defaultdict(int)

        reachable_locations = [
            NFTGameState.LOCATION_CHARACTER,
            NFTGameState.LOCATION_ACCOUNT,
            NFTGameState.LOCATION_SPAWNED,
        ]

        # Scroll NFTs reachable to players
        scroll_types = NFTItemType.objects.filter(
            typeclass=SCROLL_TYPECLASS
        )
        if scroll_types.exists():
            scroll_nfts = (
                NFTGameState.objects.filter(
                    location__in=reachable_locations,
                    item_type__in=scroll_types,
                )
                .values("item_type__name")
                .annotate(count=Count("id"))
            )
            for row in scroll_nfts:
                scroll_counts[row["item_type__name"]] += row["count"]

        # Recipe NFTs reachable to players
        recipe_types = NFTItemType.objects.filter(
            typeclass=RECIPE_TYPECLASS
        )
        if recipe_types.exists():
            recipe_nfts = (
                NFTGameState.objects.filter(
                    location__in=reachable_locations,
                    item_type__in=recipe_types,
                )
                .values("item_type__name")
                .annotate(count=Count("id"))
            )
            for row in recipe_nfts:
                recipe_counts[row["item_type__name"]] += row["count"]

        return scroll_counts, recipe_counts

    @staticmethod
    def get_nft_circulation_counts():
        """Count NFTs in circulation per item type.

        Counts NFTs in all player-owned locations: CHARACTER, ACCOUNT,
        SPAWNED, ONCHAIN (private wallet), and AUCTION (listed for sale).
        Only RESERVE is excluded — those items are held by the game system,
        not by any player.

        Scroll and recipe types are excluded here as they are tracked
        separately via knowledge saturation.

        Returns:
            dict mapping item_type name to circulation count.
        """
        excluded_typeclasses = [SCROLL_TYPECLASS, RECIPE_TYPECLASS]

        results = (
            NFTGameState.objects.filter(
                location__in=[
                    NFTGameState.LOCATION_CHARACTER,
                    NFTGameState.LOCATION_ACCOUNT,
                    NFTGameState.LOCATION_SPAWNED,
                    NFTGameState.LOCATION_ONCHAIN,
                    NFTGameState.LOCATION_AUCTION,
                ],
            )
            .exclude(item_type__typeclass__in=excluded_typeclasses)
            .values("item_type__name")
            .annotate(count=Count("id"))
        )

        return {row["item_type__name"]: row["count"] for row in results}

    @staticmethod
    def get_active_players_7d_by_spell_school(active_character_keys):
        """Count active players per spell school per mastery level.

        Iterates active characters and reads db.class_skill_mastery_levels,
        filtering to spell school keys only (excludes combat class skills
        like bash, stealth, etc.).

        Args:
            active_character_keys: set of character db_key strings

        Returns:
            dict: {school_key: {mastery_level: count}}
            e.g. {"evocation": {1: 45, 2: 30, 3: 20, 4: 10, 5: 3}}

            Counts are players at exactly that mastery level.
            To get the denominator for a spell with min_mastery=N,
            sum counts for levels >= N.
        """
        from evennia.objects.models import ObjectDB

        result = defaultdict(lambda: defaultdict(int))

        if not active_character_keys:
            return dict(result)

        characters = ObjectDB.objects.filter(
            db_key__in=active_character_keys,
            db_typeclass_path="typeclasses.actors.character.FCMCharacter",
        )

        for char in characters:
            class_levels = char.db.class_skill_mastery_levels or {}
            for skill_key, entry in class_levels.items():
                if skill_key not in SPELL_SCHOOL_KEYS:
                    continue
                # class_skill_mastery_levels stores {"mastery": int, ...}
                if hasattr(entry, "get"):
                    mastery = entry.get("mastery", 0)
                else:
                    mastery = int(entry)
                if mastery > 0:
                    result[skill_key][mastery] += 1

        # Convert nested defaultdicts to plain dicts
        return {school: dict(levels) for school, levels in result.items()}

    @staticmethod
    def get_active_players_7d_by_recipe_skill(active_character_keys):
        """Count active players per crafting skill per mastery level.

        Checks db.general_skill_mastery_levels for most crafting skills,
        and db.class_skill_mastery_levels for enchanting (a class skill
        that uses the recipe system).

        Args:
            active_character_keys: set of character db_key strings

        Returns:
            dict: {skill_key: {mastery_level: count}}
            e.g. {"blacksmith": {1: 50, 2: 35, 3: 15, 4: 5, 5: 1}}

            Counts are players at exactly that mastery level.
            To get the denominator for a recipe with min_mastery=N,
            sum counts for levels >= N.
        """
        from evennia.objects.models import ObjectDB

        result = defaultdict(lambda: defaultdict(int))

        if not active_character_keys:
            return dict(result)

        characters = ObjectDB.objects.filter(
            db_key__in=active_character_keys,
            db_typeclass_path="typeclasses.actors.character.FCMCharacter",
        )

        for char in characters:
            # General crafting skills (blacksmith, carpenter, etc.)
            general_levels = char.db.general_skill_mastery_levels or {}
            for skill_key, mastery in general_levels.items():
                if skill_key not in CRAFTING_SKILL_KEYS:
                    continue
                mastery = int(mastery)
                if mastery > 0:
                    result[skill_key][mastery] += 1

            # Enchanting is a class skill but uses the recipe system
            class_levels = char.db.class_skill_mastery_levels or {}
            for skill_key, entry in class_levels.items():
                if skill_key not in CRAFTING_SKILL_KEYS:
                    continue
                if hasattr(entry, "get"):
                    mastery = entry.get("mastery", 0)
                else:
                    mastery = int(entry)
                if mastery > 0:
                    result[skill_key][mastery] += 1

        # Convert nested defaultdicts to plain dicts
        return {skill: dict(levels) for skill, levels in result.items()}
