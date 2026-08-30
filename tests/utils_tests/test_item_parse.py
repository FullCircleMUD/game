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


class TestSplitQuantity(EvenniaTest):
    """Splitting "how many" from "of what".

    Every command that takes a countable argument asks the same
    question first, whatever it goes on to search — inventory, a room,
    a container, a corpse. `get all gold`, `drop 5 wheat` and
    `deposit wheat all` differ in scope, not in shape.

    The helper judges nothing. It does not know what stacks, what the
    caller holds, or whether the command accepts a count at all; it
    reports what was typed and leaves every decision downstream.
    """

    databases = "__all__"

    def create_script(self):
        pass

    def _split(self, args):
        from utils.item_parse import split_quantity
        return split_quantity(args)

    # ── no quantity ───────────────────────────────────────────────

    def test_a_bare_subject(self):
        self.assertEqual(self._split("cap"), (None, "cap"))

    def test_a_multi_word_subject(self):
        self.assertEqual(self._split("leather cap"), (None, "leather cap"))

    def test_empty_input(self):
        self.assertIsNone(self._split(""))

    def test_whitespace_input(self):
        self.assertIsNone(self._split("   "))

    def test_none_input(self):
        self.assertIsNone(self._split(None))

    # ── leading count ─────────────────────────────────────────────

    def test_a_leading_number(self):
        self.assertEqual(self._split("5 wheat"), (5, "wheat"))

    def test_a_leading_number_with_a_dot(self):
        self.assertEqual(self._split("5.wheat"), (5, "wheat"))

    def test_a_leading_number_before_a_multi_word_subject(self):
        self.assertEqual(self._split("2 leather cap"), (2, "leather cap"))

    def test_a_dotted_number_before_a_multi_word_subject(self):
        self.assertEqual(self._split("2.leather cap"), (2, "leather cap"))

    # ── all ───────────────────────────────────────────────────────

    def test_leading_all(self):
        self.assertEqual(self._split("all wheat"), ("all", "wheat"))

    def test_leading_all_with_a_dot(self):
        self.assertEqual(self._split("all.wheat"), ("all", "wheat"))

    def test_all_is_case_insensitive(self):
        self.assertEqual(self._split("ALL wheat"), ("all", "wheat"))

    def test_all_on_its_own_has_no_subject(self):
        self.assertEqual(self._split("all"), ("all", None))

    def test_a_word_merely_starting_with_all_is_a_subject(self):
        self.assertEqual(self._split("allspice"), (None, "allspice"))

    # ── trailing count ────────────────────────────────────────────

    def test_a_trailing_number(self):
        """`deposit gold 50` is in use, so the trailing form is kept."""
        self.assertEqual(self._split("gold 50"), (50, "gold"))

    def test_a_trailing_all(self):
        self.assertEqual(self._split("wheat all"), ("all", "wheat"))

    def test_a_trailing_number_after_a_multi_word_subject(self):
        self.assertEqual(self._split("iron ore 5"), (5, "iron ore"))

    def test_the_cost_of_the_trailing_form(self):
        """A subject genuinely ending in a number is read as a count.

        Nothing in the game is named this way today. Recorded because
        it is the price of supporting `deposit gold 50`, and because a
        future item called "key 3" would be unreachable by name.
        """
        self.assertEqual(self._split("key 3"), (3, "key"))

    # ── things that are not counts ────────────────────────────────

    def test_a_bare_number_is_a_subject(self):
        """Nothing to count — `drop 5` names something, however oddly."""
        self.assertEqual(self._split("5"), (None, "5"))

    def test_a_negative_number_is_part_of_the_subject(self):
        self.assertEqual(self._split("-3 wheat"), (None, "-3 wheat"))

    def test_zero_is_reported_as_typed(self):
        """The helper does not judge. Rejecting zero is the command's job."""
        self.assertEqual(self._split("0 wheat"), (0, "wheat"))

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(self._split("  2   cap  "), (2, "cap"))


