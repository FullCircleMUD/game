"""
Tests for the NFTSaturationService.

Covers:
    - get_active_player_count_7d() session query
    - get_knowledge_counts() spell/recipe knowledge aggregation
    - get_unlearned_copy_counts() NFT scroll/recipe copies
    - get_nft_circulation_counts() NFT circulation by type
    - take_snapshot() integration
"""

from datetime import timedelta

from django.utils import timezone
from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.models import (
    NFTGameState,
    NFTItemType,
    PlayerSession,
    SaturationSnapshot,
)
from blockchain.xrpl.services.nft_saturation import (
    NFTSaturationService,
    SCROLL_TYPECLASS,
    RECIPE_TYPECLASS,
    SPELL_SCHOOL_KEYS,
    CRAFTING_SKILL_KEYS,
)


def _create_session(char_key, hours_ago_start, hours_ago_end=None, account_id=1):
    """Helper to create a PlayerSession."""
    now = timezone.now()
    started = now - timedelta(hours=hours_ago_start)
    ended = (now - timedelta(hours=hours_ago_end)) if hours_ago_end is not None else None
    return PlayerSession.objects.create(
        account_id=account_id,
        character_key=char_key,
        started_at=started,
        ended_at=ended,
    )


def _create_item_type(name, typeclass="typeclasses.items.weapons.longsword.LongswordNFTItem", prototype_key=None):
    """Helper to create an NFTItemType."""
    return NFTItemType.objects.create(
        name=name,
        typeclass=typeclass,
        prototype_key=prototype_key,
        description=f"Test {name}",
    )


def _create_nft(item_type, location, token_id, owner="rTestWallet123", char_key=None):
    """Helper to create an NFTGameState row."""
    return NFTGameState.objects.create(
        nftoken_id=token_id,
        taxon=1,
        owner_in_game=None if location == NFTGameState.LOCATION_ONCHAIN else owner,
        location=location,
        character_key=char_key if location == NFTGameState.LOCATION_CHARACTER else None,
        item_type=item_type,
    )


# ─── Active Player Count ────────────────────────────────────────────


