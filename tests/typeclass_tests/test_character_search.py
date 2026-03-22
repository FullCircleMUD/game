# FullCircleMUD/tests/typeclass_tests/test_character_search.py
#
# evennia test --settings settings tests.typeclass_tests.test_character_search

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create


def _make_item(key, location=None, aliases=None):
    """Create a plain BaseNFTItem with optional aliases."""
    obj = create.create_object(
        "typeclasses.items.base_nft_item.BaseNFTItem",
        key=key,
        nohome=True,
    )
    if aliases:
        for alias in aliases:
            obj.aliases.add(alias)
    if location:
        obj.move_to(location, quiet=True)
    return obj


class TestCharacterSearch(EvenniaTest):
    """Tests for FCMCharacter.search() substring fallback."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add(
            "wallet_address", "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )
        self.account2.attributes.add(
            "wallet_address", "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
        )

    # ------------------------------------------------------------------ #
    #  Exact match still works (Evennia built-in)
    # ------------------------------------------------------------------ #

    def test_exact_key_match(self):
        """Full key match returns the item."""
        item = _make_item("Iron Longsword", location=self.room1)
        result = self.char1.search("Iron Longsword")
        self.assertEqual(result, item)

    def test_exact_match_case_insensitive(self):
        """Evennia's built-in search is case-insensitive."""
        item = _make_item("Iron Longsword", location=self.room1)
        result = self.char1.search("iron longsword")
        self.assertEqual(result, item)

    # ------------------------------------------------------------------ #
    #  Word-start prefix (Evennia built-in, exact=False)
    # ------------------------------------------------------------------ #

    def test_word_start_prefix(self):
        """'iron' matches 'Iron Longsword' via word-start prefix."""
        item = _make_item("Iron Longsword", location=self.room1)
        result = self.char1.search("iron")
        self.assertEqual(result, item)

    # ------------------------------------------------------------------ #
    #  Substring fallback (our custom override)
    # ------------------------------------------------------------------ #

    def test_substring_in_key(self):
        """'sword' matches 'Iron Longsword' via substring fallback."""
        item = _make_item("Iron Longsword", location=self.room1)
        result = self.char1.search("sword")
        self.assertEqual(result, item)

    def test_substring_case_insensitive(self):
        """Substring matching is case-insensitive."""
        item = _make_item("Iron Longsword", location=self.room1)
        result = self.char1.search("SWORD")
        self.assertEqual(result, item)

    def test_substring_in_alias(self):
        """Substring fallback checks aliases too."""
        item = _make_item("Iron Longsword", location=self.room1, aliases=["blade"])
        result = self.char1.search("lade")
        self.assertEqual(result, item)

    def test_substring_in_inventory(self):
        """Substring matching works for items in caller's inventory."""
        item = _make_item("Iron Longsword", location=self.char1)
        result = self.char1.search("sword")
        self.assertEqual(result, item)

    # ------------------------------------------------------------------ #
    #  Disambiguation (multiple substring matches)
    # ------------------------------------------------------------------ #

    def test_disambiguation_multiple_matches(self):
        """Multiple substring matches return None (quiet=False) with error."""
        _make_item("Iron Longsword", location=self.room1)
        _make_item("Training Longsword", location=self.room1)
        result = self.char1.search("longsword")
        # Evennia's word-start prefix should catch this, but even if
        # it falls through to substring, multiple matches → None
        self.assertIsNone(result)

    # ------------------------------------------------------------------ #
    #  No match
    # ------------------------------------------------------------------ #

    def test_no_match_returns_none(self):
        """No matching item returns None (quiet=False)."""
        _make_item("Iron Longsword", location=self.room1)
        result = self.char1.search("shield")
        self.assertIsNone(result)

    # ------------------------------------------------------------------ #
    #  quiet=True returns list
    # ------------------------------------------------------------------ #

    def test_quiet_returns_list_single(self):
        """quiet=True returns a list even for single match."""
        item = _make_item("Iron Longsword", location=self.room1)
        results = self.char1.search("sword", quiet=True)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], item)

    def test_quiet_returns_empty_list(self):
        """quiet=True returns empty list for no match."""
        _make_item("Iron Longsword", location=self.room1)
        results = self.char1.search("shield", quiet=True)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)

    def test_quiet_returns_list_multiple(self):
        """quiet=True returns list of all matches."""
        _make_item("Iron Longsword", location=self.room1)
        _make_item("Training Longsword", location=self.room1)
        results = self.char1.search("longsword", quiet=True)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)

    # ------------------------------------------------------------------ #
    #  exact=True skips substring fallback
    # ------------------------------------------------------------------ #

    def test_exact_true_skips_substring(self):
        """exact=True defers to Evennia — no substring fallback."""
        _make_item("Iron Longsword", location=self.room1)
        # "sword" is NOT an exact match for "Iron Longsword"
        result = self.char1.search("sword", exact=True)
        self.assertIsNone(result)

    # ------------------------------------------------------------------ #
    #  candidates parameter respected
    # ------------------------------------------------------------------ #

    def test_candidates_parameter(self):
        """Explicitly provided candidates limit the search scope."""
        item_in_room = _make_item("Iron Longsword", location=self.room1)
        item_elsewhere = _make_item("Iron Shield", location=self.room2)
        result = self.char1.search(
            "iron", candidates=[item_elsewhere], quiet=True
        )
        # Only the candidate item should be findable
        self.assertNotIn(item_in_room, result)

    # ------------------------------------------------------------------ #
    #  location parameter respected
    # ------------------------------------------------------------------ #

    def test_location_parameter(self):
        """location parameter scopes the search."""
        _make_item("Iron Longsword", location=self.room1)
        item2 = _make_item("Iron Shield", location=self.char1)
        result = self.char1.search("iron", location=self.char1, quiet=True)
        # Should only find the item in char1's inventory
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], item2)

    # ------------------------------------------------------------------ #
    #  Alias-based match
    # ------------------------------------------------------------------ #

    def test_alias_exact_match(self):
        """Alias exact match works (Evennia built-in)."""
        item = _make_item(
            "Iron Longsword", location=self.room1, aliases=["sword"]
        )
        result = self.char1.search("sword")
        self.assertEqual(result, item)

    def test_alias_substring_match(self):
        """Alias substring match works via our fallback."""
        item = _make_item(
            "Iron Longsword",
            location=self.room1,
            aliases=["greatsword"],
        )
        # "atsw" is a substring of "greatsword" but not word-start
        result = self.char1.search("atsw")
        self.assertEqual(result, item)
