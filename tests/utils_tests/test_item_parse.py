# FullCircleMUD/tests/utils_tests/test_item_parse.py
#
# evennia test --settings settings tests.utils_tests.test_item_parse

from evennia.utils.test_resources import EvenniaTest
from utils.item_parse import parse_item_args, ParsedItem


class TestParseItemArgs(EvenniaTest):
    """Tests for the shared item argument parser."""

    databases = "__all__"

    def create_script(self):
        pass

    # ------------------------------------------------------------------ #
    #  Empty / None input
    # ------------------------------------------------------------------ #

    def test_empty_string_returns_none(self):
        self.assertIsNone(parse_item_args(""))

    def test_whitespace_returns_none(self):
        self.assertIsNone(parse_item_args("   "))

    def test_none_returns_none(self):
        self.assertIsNone(parse_item_args(None))

    # ------------------------------------------------------------------ #
    #  Token ID via #<digits>
    # ------------------------------------------------------------------ #

    def test_hash_token_id(self):
        result = parse_item_args("#7")
        self.assertEqual(result.type, "token_id")
        self.assertEqual(result.token_id, 7)

    def test_hash_token_id_large(self):
        result = parse_item_args("#42")
        self.assertEqual(result.type, "token_id")
        self.assertEqual(result.token_id, 42)

    def test_hash_zero(self):
        result = parse_item_args("#0")
        self.assertEqual(result.type, "token_id")
        self.assertEqual(result.token_id, 0)

    def test_hash_non_digit_is_item(self):
        """#abc is not a valid token ID — treat as item search."""
        result = parse_item_args("#abc")
        self.assertEqual(result.type, "item")
        self.assertEqual(result.search_term, "#abc")

    # ------------------------------------------------------------------ #
    #  Bare number → token ID
    # ------------------------------------------------------------------ #

    def test_bare_number_is_token_id(self):
        result = parse_item_args("7")
        self.assertEqual(result.type, "token_id")
        self.assertEqual(result.token_id, 7)

    def test_bare_zero_is_token_id(self):
        result = parse_item_args("0")
        self.assertEqual(result.type, "token_id")
        self.assertEqual(result.token_id, 0)

    # ------------------------------------------------------------------ #
    #  "all" keyword
    # ------------------------------------------------------------------ #

    def test_all_bare(self):
        result = parse_item_args("all")
        self.assertEqual(result.type, "all")
        self.assertIsNone(result.amount)

    def test_all_gold(self):
        result = parse_item_args("all gold")
        self.assertEqual(result.type, "gold")
        self.assertIsNone(result.amount)  # None = all

    def test_all_resource(self):
        result = parse_item_args("all wheat")
        self.assertEqual(result.type, "resource")
        self.assertIsNone(result.amount)
        self.assertEqual(result.resource_id, 1)

    def test_all_non_fungible_is_item(self):
        """'all sword' → item search for 'sword'."""
        result = parse_item_args("all sword")
        self.assertEqual(result.type, "item")
        self.assertEqual(result.search_term, "sword")

    def test_all_case_insensitive(self):
        result = parse_item_args("ALL GOLD")
        self.assertEqual(result.type, "gold")
        self.assertIsNone(result.amount)

    # ------------------------------------------------------------------ #
    #  Number + fungible (amount-first)
    # ------------------------------------------------------------------ #

    def test_amount_gold(self):
        result = parse_item_args("50 gold")
        self.assertEqual(result.type, "gold")
        self.assertEqual(result.amount, 50)

    def test_amount_resource(self):
        result = parse_item_args("10 wheat")
        self.assertEqual(result.type, "resource")
        self.assertEqual(result.amount, 10)
        self.assertEqual(result.resource_id, 1)

    def test_amount_iron_ore(self):
        result = parse_item_args("5 iron ore")
        self.assertEqual(result.type, "resource")
        self.assertEqual(result.amount, 5)
        self.assertEqual(result.resource_id, 4)

    def test_number_plus_non_fungible_is_item(self):
        """'3 sword' → item search with full string."""
        result = parse_item_args("3 sword")
        self.assertEqual(result.type, "item")
        self.assertEqual(result.search_term, "3 sword")

    # ------------------------------------------------------------------ #
    #  Fungible name only (default amount = 1)
    # ------------------------------------------------------------------ #

    def test_gold_default_amount(self):
        result = parse_item_args("gold")
        self.assertEqual(result.type, "gold")
        self.assertEqual(result.amount, 1)

    def test_resource_default_amount(self):
        result = parse_item_args("bread")
        self.assertEqual(result.type, "resource")
        self.assertEqual(result.amount, 1)
        self.assertEqual(result.resource_id, 3)

    def test_gold_case_insensitive(self):
        result = parse_item_args("Gold")
        self.assertEqual(result.type, "gold")
        self.assertEqual(result.amount, 1)

    def test_resource_case_insensitive(self):
        result = parse_item_args("WHEAT")
        self.assertEqual(result.type, "resource")
        self.assertEqual(result.resource_id, 1)

    # ------------------------------------------------------------------ #
    #  Fungible name + amount (type-first, for backwards compat)
    # ------------------------------------------------------------------ #

    def test_gold_with_trailing_amount(self):
        result = parse_item_args("gold 50")
        self.assertEqual(result.type, "gold")
        self.assertEqual(result.amount, 50)

    def test_gold_with_trailing_all(self):
        result = parse_item_args("gold all")
        self.assertEqual(result.type, "gold")
        self.assertIsNone(result.amount)

    def test_resource_with_trailing_amount(self):
        result = parse_item_args("wheat 10")
        self.assertEqual(result.type, "resource")
        self.assertEqual(result.amount, 10)

    # ------------------------------------------------------------------ #
    #  Item name search (fallthrough)
    # ------------------------------------------------------------------ #

    def test_simple_item_name(self):
        result = parse_item_args("sword")
        self.assertEqual(result.type, "item")
        self.assertEqual(result.search_term, "sword")

    def test_multi_word_item_name(self):
        result = parse_item_args("iron longsword")
        self.assertEqual(result.type, "item")
        self.assertEqual(result.search_term, "iron longsword")

    def test_item_name_with_leading_spaces(self):
        result = parse_item_args("   sword   ")
        self.assertEqual(result.type, "item")
        self.assertEqual(result.search_term, "sword")

    # ------------------------------------------------------------------ #
    #  All resource types work
    # ------------------------------------------------------------------ #

    def test_all_five_resources(self):
        """Verify all seeded resource types are matchable."""
        resources = {
            "wheat": 1,
            "flour": 2,
            "bread": 3,
            "iron ore": 4,
            "iron ingot": 5,
        }
        for name, expected_id in resources.items():
            result = parse_item_args(name)
            self.assertEqual(
                result.type, "resource",
                f"Expected '{name}' to parse as resource"
            )
            self.assertEqual(
                result.resource_id, expected_id,
                f"Expected '{name}' resource_id to be {expected_id}"
            )

    # ------------------------------------------------------------------ #
    #  Namedtuple structure
    # ------------------------------------------------------------------ #

    def test_returns_namedtuple(self):
        result = parse_item_args("sword")
        self.assertIsInstance(result, ParsedItem)
        self.assertIsNone(result.amount)
        self.assertIsNone(result.resource_id)
        self.assertIsNone(result.resource_info)
        self.assertIsNone(result.token_id)