class TestGetActivePlayerCount7d(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_no_sessions_returns_zero(self):
        count, keys = NFTSaturationService.get_active_player_count_7d()
        self.assertEqual(count, 0)
        self.assertEqual(keys, set())

    def test_one_recent_session(self):
        _create_session("Alice", hours_ago_start=2, hours_ago_end=1)
        count, keys = NFTSaturationService.get_active_player_count_7d()
        self.assertEqual(count, 1)
        self.assertIn("Alice", keys)

    def test_multiple_sessions_same_character_counted_once(self):
        _create_session("Alice", hours_ago_start=10, hours_ago_end=8, account_id=1)
        _create_session("Alice", hours_ago_start=5, hours_ago_end=3, account_id=1)
        count, keys = NFTSaturationService.get_active_player_count_7d()
        self.assertEqual(count, 1)

    def test_old_session_excluded(self):
        _create_session("Alice", hours_ago_start=200, hours_ago_end=199, account_id=1)
        count, keys = NFTSaturationService.get_active_player_count_7d()
        self.assertEqual(count, 0)

    def test_open_session_counts(self):
        _create_session("Alice", hours_ago_start=1, hours_ago_end=None)
        count, keys = NFTSaturationService.get_active_player_count_7d()
        self.assertEqual(count, 1)
        self.assertIn("Alice", keys)

    def test_two_different_characters(self):
        _create_session("Alice", hours_ago_start=2, hours_ago_end=1, account_id=1)
        _create_session("Bob", hours_ago_start=3, hours_ago_end=2, account_id=2)
        count, keys = NFTSaturationService.get_active_player_count_7d()
        self.assertEqual(count, 2)
        self.assertIn("Alice", keys)
        self.assertIn("Bob", keys)


# ─── Knowledge Counts ───────────────────────────────────────────────


class TestGetKnowledgeCounts(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_empty_keys_returns_empty(self):
        spell_counts, recipe_counts = NFTSaturationService.get_knowledge_counts(set())
        self.assertEqual(len(spell_counts), 0)
        self.assertEqual(len(recipe_counts), 0)

    def test_character_with_spells(self):
        self.char1.db.spellbook = {"magic_missile": True, "shield": True}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {}
        # magic_missile=evocation/BASIC, shield=abjuration/BASIC
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 1, "classes": ["mage"]},
            "abjuration": {"mastery": 1, "classes": ["mage"]},
        }

        spell_counts, recipe_counts = NFTSaturationService.get_knowledge_counts(
            {self.char1.key}
        )
        self.assertEqual(spell_counts["magic_missile"], 1)
        self.assertEqual(spell_counts["shield"], 1)
        self.assertEqual(len(recipe_counts), 0)

    def test_character_with_recipes(self):
        self.char1.db.spellbook = {}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {"training_longsword": True}
        # training_longsword=carpenter/BASIC
        self.char1.db.general_skill_mastery_levels = {"carpenter": 1}

        spell_counts, recipe_counts = NFTSaturationService.get_knowledge_counts(
            {self.char1.key}
        )
        self.assertEqual(len(spell_counts), 0)
        self.assertEqual(recipe_counts["training_longsword"], 1)

    def test_granted_spells_counted(self):
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.granted_spells = {"cure_wounds": True}
        self.char1.db.recipe_book = {}
        # magic_missile=evocation/BASIC, cure_wounds=divine_healing/BASIC
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 1, "classes": ["mage"]},
            "divine_healing": {"mastery": 1, "classes": ["cleric"]},
        }

        spell_counts, _ = NFTSaturationService.get_knowledge_counts(
            {self.char1.key}
        )
        self.assertEqual(spell_counts["magic_missile"], 1)
        self.assertEqual(spell_counts["cure_wounds"], 1)

    def test_granted_spell_not_double_counted(self):
        """If spell is in both spellbook and granted, count once."""
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.granted_spells = {"magic_missile": True}
        self.char1.db.recipe_book = {}
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 1, "classes": ["mage"]},
        }

        spell_counts, _ = NFTSaturationService.get_knowledge_counts(
            {self.char1.key}
        )
        self.assertEqual(spell_counts["magic_missile"], 1)

    def test_two_characters_same_spell(self):
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {}
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 1, "classes": ["mage"]},
        }
        self.char2.db.spellbook = {"magic_missile": True, "fireball": True}
        self.char2.db.granted_spells = {}
        self.char2.db.recipe_book = {}
        # fireball=evocation/EXPERT (3), so char2 needs mastery >= 3
        self.char2.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 3, "classes": ["mage"]},
        }

        spell_counts, _ = NFTSaturationService.get_knowledge_counts(
            {self.char1.key, self.char2.key}
        )
        self.assertEqual(spell_counts["magic_missile"], 2)
        self.assertEqual(spell_counts["fireball"], 1)

    def test_nonexistent_character_key_ignored(self):
        """Character key that doesn't match any ObjectDB row is silently skipped."""
        spell_counts, recipe_counts = NFTSaturationService.get_knowledge_counts(
            {"nonexistent_char"}
        )
        self.assertEqual(len(spell_counts), 0)
        self.assertEqual(len(recipe_counts), 0)

    def test_spell_not_counted_without_mastery(self):
        """Character with spell in spellbook but no school mastery (e.g. remorted
        to warrior) should not be counted in known_by."""
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {}
        # No class_skill_mastery_levels — remorted away from mage
        self.char1.db.class_skill_mastery_levels = {}

        spell_counts, _ = NFTSaturationService.get_knowledge_counts(
            {self.char1.key}
        )
        self.assertEqual(spell_counts.get("magic_missile", 0), 0)

    def test_spell_not_counted_with_insufficient_mastery(self):
        """Character with mastery below spell requirement is not counted.
        fireball requires EXPERT (3) — BASIC (1) is not enough."""
        self.char1.db.spellbook = {"fireball": True}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {}
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 1, "classes": ["mage"]},
        }

        spell_counts, _ = NFTSaturationService.get_knowledge_counts(
            {self.char1.key}
        )
        self.assertEqual(spell_counts.get("fireball", 0), 0)

    def test_granted_spell_not_counted_without_mastery(self):
        """Granted spells also require mastery to be counted."""
        self.char1.db.spellbook = {}
        self.char1.db.granted_spells = {"cure_wounds": True}
        self.char1.db.recipe_book = {}
        # No divine_healing mastery
        self.char1.db.class_skill_mastery_levels = {}

        spell_counts, _ = NFTSaturationService.get_knowledge_counts(
            {self.char1.key}
        )
        self.assertEqual(spell_counts.get("cure_wounds", 0), 0)

    def test_recipe_not_counted_without_mastery(self):
        """Character with recipe in book but no crafting mastery is not counted."""
        self.char1.db.spellbook = {}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {"training_longsword": True}
        # No carpenter mastery
        self.char1.db.general_skill_mastery_levels = {}

        _, recipe_counts = NFTSaturationService.get_knowledge_counts(
            {self.char1.key}
        )
        self.assertEqual(recipe_counts.get("training_longsword", 0), 0)

    def test_remorted_character_mixed_mastery(self):
        """Character knows spells from two schools but only has mastery in one.
        Only the spell they have mastery for should be counted."""
        self.char1.db.spellbook = {"magic_missile": True, "shield": True}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {}
        # Has evocation but not abjuration (remorted to a class without abjuration)
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 1, "classes": ["mage"]},
        }

        spell_counts, _ = NFTSaturationService.get_knowledge_counts(
            {self.char1.key}
        )
        self.assertEqual(spell_counts["magic_missile"], 1)
        self.assertEqual(spell_counts.get("shield", 0), 0)