class TestSplitQuantity(EvenniaTest):
    """Splitting "how many" from "of what".

    Every command that takes a countable argument asks the same
    question first, whatever it goes on to search — inventory, a room,
    a container, a corpse. `get all gold`, `drop 5 wheat` and
    `deposit all wheat` differ in scope, not in shape.

    **Counts lead.** `5 wheat`, not `wheat 5`. One order everywhere, so
    a player who learns it on one command has learned it on all of
    them. A trailing number is part of the name, which also keeps an
    item called "key 3" reachable.

    The helper judges nothing. It does not know what stacks, what the
    caller holds, or whether the command accepts a count at all; it
    reports what was typed and leaves every decision downstream.
    """

    databases = "__all__"

    def create_script(self):
        pass

    def _split(self, args):
        from utils.item_parse import split_quantity
        return split_quantity(args)

    # ── no count ──────────────────────────────────────────────────

    def test_a_bare_subject(self):
        self.assertEqual(self._split("cap"), (None, "cap"))

    def test_a_multi_word_subject(self):
        self.assertEqual(self._split("leather cap"), (None, "leather cap"))

    def test_empty_input(self):
        self.assertIsNone(self._split(""))

    def test_whitespace_input(self):
        self.assertIsNone(self._split("   "))

    def test_none_input(self):
        self.assertIsNone(self._split(None))

    # ── leading count ─────────────────────────────────────────────

    def test_a_leading_number(self):
        self.assertEqual(self._split("5 wheat"), (5, "wheat"))

    def test_a_leading_number_with_a_dot(self):
        self.assertEqual(self._split("5.wheat"), (5, "wheat"))

    def test_a_leading_number_before_a_multi_word_subject(self):
        self.assertEqual(self._split("2 leather cap"), (2, "leather cap"))

    def test_a_dotted_number_before_a_multi_word_subject(self):
        self.assertEqual(self._split("2.leather cap"), (2, "leather cap"))

    # ── all ───────────────────────────────────────────────────────

    def test_leading_all(self):
        self.assertEqual(self._split("all wheat"), ("all", "wheat"))

    def test_leading_all_with_a_dot(self):
        self.assertEqual(self._split("all.wheat"), ("all", "wheat"))

    def test_all_is_case_insensitive(self):
        self.assertEqual(self._split("ALL wheat"), ("all", "wheat"))

    def test_all_on_its_own_has_no_subject(self):
        self.assertEqual(self._split("all"), ("all", None))

    def test_a_word_merely_starting_with_all_is_a_subject(self):
        self.assertEqual(self._split("allspice"), (None, "allspice"))

    # ── trailing numbers are part of the name ─────────────────────

    def test_a_trailing_number_is_not_a_count(self):
        """Counts lead. `deposit gold 50` is the old order and will be
        refactored to `deposit 50 gold`, not accommodated here."""
        self.assertEqual(self._split("gold 50"), (None, "gold 50"))

    def test_a_trailing_all_is_not_a_count(self):
        self.assertEqual(self._split("wheat all"), (None, "wheat all"))

    def test_an_item_name_ending_in_a_number_survives(self):
        self.assertEqual(self._split("key 3"), (None, "key 3"))

    # ── things that are not counts ────────────────────────────────

    def test_a_bare_number_is_a_subject(self):
        """Nothing to count — `drop 5` names something, however oddly."""
        self.assertEqual(self._split("5"), (None, "5"))

    def test_a_negative_number_is_part_of_the_subject(self):
        self.assertEqual(self._split("-3 wheat"), (None, "-3 wheat"))

    def test_zero_is_reported_as_typed(self):
        """The helper does not judge. Rejecting zero is the command's job."""
        self.assertEqual(self._split("0 wheat"), (0, "wheat"))

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(self._split("  2   cap  "), (2, "cap"))
