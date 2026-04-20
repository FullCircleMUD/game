"""
Tests for direction_parser.parse_direction.

evennia test --settings settings tests.utils_tests.test_direction_parser
"""

from evennia.utils.test_resources import EvenniaTest

from utils.direction_parser import parse_direction


class TestParseDirection(EvenniaTest):

    def create_script(self):
        pass

    def test_direction_after_name(self):
        self.assertEqual(parse_direction("door south"), ("door", "south"))

    def test_direction_before_name(self):
        self.assertEqual(parse_direction("south door"), ("door", "south"))

    def test_abbreviation_after_name(self):
        self.assertEqual(parse_direction("door s"), ("door", "south"))

    def test_abbreviation_before_name(self):
        self.assertEqual(parse_direction("s door"), ("door", "south"))

    def test_direction_only_full(self):
        self.assertEqual(parse_direction("south"), ("", "south"))

    def test_direction_only_abbrev(self):
        self.assertEqual(parse_direction("s"), ("", "south"))

    def test_no_direction(self):
        self.assertEqual(parse_direction("chest"), ("chest", None))

    def test_multi_word_no_direction(self):
        self.assertEqual(parse_direction("iron gate"), ("iron gate", None))

    def test_multi_word_with_direction(self):
        self.assertEqual(parse_direction("iron gate east"), ("iron gate", "east"))

    def test_direction_up(self):
        self.assertEqual(parse_direction("hatch up"), ("hatch", "up"))

    def test_direction_down(self):
        self.assertEqual(parse_direction("d trapdoor"), ("trapdoor", "down"))

    def test_diagonal(self):
        self.assertEqual(parse_direction("door ne"), ("door", "northeast"))

    def test_empty_string(self):
        self.assertEqual(parse_direction(""), ("", None))

    def test_whitespace_only(self):
        self.assertEqual(parse_direction("   "), ("", None))