# ─── Unlearned Copy Counts ──────────────────────────────────────────


class TestGetUnlearnedCopyCounts(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_no_scroll_nfts_returns_empty(self):
        scroll_counts, recipe_counts = NFTSaturationService.get_unlearned_copy_counts()
        self.assertEqual(len(scroll_counts), 0)
        self.assertEqual(len(recipe_counts), 0)

    def test_scroll_in_character_hands_counted(self):
        scroll_type = _create_item_type(
            "Test Fire Scroll ZZZ", SCROLL_TYPECLASS, prototype_key="test_fire_scroll"
        )
        _create_nft(scroll_type, NFTGameState.LOCATION_CHARACTER, "token_100", char_key="Alice")
        _create_nft(scroll_type, NFTGameState.LOCATION_CHARACTER, "token_101", char_key="Bob")

        scroll_counts, _ = NFTSaturationService.get_unlearned_copy_counts()
        self.assertEqual(scroll_counts["test_fire"], 2)

    def test_scroll_in_account_counted(self):
        scroll_type = _create_item_type(
            "Test Ice Scroll ZZZ", SCROLL_TYPECLASS, prototype_key="test_ice_scroll"
        )
        _create_nft(scroll_type, NFTGameState.LOCATION_ACCOUNT, "token_102")

        scroll_counts, _ = NFTSaturationService.get_unlearned_copy_counts()
        self.assertEqual(scroll_counts["test_ice"], 1)

    def test_scroll_spawned_in_world_counted(self):
        """Scrolls sitting in rooms must count as unlearned copies.

        Regression: without this, the spawn loop re-fires every cycle on
        scrolls it already dropped last cycle, flooding the world until
        a player finally picks one up.
        """
        scroll_type = _create_item_type(
            "Test Fire Scroll ZZZ", SCROLL_TYPECLASS, prototype_key="test_fire_scroll"
        )
        _create_nft(scroll_type, NFTGameState.LOCATION_SPAWNED, "token_spawn_1")
        _create_nft(scroll_type, NFTGameState.LOCATION_SPAWNED, "token_spawn_2")

        scroll_counts, _ = NFTSaturationService.get_unlearned_copy_counts()
        self.assertEqual(scroll_counts["test_fire"], 2)

    def test_recipe_spawned_in_world_counted(self):
        """Recipes sitting in rooms must count as unlearned copies."""
        recipe_type = _create_item_type(
            "Test Recipe ZZZ", RECIPE_TYPECLASS, prototype_key="test_recipe"
        )
        _create_nft(recipe_type, NFTGameState.LOCATION_SPAWNED, "token_spawn_3")

        _, recipe_counts = NFTSaturationService.get_unlearned_copy_counts()
        self.assertEqual(recipe_counts["test"], 1)

    def test_scroll_in_reserve_excluded(self):
        scroll_type = _create_item_type(
            "Test Fire Scroll ZZZ", SCROLL_TYPECLASS, prototype_key="test_fire_scroll"
        )
        _create_nft(scroll_type, NFTGameState.LOCATION_RESERVE, "token_103")

        scroll_counts, _ = NFTSaturationService.get_unlearned_copy_counts()
        self.assertEqual(len(scroll_counts), 0)

    def test_scroll_onchain_excluded(self):
        scroll_type = _create_item_type(
            "Test Fire Scroll ZZZ", SCROLL_TYPECLASS, prototype_key="test_fire_scroll"
        )
        _create_nft(scroll_type, NFTGameState.LOCATION_ONCHAIN, "token_104")

        scroll_counts, _ = NFTSaturationService.get_unlearned_copy_counts()
        self.assertEqual(len(scroll_counts), 0)

    def test_recipe_in_character_hands_counted(self):
        recipe_type = _create_item_type(
            "Test Recipe ZZZ", RECIPE_TYPECLASS, prototype_key="test_recipe"
        )
        _create_nft(recipe_type, NFTGameState.LOCATION_CHARACTER, "token_105", char_key="Alice")

        _, recipe_counts = NFTSaturationService.get_unlearned_copy_counts()
        self.assertEqual(recipe_counts["test"], 1)

    def test_scroll_without_prototype_key_ignored(self):
        """Scroll NFTItemType with no prototype_key should be skipped.

        Defensive: legacy/malformed rows without the "{key}_scroll" suffix
        are silently ignored instead of polluting the counter.
        """
        scroll_type = _create_item_type(
            "Legacy Scroll", SCROLL_TYPECLASS, prototype_key=None
        )
        _create_nft(scroll_type, NFTGameState.LOCATION_SPAWNED, "token_legacy")

        scroll_counts, _ = NFTSaturationService.get_unlearned_copy_counts()
        self.assertEqual(len(scroll_counts), 0)


# ─── NFT Circulation Counts ─────────────────────────────────────────


class TestGetNftCirculationCounts(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_no_nfts_returns_empty(self):
        counts = NFTSaturationService.get_nft_circulation_counts()
        self.assertEqual(len(counts), 0)

    def test_nfts_in_character_counted(self):
        sword_type = _create_item_type("Test Sword ZZZ")
        _create_nft(sword_type, NFTGameState.LOCATION_CHARACTER, "token_200", char_key="Alice")
        _create_nft(sword_type, NFTGameState.LOCATION_CHARACTER, "token_201", char_key="Bob")

        counts = NFTSaturationService.get_nft_circulation_counts()
        self.assertEqual(counts["Test Sword ZZZ"], 2)

    def test_nfts_in_account_counted(self):
        sword_type = _create_item_type("Test Sword ZZZ")
        _create_nft(sword_type, NFTGameState.LOCATION_ACCOUNT, "token_202")

        counts = NFTSaturationService.get_nft_circulation_counts()
        self.assertEqual(counts["Test Sword ZZZ"], 1)

    def test_nfts_in_spawned_counted(self):
        sword_type = _create_item_type("Test Sword ZZZ")
        _create_nft(sword_type, NFTGameState.LOCATION_SPAWNED, "token_203")

        counts = NFTSaturationService.get_nft_circulation_counts()
        self.assertEqual(counts["Test Sword ZZZ"], 1)

    def test_nfts_in_reserve_excluded(self):
        sword_type = _create_item_type("Test Sword ZZZ")
        _create_nft(sword_type, NFTGameState.LOCATION_RESERVE, "token_204")

        counts = NFTSaturationService.get_nft_circulation_counts()
        self.assertEqual(len(counts), 0)

    def test_nfts_onchain_counted(self):
        sword_type = _create_item_type("Test Sword ZZZ")
        _create_nft(sword_type, NFTGameState.LOCATION_ONCHAIN, "token_205")

        counts = NFTSaturationService.get_nft_circulation_counts()
        self.assertEqual(counts["Test Sword ZZZ"], 1)

    def test_nfts_in_auction_counted(self):
        sword_type = _create_item_type("Test Sword ZZZ")
        _create_nft(sword_type, NFTGameState.LOCATION_AUCTION, "token_205b")

        counts = NFTSaturationService.get_nft_circulation_counts()
        self.assertEqual(counts["Test Sword ZZZ"], 1)

    def test_scroll_nfts_excluded(self):
        """Scroll NFTs are tracked via knowledge saturation, not circulation."""
        scroll_type = _create_item_type("Test Fire Scroll ZZZ", SCROLL_TYPECLASS)
        _create_nft(scroll_type, NFTGameState.LOCATION_CHARACTER, "token_206", char_key="Alice")

        counts = NFTSaturationService.get_nft_circulation_counts()
        self.assertEqual(len(counts), 0)

    def test_recipe_nfts_excluded(self):
        """Recipe NFTs are tracked via knowledge saturation, not circulation."""
        recipe_type = _create_item_type("Test Recipe ZZZ", RECIPE_TYPECLASS)
        _create_nft(recipe_type, NFTGameState.LOCATION_CHARACTER, "token_207", char_key="Alice")

        counts = NFTSaturationService.get_nft_circulation_counts()
        self.assertEqual(len(counts), 0)

    def test_multiple_item_types_grouped(self):
        sword_type = _create_item_type("Test Sword ZZZ")
        shield_type = _create_item_type("Test Shield ZZZ")
        _create_nft(sword_type, NFTGameState.LOCATION_CHARACTER, "token_208", char_key="Alice")
        _create_nft(sword_type, NFTGameState.LOCATION_CHARACTER, "token_209", char_key="Bob")
        _create_nft(shield_type, NFTGameState.LOCATION_CHARACTER, "token_210", char_key="Alice")

        counts = NFTSaturationService.get_nft_circulation_counts()
        self.assertEqual(counts["Test Sword ZZZ"], 2)
        self.assertEqual(counts["Test Shield ZZZ"], 1)


# ─── Integration: take_snapshot ────────────────────────────────


class TestTakeDailySnapshot(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_no_active_players_skips(self):
        """No active players → no snapshot rows written."""
        NFTSaturationService.take_snapshot()
        self.assertEqual(SaturationSnapshot.objects.count(), 0)

    def test_writes_spell_snapshot_rows(self):
        """Active player with spells and mastery → correct saturation."""
        _create_session(self.char1.key, hours_ago_start=2, hours_ago_end=1)
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {}
        # magic_missile is evocation/BASIC — set mastery for denominator
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 1, "classes": ["mage"]},
        }

        NFTSaturationService.take_snapshot()

        spell_rows = SaturationSnapshot.objects.filter(
            category=SaturationSnapshot.CATEGORY_SPELL
        )
        mm_row = spell_rows.filter(item_key="magic_missile").first()
        if mm_row:
            self.assertEqual(mm_row.known_by, 1)
            self.assertEqual(mm_row.active_players_7d, 1)
            self.assertEqual(mm_row.eligible_players, 1)
            self.assertAlmostEqual(mm_row.saturation, 1.0)

    def test_writes_recipe_snapshot_rows(self):
        """Active player with recipes and mastery → correct saturation."""
        _create_session(self.char1.key, hours_ago_start=2, hours_ago_end=1)
        self.char1.db.spellbook = {}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {"training_longsword": True}
        # training_longsword is carpenter/BASIC — set mastery for denominator
        self.char1.db.general_skill_mastery_levels = {"carpenter": 1}

        NFTSaturationService.take_snapshot()

        recipe_rows = SaturationSnapshot.objects.filter(
            category=SaturationSnapshot.CATEGORY_RECIPE
        )
        tl_row = recipe_rows.filter(item_key="training_longsword").first()
        if tl_row:
            self.assertEqual(tl_row.known_by, 1)
            self.assertEqual(tl_row.eligible_players, 1)
            self.assertAlmostEqual(tl_row.saturation, 1.0)

    def test_writes_circulation_snapshot_rows(self):
        """NFTs in circulation → snapshot rows."""
        _create_session(self.char1.key, hours_ago_start=2, hours_ago_end=1)
        self.char1.db.spellbook = {}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {}

        sword_type = _create_item_type("Test Sword ZZZ")
        _create_nft(sword_type, NFTGameState.LOCATION_CHARACTER, "token_300", char_key="Alice")
        _create_nft(sword_type, NFTGameState.LOCATION_CHARACTER, "token_301", char_key="Bob")

        NFTSaturationService.take_snapshot()

        item_row = SaturationSnapshot.objects.filter(
            category=SaturationSnapshot.CATEGORY_ITEM,
            item_key="Test Sword ZZZ",
        ).first()
        self.assertIsNotNone(item_row)
        self.assertEqual(item_row.in_circulation, 2)

    def test_second_call_updates_existing(self):
        """Running twice in the same hour updates rows (upsert)."""
        _create_session(self.char1.key, hours_ago_start=2, hours_ago_end=1)
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {}

        NFTSaturationService.take_snapshot()
        first_count = SaturationSnapshot.objects.count()

        # Add another spell and re-run
        self.char1.db.spellbook = {"magic_missile": True, "shield": True}
        NFTSaturationService.take_snapshot()

        # Row count should not double — update_or_create handles upsert
        self.assertEqual(SaturationSnapshot.objects.count(), first_count)

    def test_unlearned_copies_included_in_saturation(self):
        """Unlearned scroll copies add to saturation score.

        Regression: the snapshot's unlearned_copies must reflect real
        spawned/held NFTs. Without this, the gap-based spawn calculator
        fires full demand every hour, duplicating scrolls in the world.
        """
        _create_session(self.char1.key, hours_ago_start=2, hours_ago_end=1)
        self.char1.db.spellbook = {}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {}

        from world.spells.registry import SPELL_REGISTRY
        self.assertTrue(SPELL_REGISTRY, "SPELL_REGISTRY must not be empty for this test")

        first_spell_key = next(iter(SPELL_REGISTRY))
        spell = SPELL_REGISTRY[first_spell_key]
        # Set mastery so this char is eligible for the spell
        self.char1.db.class_skill_mastery_levels = {
            spell.school_key: {"mastery": spell.min_mastery.value, "classes": ["mage"]},
        }
        scroll_type = _create_item_type(
            f"Scroll of {first_spell_key}",
            SCROLL_TYPECLASS,
            prototype_key=f"{first_spell_key}_scroll",
        )
        _create_nft(scroll_type, NFTGameState.LOCATION_CHARACTER, "token_302", char_key="Alice")

        NFTSaturationService.take_snapshot()

        row = SaturationSnapshot.objects.get(
            category=SaturationSnapshot.CATEGORY_SPELL,
            item_key=f"scroll_{first_spell_key}",
        )
        self.assertEqual(row.known_by, 0)
        self.assertEqual(row.unlearned_copies, 1)
        self.assertEqual(row.eligible_players, 1)
        self.assertAlmostEqual(row.saturation, 1.0)

    def test_spawned_scroll_reduces_gap_next_snapshot(self):
        """A scroll at LOCATION_SPAWNED must count toward unlearned_copies.

        This is the exact scenario that was silently broken: the snapshot
        must see scrolls sitting in the world (not just in player hands)
        so the next spawn tick's gap = eligible - known - unlearned = 0.
        """
        _create_session(self.char1.key, hours_ago_start=2, hours_ago_end=1)
        self.char1.db.spellbook = {}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {}

        from world.spells.registry import SPELL_REGISTRY
        self.assertTrue(SPELL_REGISTRY, "SPELL_REGISTRY must not be empty for this test")

        first_spell_key = next(iter(SPELL_REGISTRY))
        spell = SPELL_REGISTRY[first_spell_key]
        self.char1.db.class_skill_mastery_levels = {
            spell.school_key: {"mastery": spell.min_mastery.value, "classes": ["mage"]},
        }
        scroll_type = _create_item_type(
            f"Scroll of {first_spell_key}",
            SCROLL_TYPECLASS,
            prototype_key=f"{first_spell_key}_scroll",
        )
        # Two scrolls sitting in the world, nobody holding them yet
        _create_nft(scroll_type, NFTGameState.LOCATION_SPAWNED, "token_spawned_1")
        _create_nft(scroll_type, NFTGameState.LOCATION_SPAWNED, "token_spawned_2")

        NFTSaturationService.take_snapshot()

        row = SaturationSnapshot.objects.get(
            category=SaturationSnapshot.CATEGORY_SPELL,
            item_key=f"scroll_{first_spell_key}",
        )
        self.assertEqual(row.unlearned_copies, 2)

    def test_no_eligible_players_saturation_zero(self):
        """Spell with no eligible players → saturation 0.0."""
        _create_session(self.char1.key, hours_ago_start=2, hours_ago_end=1)
        self.char1.db.spellbook = {}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {}
        # No mastery set — char is not eligible for any spells

        NFTSaturationService.take_snapshot()

        # All spell rows should have eligible_players=0, saturation=0.0
        mm_row = SaturationSnapshot.objects.filter(
            category=SaturationSnapshot.CATEGORY_SPELL,
            item_key="magic_missile",
        ).first()
        if mm_row:
            self.assertEqual(mm_row.eligible_players, 0)
            self.assertAlmostEqual(mm_row.saturation, 0.0)

    def test_mastery_aware_denominator_spell(self):
        """Saturation denominator uses eligible players, not total."""
        _create_session(self.char1.key, hours_ago_start=2, hours_ago_end=1)
        _create_session(self.char2.key, hours_ago_start=3, hours_ago_end=2)
        # char1 has evocation 3 and knows magic_missile
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {}
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 3, "classes": ["mage"]},
        }
        # char2 has NO evocation — not eligible
        self.char2.db.spellbook = {}
        self.char2.db.granted_spells = {}
        self.char2.db.recipe_book = {}

        NFTSaturationService.take_snapshot()

        mm_row = SaturationSnapshot.objects.filter(
            category=SaturationSnapshot.CATEGORY_SPELL,
            item_key="magic_missile",
        ).first()
        if mm_row:
            self.assertEqual(mm_row.active_players_7d, 2)
            self.assertEqual(mm_row.eligible_players, 1)  # only char1
            self.assertEqual(mm_row.known_by, 1)
            self.assertAlmostEqual(mm_row.saturation, 1.0)  # 1/1


# ─── Active Players by Spell School ───────────────────────────────


class TestGetActivePlayers7dBySpellSchool(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_empty_keys_returns_empty(self):
        result = NFTSaturationService.get_active_players_7d_by_spell_school(set())
        self.assertEqual(result, {})

    def test_character_with_evocation(self):
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 3, "classes": ["mage"]},
        }
        result = NFTSaturationService.get_active_players_7d_by_spell_school(
            {self.char1.key}
        )
        self.assertEqual(result, {"evocation": {3: 1}})

    def test_two_characters_different_levels(self):
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 2, "classes": ["mage"]},
        }
        self.char2.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 4, "classes": ["mage"]},
        }
        result = NFTSaturationService.get_active_players_7d_by_spell_school(
            {self.char1.key, self.char2.key}
        )
        self.assertEqual(result, {"evocation": {2: 1, 4: 1}})

    def test_two_characters_same_level(self):
        self.char1.db.class_skill_mastery_levels = {
            "necromancy": {"mastery": 1, "classes": ["mage"]},
        }
        self.char2.db.class_skill_mastery_levels = {
            "necromancy": {"mastery": 1, "classes": ["mage"]},
        }
        result = NFTSaturationService.get_active_players_7d_by_spell_school(
            {self.char1.key, self.char2.key}
        )
        self.assertEqual(result, {"necromancy": {1: 2}})

    def test_multiple_schools_on_one_character(self):
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 3, "classes": ["mage"]},
            "abjuration": {"mastery": 1, "classes": ["mage"]},
            "divine_healing": {"mastery": 2, "classes": ["cleric"]},
        }
        result = NFTSaturationService.get_active_players_7d_by_spell_school(
            {self.char1.key}
        )
        self.assertEqual(result["evocation"], {3: 1})
        self.assertEqual(result["abjuration"], {1: 1})
        self.assertEqual(result["divine_healing"], {2: 1})

    def test_non_spell_school_class_skills_excluded(self):
        """Combat class skills like bash, stealth should not appear."""
        self.char1.db.class_skill_mastery_levels = {
            "bash": {"mastery": 3, "classes": ["warrior"]},
            "stealth": {"mastery": 2, "classes": ["thief"]},
            "evocation": {"mastery": 1, "classes": ["mage"]},
        }
        result = NFTSaturationService.get_active_players_7d_by_spell_school(
            {self.char1.key}
        )
        self.assertNotIn("bash", result)
        self.assertNotIn("stealth", result)
        self.assertIn("evocation", result)

    def test_zero_mastery_excluded(self):
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 0, "classes": ["mage"]},
        }
        result = NFTSaturationService.get_active_players_7d_by_spell_school(
            {self.char1.key}
        )
        self.assertEqual(result, {})

    def test_no_class_skill_mastery_levels(self):
        self.char1.db.class_skill_mastery_levels = None
        result = NFTSaturationService.get_active_players_7d_by_spell_school(
            {self.char1.key}
        )
        self.assertEqual(result, {})

    def test_enchanting_excluded_from_spell_schools(self):
        """Enchanting is a crafting skill, not a spell school."""
        self.char1.db.class_skill_mastery_levels = {
            "enchanting": {"mastery": 2, "classes": ["mage"]},
        }
        result = NFTSaturationService.get_active_players_7d_by_spell_school(
            {self.char1.key}
        )
        self.assertNotIn("enchanting", result)


# ─── Active Players by Recipe Skill ───────────────────────────────


class TestGetActivePlayers7dByRecipeSkill(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_empty_keys_returns_empty(self):
        result = NFTSaturationService.get_active_players_7d_by_recipe_skill(set())
        self.assertEqual(result, {})

    def test_character_with_blacksmith(self):
        self.char1.db.general_skill_mastery_levels = {"blacksmith": 2}
        result = NFTSaturationService.get_active_players_7d_by_recipe_skill(
            {self.char1.key}
        )
        self.assertEqual(result, {"blacksmith": {2: 1}})

    def test_two_characters_same_skill_same_level(self):
        self.char1.db.general_skill_mastery_levels = {"blacksmith": 2}
        self.char2.db.general_skill_mastery_levels = {"blacksmith": 2}
        result = NFTSaturationService.get_active_players_7d_by_recipe_skill(
            {self.char1.key, self.char2.key}
        )
        self.assertEqual(result, {"blacksmith": {2: 2}})

    def test_two_characters_same_skill_different_levels(self):
        self.char1.db.general_skill_mastery_levels = {"carpenter": 1}
        self.char2.db.general_skill_mastery_levels = {"carpenter": 3}
        result = NFTSaturationService.get_active_players_7d_by_recipe_skill(
            {self.char1.key, self.char2.key}
        )
        self.assertEqual(result, {"carpenter": {1: 1, 3: 1}})

    def test_multiple_crafting_skills(self):
        self.char1.db.general_skill_mastery_levels = {
            "blacksmith": 3,
            "leatherworker": 1,
        }
        result = NFTSaturationService.get_active_players_7d_by_recipe_skill(
            {self.char1.key}
        )
        self.assertEqual(result["blacksmith"], {3: 1})
        self.assertEqual(result["leatherworker"], {1: 1})

    def test_non_crafting_general_skills_excluded(self):
        """Combat/exploration general skills should not appear."""
        self.char1.db.general_skill_mastery_levels = {
            "battleskills": 3,
            "alertness": 2,
            "blacksmith": 1,
        }
        result = NFTSaturationService.get_active_players_7d_by_recipe_skill(
            {self.char1.key}
        )
        self.assertNotIn("battleskills", result)
        self.assertNotIn("alertness", result)
        self.assertIn("blacksmith", result)

    def test_zero_mastery_excluded(self):
        self.char1.db.general_skill_mastery_levels = {"blacksmith": 0}
        result = NFTSaturationService.get_active_players_7d_by_recipe_skill(
            {self.char1.key}
        )
        self.assertEqual(result, {})

    def test_no_general_skill_mastery_levels(self):
        self.char1.db.general_skill_mastery_levels = None
        result = NFTSaturationService.get_active_players_7d_by_recipe_skill(
            {self.char1.key}
        )
        self.assertEqual(result, {})

    def test_enchanting_from_class_skills(self):
        """Enchanting is stored in class_skill_mastery_levels but treated as crafting."""
        self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.class_skill_mastery_levels = {
            "enchanting": {"mastery": 2, "classes": ["mage"]},
        }
        result = NFTSaturationService.get_active_players_7d_by_recipe_skill(
            {self.char1.key}
        )
        self.assertEqual(result, {"enchanting": {2: 1}})
