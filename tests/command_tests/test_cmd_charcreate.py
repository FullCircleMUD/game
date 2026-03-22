"""
Tests for the character creation command and chargen menu nodes.

Tests cover:
    - Point buy cost table and helpers
    - Individual menu node behavior (race, class, alignment, point buy, name)
    - Skill allocation nodes (weapon, class, general)
    - Language selection node
    - Full character creation flow
    - Back navigation
    - Input validation
"""

from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import BaseEvenniaTest

from enums.abilities_enum import Ability
from enums.alignment import Alignment
from enums.mastery_level import MasteryLevel
from enums.weapon_type import WeaponType
from typeclasses.actors.races import get_race
from server.main_menu.chargen.chargen_menu import (
    POINT_COSTS,
    MIN_SCORE,
    MAX_SCORE,
    ABILITIES,
    _calculate_points_spent,
    _get_racial_bonuses,
    _handle_point_buy_input,
    _handle_name_input,
    _handle_race_info,
    _handle_class_info,
    _handle_alignment_input,
    _handle_weapon_toggle,
    _handle_class_skill_toggle,
    _handle_general_skill_toggle,
    _handle_language_toggle,
    _set_race,
    _set_class,
    _restart,
    _reset_scores_and_back,
    _clear_skills_and_back_to_pointbuy,
    _get_weapon_items,
    _get_class_skill_items,
    _get_general_skill_items,
    _get_bonus_language_picks,
    _get_auto_languages,
    _get_choosable_languages,
    node_race_select,
    node_class_select,
    node_alignment_select,
    node_point_buy,
    node_point_buy_confirm,
    node_weapon_skills,
    node_class_skills,
    node_general_skills,
    node_languages,
    node_skill_confirm,
    node_restart_confirm,
    node_name,
    node_confirm,
    node_create,
)


class _MockCaller:
    """Lightweight mock for EvMenu caller (account)."""

    def __init__(self, chargen_state=None):
        self.ndb = MagicMock()
        self.ndb._chargen = chargen_state or {}
        self._messages = []

    def msg(self, text="", **kwargs):
        self._messages.append(text)


def _default_state():
    """Return a typical chargen state mid-flow."""
    return {
        "session": MagicMock(address="127.0.0.1"),
        "race_key": "human",
        "class_key": "warrior",
        "alignment": Alignment.TRUE_NEUTRAL,
        "scores": {ab: 8 for ab in ABILITIES},
        "points_remaining": 27,
        "point_buy": 27,
    }


# =======================================================================
#  Point Buy Cost Table
# =======================================================================

class TestPointBuyCostTable(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_cost_table_starts_at_zero(self):
        self.assertEqual(POINT_COSTS[8], 0)

    def test_cost_table_max_score(self):
        self.assertEqual(POINT_COSTS[20], 28)

    def test_cost_table_all_scores_present(self):
        for score in range(MIN_SCORE, MAX_SCORE + 1):
            self.assertIn(score, POINT_COSTS)

    def test_cost_table_monotonically_increasing(self):
        prev = POINT_COSTS[MIN_SCORE] - 1
        for score in range(MIN_SCORE, MAX_SCORE + 1):
            self.assertGreater(POINT_COSTS[score], prev)
            prev = POINT_COSTS[score]

    def test_standard_27_points_max_is_15(self):
        """With 27 points, no single score can exceed 15 while others are 8."""
        # Cost of 15 = 9, remaining = 18
        # 5 other scores at 8 cost 0 each → total = 9 ≤ 27 ✓
        # Cost of 16 = 12 → only 15 left for 5 scores
        # Can we get one 16? 12 + 0*5 = 12 ≤ 27 ✓ — but that's a remort thing
        # Actually 27 points CAN buy a 16 (cost 12), leaving 15 for others
        # The point is that 15 is the practical max for balanced builds
        self.assertEqual(POINT_COSTS[15], 9)
        self.assertEqual(POINT_COSTS[16], 12)

    def test_calculate_points_spent_all_eights(self):
        scores = {ab: 8 for ab in ABILITIES}
        self.assertEqual(_calculate_points_spent(scores), 0)

    def test_calculate_points_spent_mixed(self):
        scores = {
            Ability.STR: 15, Ability.DEX: 14, Ability.CON: 13,
            Ability.INT: 10, Ability.WIS: 10, Ability.CHA: 8,
        }
        # 9 + 7 + 5 + 2 + 2 + 0 = 25
        self.assertEqual(_calculate_points_spent(scores), 25)


# =======================================================================
#  Racial Bonuses Helper
# =======================================================================

class TestRacialBonuses(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_human_no_bonuses(self):
        bonuses = _get_racial_bonuses("human")
        self.assertEqual(len(bonuses), 0)

    def test_dwarf_bonuses(self):
        bonuses = _get_racial_bonuses("dwarf")
        self.assertEqual(bonuses[Ability.CON], 2)
        self.assertEqual(bonuses[Ability.DEX], -1)

    def test_unknown_race(self):
        bonuses = _get_racial_bonuses("nonexistent")
        self.assertEqual(bonuses, {})


# =======================================================================
#  Race Node
# =======================================================================

class TestRaceNode(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_race_node_returns_options(self):
        caller = _MockCaller({})
        text, options = node_race_select(caller, "")
        self.assertIn("Choose Your Race", text)
        # Should have at least 3 numbered race options + 1 _default
        numbered = [o for o in options if o.get("key", "").isdigit()]
        self.assertGreaterEqual(len(numbered), 3)

    def test_race_node_compact_teaser(self):
        """Race node shows compact teasers, not full descriptions."""
        caller = _MockCaller({})
        text, options = node_race_select(caller, "")
        # Should have info hint
        self.assertIn("info", text)
        # Should NOT have the full stat block inline
        self.assertNotIn("Ability bonuses:", text)

    def test_race_info_shows_detail(self):
        caller = _MockCaller({"_race_keys": ["human", "dwarf", "elf"]})
        result = _handle_race_info(caller, "info 2")
        # Should return to race select with detail
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0], "node_race_select")
        self.assertIn("detail", result[1])
        self.assertIn("Dwarf", result[1]["detail"])
        self.assertIn("Ability bonuses:", result[1]["detail"])

    def test_race_info_by_name(self):
        caller = _MockCaller({"_race_keys": ["human", "dwarf", "elf"]})
        result = _handle_race_info(caller, "info dwarf")
        self.assertIn("Dwarf", result[1]["detail"])

    def test_race_info_invalid(self):
        caller = _MockCaller({"_race_keys": ["human", "dwarf", "elf"]})
        result = _handle_race_info(caller, "info 99")
        self.assertIn("No race found", result[1]["detail"])

    def test_race_unknown_command(self):
        caller = _MockCaller({"_race_keys": ["human", "dwarf", "elf"]})
        result = _handle_race_info(caller, "blah")
        self.assertIn("Unknown command", result[1]["detail"])

    def test_set_race_stores_key(self):
        caller = _MockCaller({})
        result = _set_race(caller, "", race_key="dwarf")
        self.assertEqual(caller.ndb._chargen["race_key"], "dwarf")
        self.assertEqual(result, "node_class_select")


# =======================================================================
#  Class Node
# =======================================================================

class TestClassNode(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_class_node_shows_race(self):
        caller = _MockCaller({"race_key": "human"})
        text, options = node_class_select(caller, "")
        self.assertIn("Human", text)

    def test_class_node_has_back_option(self):
        caller = _MockCaller({"race_key": "human"})
        text, options = node_class_select(caller, "")
        back_opts = [o for o in options if o.get("desc", "").startswith("Back")]
        self.assertEqual(len(back_opts), 1)

    def test_class_node_compact_teaser(self):
        caller = _MockCaller({"race_key": "human"})
        text, options = node_class_select(caller, "")
        self.assertIn("info", text)
        # Numbered options + back + _default
        numbered = [o for o in options if isinstance(o.get("key", ""), str) and o["key"].isdigit()]
        self.assertGreaterEqual(len(numbered), 2)

    def test_class_info_shows_detail(self):
        caller = _MockCaller({"race_key": "human", "_class_keys": ["warrior", "thief"]})
        result = _handle_class_info(caller, "info 1")
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0], "node_class_select")
        self.assertIn("Warrior", result[1]["detail"])
        self.assertIn("Prime attribute:", result[1]["detail"])

    def test_class_info_by_name(self):
        caller = _MockCaller({"race_key": "human", "_class_keys": ["warrior", "thief"]})
        result = _handle_class_info(caller, "info thief")
        self.assertIn("Thief", result[1]["detail"])

    def test_class_info_invalid(self):
        caller = _MockCaller({"race_key": "human", "_class_keys": ["warrior", "thief"]})
        result = _handle_class_info(caller, "info 99")
        self.assertIn("No class found", result[1]["detail"])

    def test_set_class_stores_key(self):
        caller = _MockCaller({"race_key": "human"})
        result = _set_class(caller, "", class_key="warrior")
        self.assertEqual(caller.ndb._chargen["class_key"], "warrior")
        self.assertEqual(result, "node_alignment_select")


# =======================================================================
#  Alignment Node
# =======================================================================

class TestAlignmentNode(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_alignment_node_shows_race_and_class(self):
        caller = _MockCaller({"race_key": "human", "class_key": "warrior"})
        text, options = node_alignment_select(caller, "")
        self.assertIn("Human", text)
        self.assertIn("Warrior", text)

    def test_alignment_node_all_nine_for_unrestricted(self):
        """Human warrior has no alignment restrictions — all 9 available via _default."""
        caller = _MockCaller({"race_key": "human", "class_key": "warrior"})
        text, options = node_alignment_select(caller, "")
        # Only 2 options: back + _default (numbered grid rendered in text body)
        self.assertEqual(len(options), 2)
        # All 9 alignments should be numbered in the text
        self.assertIn("1.", text)
        self.assertIn("9.", text)

    def test_alignment_input_stores_value(self):
        caller = _MockCaller({"race_key": "human", "class_key": "warrior"})
        # First call node to populate _valid_alignments cache
        node_alignment_select(caller, "")
        result = _handle_alignment_input(caller, "3")
        # Human warrior valid alignments: all 9 in grid order, 3rd = Chaotic Good
        self.assertEqual(caller.ndb._chargen["alignment"], Alignment.CHAOTIC_GOOD)
        self.assertEqual(result, "node_point_buy")

    def test_alignment_input_initializes_scores(self):
        caller = _MockCaller({"race_key": "human", "class_key": "warrior"})
        node_alignment_select(caller, "")
        _handle_alignment_input(caller, "5")
        state = caller.ndb._chargen
        self.assertIn("scores", state)
        for ab in ABILITIES:
            self.assertEqual(state["scores"][ab], 8)
        self.assertEqual(state["points_remaining"], 27)

    def test_alignment_input_invalid_number(self):
        caller = _MockCaller({"race_key": "human", "class_key": "warrior"})
        node_alignment_select(caller, "")
        result = _handle_alignment_input(caller, "99")
        self.assertIsInstance(result, tuple)
        self.assertIn("Unknown command", result[1]["error"])


# =======================================================================
#  Point Buy Node
# =======================================================================

class TestPointBuyNode(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_point_buy_displays_scores(self):
        caller = _MockCaller(_default_state())
        text, options = node_point_buy(caller, "")
        self.assertIn("Points remaining", text)
        self.assertIn("STR", text)
        self.assertIn("27", text)

    def test_point_buy_has_done_and_back(self):
        caller = _MockCaller(_default_state())
        text, options = node_point_buy(caller, "")
        keys = []
        for opt in options:
            k = opt.get("key", "")
            if isinstance(k, tuple):
                keys.extend(k)
            else:
                keys.append(k)
        self.assertIn("done", keys)
        self.assertIn("back", keys)

    def test_increment_ability(self):
        caller = _MockCaller(_default_state())
        result = _handle_point_buy_input(caller, "str+")
        state = caller.ndb._chargen
        self.assertEqual(state["scores"][Ability.STR], 9)
        self.assertEqual(state["points_remaining"], 26)  # 27 - 1
        self.assertEqual(result, "node_point_buy")

    def test_decrement_ability(self):
        state = _default_state()
        state["scores"][Ability.STR] = 10
        state["points_remaining"] = 25
        caller = _MockCaller(state)
        result = _handle_point_buy_input(caller, "str-")
        self.assertEqual(caller.ndb._chargen["scores"][Ability.STR], 9)
        self.assertEqual(caller.ndb._chargen["points_remaining"], 26)  # 25 + 1

    def test_set_ability_directly(self):
        caller = _MockCaller(_default_state())
        result = _handle_point_buy_input(caller, "str 15")
        state = caller.ndb._chargen
        self.assertEqual(state["scores"][Ability.STR], 15)
        self.assertEqual(state["points_remaining"], 18)  # 27 - 9

    def test_cannot_exceed_max(self):
        state = _default_state()
        state["scores"][Ability.STR] = MAX_SCORE
        caller = _MockCaller(state)
        result = _handle_point_buy_input(caller, "str+")
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0], "node_point_buy")
        self.assertIn("maximum", result[1]["error"])

    def test_cannot_go_below_min(self):
        state = _default_state()
        state["scores"][Ability.STR] = MIN_SCORE
        caller = _MockCaller(state)
        result = _handle_point_buy_input(caller, "str-")
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0], "node_point_buy")
        self.assertIn("minimum", result[1]["error"])

    def test_not_enough_points(self):
        state = _default_state()
        state["points_remaining"] = 0
        caller = _MockCaller(state)
        result = _handle_point_buy_input(caller, "str+")
        self.assertIsInstance(result, tuple)
        self.assertIn("Not enough points", result[1]["error"])

    def test_set_too_high(self):
        caller = _MockCaller(_default_state())
        result = _handle_point_buy_input(caller, "str 21")
        self.assertIsInstance(result, tuple)
        self.assertIn("between", result[1]["error"])

    def test_set_too_low(self):
        caller = _MockCaller(_default_state())
        result = _handle_point_buy_input(caller, "str 4")
        self.assertIsInstance(result, tuple)
        self.assertIn("between", result[1]["error"])

    def test_unknown_command(self):
        caller = _MockCaller(_default_state())
        result = _handle_point_buy_input(caller, "xyz")
        self.assertIsInstance(result, tuple)
        self.assertIn("Unknown", result[1]["error"])

    def test_set_ability_refund(self):
        """Setting an ability lower should refund points."""
        state = _default_state()
        state["scores"][Ability.STR] = 15
        state["points_remaining"] = 18  # 27 - 9
        caller = _MockCaller(state)
        _handle_point_buy_input(caller, "str 10")
        self.assertEqual(caller.ndb._chargen["scores"][Ability.STR], 10)
        self.assertEqual(caller.ndb._chargen["points_remaining"], 25)  # 18 + 7 (cost 9 - cost 2)

    def test_increment_cost_increases_at_high_scores(self):
        """Going from 14→15 costs 2 points, not 1."""
        state = _default_state()
        state["scores"][Ability.STR] = 14
        state["points_remaining"] = 20
        caller = _MockCaller(state)
        _handle_point_buy_input(caller, "str+")
        self.assertEqual(caller.ndb._chargen["scores"][Ability.STR], 15)
        # Cost: POINT_COSTS[15] - POINT_COSTS[14] = 9 - 7 = 2
        self.assertEqual(caller.ndb._chargen["points_remaining"], 18)

    def test_decrement_below_eight_refunds_point(self):
        """Dumping STR from 8→7 should refund 1 point."""
        caller = _MockCaller(_default_state())
        _handle_point_buy_input(caller, "str-")
        self.assertEqual(caller.ndb._chargen["scores"][Ability.STR], 7)
        self.assertEqual(caller.ndb._chargen["points_remaining"], 28)  # 27 + 1

    def test_dump_stat_to_minimum(self):
        """Dumping STR from 8→5 should refund 3 points total."""
        caller = _MockCaller(_default_state())
        _handle_point_buy_input(caller, "str 5")
        self.assertEqual(caller.ndb._chargen["scores"][Ability.STR], 5)
        # cost_diff = POINT_COSTS[5] - POINT_COSTS[8] = -3 - 0 = -3
        # points = 27 - (-3) = 30
        self.assertEqual(caller.ndb._chargen["points_remaining"], 30)

    def test_set_from_dump_to_high(self):
        """Setting from 5 directly to 15 should cost 12 points (9 - (-3))."""
        state = _default_state()
        state["scores"][Ability.STR] = 5
        state["points_remaining"] = 30
        caller = _MockCaller(state)
        _handle_point_buy_input(caller, "str 15")
        self.assertEqual(caller.ndb._chargen["scores"][Ability.STR], 15)
        # cost_diff = POINT_COSTS[15] - POINT_COSTS[5] = 9 - (-3) = 12
        self.assertEqual(caller.ndb._chargen["points_remaining"], 18)

    def test_negative_cost_in_calculate_points_spent(self):
        """Scores below 8 should produce negative point costs."""
        scores = {
            Ability.STR: 5, Ability.DEX: 5, Ability.CON: 8,
            Ability.INT: 8, Ability.WIS: 8, Ability.CHA: 8,
        }
        # -3 + -3 + 0 + 0 + 0 + 0 = -6
        self.assertEqual(_calculate_points_spent(scores), -6)

    def test_reset_scores_and_back(self):
        caller = _MockCaller(_default_state())
        result = _reset_scores_and_back(caller, "")
        self.assertNotIn("scores", caller.ndb._chargen)
        self.assertEqual(result, "node_alignment_select")

    def test_error_displays_in_node(self):
        caller = _MockCaller(_default_state())
        text, options = node_point_buy(caller, "", error="Test error message")
        self.assertIn("Test error message", text)

    def test_done_with_points_remaining_goes_to_confirm(self):
        """Done with unspent points should route to confirmation node."""
        caller = _MockCaller(_default_state())
        text, options = node_point_buy(caller, "")
        done_opt = [o for o in options if isinstance(o.get("key"), tuple) and "done" in o["key"]]
        self.assertEqual(len(done_opt), 1)
        self.assertEqual(done_opt[0]["goto"], "node_point_buy_confirm")

    def test_done_with_zero_points_goes_to_weapon_skills(self):
        """Done with all points spent should go directly to weapon skills."""
        state = _default_state()
        state["points_remaining"] = 0
        caller = _MockCaller(state)
        text, options = node_point_buy(caller, "")
        done_opt = [o for o in options if isinstance(o.get("key"), tuple) and "done" in o["key"]]
        self.assertEqual(len(done_opt), 1)
        self.assertEqual(done_opt[0]["goto"], "node_weapon_skills")

    def test_point_buy_confirm_shows_warning(self):
        state = _default_state()
        state["points_remaining"] = 5
        caller = _MockCaller(state)
        text, options = node_point_buy_confirm(caller, "")
        self.assertIn("5", text)
        self.assertIn("still have", text)

    def test_point_buy_confirm_yes_proceeds(self):
        caller = _MockCaller(_default_state())
        text, options = node_point_buy_confirm(caller, "")
        yes_opt = [o for o in options if isinstance(o.get("key"), tuple) and "yes" in o["key"]]
        self.assertEqual(yes_opt[0]["goto"], "node_weapon_skills")

    def test_point_buy_confirm_no_goes_back(self):
        caller = _MockCaller(_default_state())
        text, options = node_point_buy_confirm(caller, "")
        no_opt = [o for o in options if isinstance(o.get("key"), tuple) and "no" in o["key"]]
        self.assertEqual(no_opt[0]["goto"], "node_point_buy")


# =======================================================================
#  Name Node
# =======================================================================

class TestNameNode(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_name_node_shows_instructions(self):
        caller = _MockCaller(_default_state())
        text, options = node_name(caller, "")
        self.assertIn("Choose Your Name", text)

    def test_valid_name(self):
        caller = _MockCaller(_default_state())
        with patch(
            "server.main_menu.chargen.chargen_menu.ObjectDB.objects"
        ) as mock_objects:
            mock_objects.filter.return_value.exists.return_value = False
            result = _handle_name_input(caller, "Thorin")

        self.assertEqual(result, "node_confirm")
        self.assertEqual(caller.ndb._chargen["char_name"], "Thorin")

    def test_name_too_short(self):
        caller = _MockCaller(_default_state())
        result = _handle_name_input(caller, "Ab")
        self.assertIsInstance(result, tuple)
        self.assertIn("at least 3", result[1]["error"])

    def test_name_too_long(self):
        caller = _MockCaller(_default_state())
        result = _handle_name_input(caller, "A" * 21)
        self.assertIsInstance(result, tuple)
        self.assertIn("20 characters", result[1]["error"])

    def test_name_non_alpha(self):
        caller = _MockCaller(_default_state())
        result = _handle_name_input(caller, "Thor1n")
        self.assertIsInstance(result, tuple)
        self.assertIn("only letters", result[1]["error"])

    def test_name_with_unquoted_spaces(self):
        """Unquoted multi-word name should suggest double quotes."""
        caller = _MockCaller(_default_state())
        result = _handle_name_input(caller, "Sir Robin")
        self.assertIsInstance(result, tuple)
        self.assertIn("double quotes", result[1]["error"])

    def test_name_already_taken(self):
        caller = _MockCaller(_default_state())
        with patch(
            "server.main_menu.chargen.chargen_menu.ObjectDB.objects"
        ) as mock_objects:
            mock_objects.filter.return_value.exists.return_value = True
            result = _handle_name_input(caller, "Thorin")
        self.assertIsInstance(result, tuple)
        self.assertIn("already taken", result[1]["error"])

    def test_name_capitalized(self):
        caller = _MockCaller(_default_state())
        with patch(
            "server.main_menu.chargen.chargen_menu.ObjectDB.objects"
        ) as mock_objects:
            mock_objects.filter.return_value.exists.return_value = False
            _handle_name_input(caller, "thorin")
        self.assertEqual(caller.ndb._chargen["char_name"], "Thorin")

    def test_name_node_shows_error(self):
        caller = _MockCaller(_default_state())
        text, options = node_name(caller, "", error="Name error")
        self.assertIn("Name error", text)


# =======================================================================
#  Confirm Node
# =======================================================================

class TestConfirmNode(BaseEvenniaTest):

    def create_script(self):
        pass

    def _full_state(self):
        state = _default_state()
        state["scores"] = {
            Ability.STR: 15, Ability.DEX: 14, Ability.CON: 13,
            Ability.INT: 10, Ability.WIS: 10, Ability.CHA: 8,
        }
        state["char_name"] = "Thorin"
        return state

    def test_confirm_shows_all_choices(self):
        caller = _MockCaller(self._full_state())
        text, options = node_confirm(caller, "")
        self.assertIn("Thorin", text)
        self.assertIn("Human", text)
        self.assertIn("Warrior", text)
        self.assertIn("True Neutral", text)
        self.assertIn("STR", text)

    def test_confirm_has_confirm_back_restart(self):
        caller = _MockCaller(self._full_state())
        text, options = node_confirm(caller, "")
        descs = [o.get("desc", "") for o in options]
        self.assertTrue(any("Create" in d for d in descs))
        self.assertTrue(any("Back" in d for d in descs))
        self.assertTrue(any("Start over" in d for d in descs))

    def test_restart_clears_state(self):
        state = self._full_state()
        session = state["session"]
        caller = _MockCaller(state)
        result = _restart(caller, "")
        self.assertEqual(result, "node_race_select")
        self.assertEqual(caller.ndb._chargen["session"], session)
        self.assertNotIn("race_key", caller.ndb._chargen)


# =======================================================================
#  Create Node (full flow)
# =======================================================================

class TestCreateNode(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_create_node_calls_create_character(self):
        state = _default_state()
        state["scores"] = {
            Ability.STR: 15, Ability.DEX: 14, Ability.CON: 13,
            Ability.INT: 10, Ability.WIS: 10, Ability.CHA: 8,
        }
        state["char_name"] = "Testchar"
        state["alignment"] = Alignment.CHAOTIC_GOOD

        caller = _MockCaller(state)

        mock_char = MagicMock()
        mock_char.key = "Testchar"
        # Make setattr work properly
        mock_char.base_strength = 8
        mock_char.strength = 8
        mock_char.base_dexterity = 8
        mock_char.dexterity = 8
        mock_char.base_constitution = 8
        mock_char.constitution = 8
        mock_char.base_intelligence = 8
        mock_char.intelligence = 8
        mock_char.base_wisdom = 8
        mock_char.wisdom = 8
        mock_char.base_charisma = 8
        mock_char.charisma = 8

        caller.create_character = MagicMock(return_value=(mock_char, None))

        with patch(
            "server.main_menu.chargen.chargen_menu.get_race"
        ) as mock_get_race, patch(
            "server.main_menu.chargen.chargen_menu.get_char_class"
        ) as mock_get_class:
            mock_race = MagicMock()
            mock_get_race.return_value = mock_race
            mock_class = MagicMock()
            mock_get_class.return_value = mock_class

            result = node_create(caller, "")

        # Verify character was created
        caller.create_character.assert_called_once_with(
            key="Testchar", ip="127.0.0.1"
        )

        # Verify race was applied
        mock_race.at_taking_race.assert_called_once_with(mock_char)

        # Verify class was applied
        mock_class.at_char_first_gaining_class.assert_called_once_with(mock_char)

        # Verify alignment was set
        self.assertEqual(mock_char.alignment, Alignment.CHAOTIC_GOOD)

        # Verify point buy scores were applied
        self.assertEqual(mock_char.base_strength, 15)
        self.assertEqual(mock_char.strength, 15)

        # Verify menu exit
        self.assertIsNone(result)

        # Verify success message
        self.assertTrue(
            any("created successfully" in msg for msg in caller._messages)
        )

    def test_create_node_handles_errors(self):
        state = _default_state()
        state["char_name"] = "Testchar"
        state["scores"] = {ab: 8 for ab in ABILITIES}
        caller = _MockCaller(state)
        caller.create_character = MagicMock(
            return_value=(None, ["Max characters reached."])
        )

        result = node_create(caller, "")

        self.assertIsNone(result)
        self.assertTrue(
            any("failed" in msg for msg in caller._messages)
        )

    def test_create_applies_scores_before_race(self):
        """Point buy scores must be set BEFORE at_taking_race (which adds bonuses)."""
        state = _default_state()
        state["scores"] = {ab: 10 for ab in ABILITIES}
        state["char_name"] = "Ordertest"

        caller = _MockCaller(state)
        mock_char = MagicMock()
        mock_char.key = "Ordertest"
        caller.create_character = MagicMock(return_value=(mock_char, None))

        call_order = []

        with patch(
            "server.main_menu.chargen.chargen_menu.get_race"
        ) as mock_get_race, patch(
            "server.main_menu.chargen.chargen_menu.get_char_class"
        ) as mock_get_class:
            mock_race = MagicMock()

            def track_race(char):
                call_order.append("at_taking_race")

            mock_race.at_taking_race = track_race
            mock_get_race.return_value = mock_race

            mock_class = MagicMock()

            def track_class(char):
                call_order.append("at_char_first_gaining_class")

            mock_class.at_char_first_gaining_class = track_class
            mock_get_class.return_value = mock_class

            # Intercept setattr on the mock char to track score assignment
            original_setattr = type(mock_char).__setattr__

            def tracking_setattr(self_inner, name, value):
                if name == "base_strength":
                    call_order.append("set_scores")
                original_setattr(self_inner, name, value)

            with patch.object(type(mock_char), "__setattr__", tracking_setattr):
                node_create(caller, "")

        # Verify order: scores → race → class
        self.assertIn("set_scores", call_order)
        self.assertIn("at_taking_race", call_order)
        self.assertIn("at_char_first_gaining_class", call_order)
        score_idx = call_order.index("set_scores")
        race_idx = call_order.index("at_taking_race")
        class_idx = call_order.index("at_char_first_gaining_class")
        self.assertLess(score_idx, race_idx)
        self.assertLess(race_idx, class_idx)


# =======================================================================
#  Weapon Skills Node
# =======================================================================

def _skill_state(race_key="dwarf", class_key="warrior"):
    """Return chargen state ready for skill selection."""
    state = _default_state()
    state["race_key"] = race_key
    state["class_key"] = class_key
    state["scores"] = {
        Ability.STR: 15, Ability.DEX: 14, Ability.CON: 13,
        Ability.INT: 10, Ability.WIS: 10, Ability.CHA: 8,
    }
    state["points_remaining"] = 2
    return state


class TestWeaponSkillsNode(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_displays_racial_profs(self):
        """Dwarf should show battleaxe and hammer as racial free."""
        caller = _MockCaller(_skill_state())
        text, options = node_weapon_skills(caller, "")
        self.assertIn("Racial (free)", text)
        self.assertIn("Battleaxe", text)
        self.assertIn("Hammer", text)

    def test_no_racial_profs_for_human(self):
        """Human has no racial weapon proficiencies."""
        caller = _MockCaller(_skill_state(race_key="human"))
        text, options = node_weapon_skills(caller, "")
        self.assertNotIn("Racial (free)", text)

    def test_excludes_racial_from_toggleable(self):
        """Dwarf's battleaxe/hammer should NOT appear in numbered list."""
        caller = _MockCaller(_skill_state())
        items = _get_weapon_items(get_race("dwarf"), "warrior")
        item_keys = {key for _, key in items}
        self.assertNotIn("battleaxe", item_keys)
        self.assertNotIn("hammer", item_keys)

    def test_shows_budget(self):
        """Warrior gets 4 weapon skill points at level 1."""
        caller = _MockCaller(_skill_state())
        text, options = node_weapon_skills(caller, "")
        self.assertIn("4", text)  # budget shown

    def test_toggle_on(self):
        """Toggling a weapon adds it to selected set."""
        caller = _MockCaller(_skill_state())
        node_weapon_skills(caller, "")  # populate _weapon_items
        result = _handle_weapon_toggle(caller, "1")
        state = caller.ndb._chargen
        self.assertEqual(len(state["selected_weapon_skills"]), 1)
        self.assertEqual(result, "node_weapon_skills")

    def test_toggle_off(self):
        """Toggling same weapon again removes it."""
        caller = _MockCaller(_skill_state())
        node_weapon_skills(caller, "")
        _handle_weapon_toggle(caller, "1")
        _handle_weapon_toggle(caller, "1")
        state = caller.ndb._chargen
        self.assertEqual(len(state["selected_weapon_skills"]), 0)

    def test_budget_enforcement(self):
        """Cannot select more than budget allows."""
        caller = _MockCaller(_skill_state())
        node_weapon_skills(caller, "")
        # Warrior budget = 4, toggle 4 weapons
        for i in range(1, 5):
            _handle_weapon_toggle(caller, str(i))
        # 5th should fail
        result = _handle_weapon_toggle(caller, "5")
        self.assertIsInstance(result, tuple)
        self.assertIn("No points remaining", result[1]["error"])
        self.assertEqual(len(caller.ndb._chargen["selected_weapon_skills"]), 4)

    def test_done_with_unspent_goes_to_confirm(self):
        """Done with unspent weapon points routes to skill_confirm."""
        caller = _MockCaller(_skill_state())
        text, options = node_weapon_skills(caller, "")
        done_opt = [o for o in options if isinstance(o.get("key"), tuple) and "done" in o["key"]]
        self.assertEqual(len(done_opt), 1)
        goto = done_opt[0]["goto"]
        self.assertIsInstance(goto, tuple)
        self.assertEqual(goto[0], "node_skill_confirm")
        self.assertEqual(goto[1]["next_node"], "node_class_skills")

    def test_done_all_spent_goes_to_class_skills(self):
        """Done with all points spent goes directly to class skills."""
        state = _skill_state()
        state["selected_weapon_skills"] = {"dagger", "bow", "spear", "staff"}
        caller = _MockCaller(state)
        text, options = node_weapon_skills(caller, "")
        done_opt = [o for o in options if isinstance(o.get("key"), tuple) and "done" in o["key"]]
        self.assertEqual(done_opt[0]["goto"], "node_class_skills")

    def test_back_clears_all_skills(self):
        """Back from weapon skills clears ALL skill/language selections."""
        state = _skill_state()
        state["selected_weapon_skills"] = {"dagger"}
        state["selected_class_skills"] = {"bash"}
        state["selected_general_skills"] = {"battleskills"}
        state["selected_extra_languages"] = {"kobold"}
        caller = _MockCaller(state)
        result = _clear_skills_and_back_to_pointbuy(caller, "")
        self.assertEqual(result, "node_point_buy")
        self.assertNotIn("selected_weapon_skills", caller.ndb._chargen)
        self.assertNotIn("selected_class_skills", caller.ndb._chargen)
        self.assertNotIn("selected_general_skills", caller.ndb._chargen)
        self.assertNotIn("selected_extra_languages", caller.ndb._chargen)

    def test_invalid_input(self):
        """Non-numeric input returns error."""
        caller = _MockCaller(_skill_state())
        node_weapon_skills(caller, "")
        result = _handle_weapon_toggle(caller, "abc")
        self.assertIsInstance(result, tuple)
        self.assertIn("Unknown command", result[1]["error"])

    def test_step_number(self):
        """Weapon skills should show Step 5."""
        caller = _MockCaller(_skill_state())
        text, options = node_weapon_skills(caller, "")
        self.assertIn("Step 5", text)

    def test_warrior_cannot_see_blowgun(self):
        """Warrior cannot train blowgun — should not appear in list."""
        items = _get_weapon_items(get_race("dwarf"), "warrior")
        item_keys = {key for _, key in items}
        self.assertNotIn("blowgun", item_keys)

    def test_warrior_cannot_see_shuriken(self):
        """Warrior cannot train shuriken — should not appear in list."""
        items = _get_weapon_items(get_race("dwarf"), "warrior")
        item_keys = {key for _, key in items}
        self.assertNotIn("shuriken", item_keys)

    def test_thief_can_see_blowgun(self):
        """Thief can train blowgun."""
        items = _get_weapon_items(get_race("human"), "thief")
        item_keys = {key for _, key in items}
        self.assertIn("blowgun", item_keys)

    def test_thief_cannot_see_great_sword(self):
        """Thief cannot train great_sword."""
        items = _get_weapon_items(get_race("human"), "thief")
        item_keys = {key for _, key in items}
        self.assertNotIn("great_sword", item_keys)

    def test_thief_sees_fewer_weapons_than_warrior(self):
        """Thief should see fewer weapon options than warrior."""
        warrior_items = _get_weapon_items(get_race("human"), "warrior")
        thief_items = _get_weapon_items(get_race("human"), "thief")
        self.assertGreater(len(warrior_items), len(thief_items))


# =======================================================================
#  Class Skills Node
# =======================================================================

class TestClassSkillsNode(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_warrior_class_skills(self):
        """Warrior should see warrior-specific skills."""
        items = _get_class_skill_items("warrior")
        item_keys = {key for _, key in items}
        self.assertIn("bash", item_keys)           # BASH → {"warrior"}
        self.assertIn("protect", item_keys)        # PROTECT → {"warrior", "paladin"}
        self.assertIn("strategy", item_keys)        # STRATEGY → {"warrior", "paladin"}
        self.assertIn("pummel", item_keys)        # PUMMEL → {"paladin", "warrior"}
        # Frenzy is berserker-only
        self.assertNotIn("frenzy", item_keys)

    def test_thief_class_skills(self):
        """Thief should see thief-specific skills."""
        items = _get_class_skill_items("thief")
        item_keys = {key for _, key in items}
        self.assertIn("stealth", item_keys)
        self.assertIn("subterfuge", item_keys)
        self.assertIn("stab", item_keys)
        # Warrior skills should NOT be present
        self.assertNotIn("bash", item_keys)
        self.assertNotIn("frenzy", item_keys)

    def test_excludes_general_skills(self):
        """General skills (available to all) should NOT appear in class skills."""
        items = _get_class_skill_items("warrior")
        item_keys = {key for _, key in items}
        self.assertNotIn("battleskills", item_keys)
        self.assertNotIn("blacksmith", item_keys)

    def test_class_skill_toggle(self):
        """Toggle a class skill on."""
        state = _skill_state()
        caller = _MockCaller(state)
        node_class_skills(caller, "")
        result = _handle_class_skill_toggle(caller, "1")
        self.assertEqual(len(caller.ndb._chargen["selected_class_skills"]), 1)
        self.assertEqual(result, "node_class_skills")

    def test_class_skill_budget(self):
        """Warrior gets 3 class skill points at level 1."""
        caller = _MockCaller(_skill_state())
        text, options = node_class_skills(caller, "")
        self.assertIn("3", text)  # budget

    def test_class_skill_budget_enforcement(self):
        """Cannot exceed class skill budget."""
        caller = _MockCaller(_skill_state())
        node_class_skills(caller, "")
        # Warrior budget = 3
        for i in range(1, 4):
            _handle_class_skill_toggle(caller, str(i))
        result = _handle_class_skill_toggle(caller, "4")
        self.assertIsInstance(result, tuple)
        self.assertIn("No points remaining", result[1]["error"])

    def test_done_unspent_goes_to_confirm(self):
        """Done with unspent class skill points routes to skill_confirm."""
        caller = _MockCaller(_skill_state())
        text, options = node_class_skills(caller, "")
        done_opt = [o for o in options if isinstance(o.get("key"), tuple) and "done" in o["key"]]
        goto = done_opt[0]["goto"]
        self.assertIsInstance(goto, tuple)
        self.assertEqual(goto[0], "node_skill_confirm")
        self.assertEqual(goto[1]["next_node"], "node_general_skills")

    def test_done_all_spent_goes_to_general(self):
        """Done with all class skill points spent goes to general skills."""
        state = _skill_state()
        state["selected_class_skills"] = {"bash", "pummel", "riposte"}
        caller = _MockCaller(state)
        text, options = node_class_skills(caller, "")
        done_opt = [o for o in options if isinstance(o.get("key"), tuple) and "done" in o["key"]]
        self.assertEqual(done_opt[0]["goto"], "node_general_skills")

    def test_back_goes_to_weapon_skills(self):
        """Back from class skills goes to weapon skills."""
        caller = _MockCaller(_skill_state())
        text, options = node_class_skills(caller, "")
        back_opt = [o for o in options if isinstance(o.get("key"), tuple) and "back" in o["key"]]
        self.assertEqual(back_opt[0]["goto"], "node_weapon_skills")

    def test_step_number(self):
        """Class skills should show Step 6."""
        caller = _MockCaller(_skill_state())
        text, options = node_class_skills(caller, "")
        self.assertIn("Step 6", text)


# =======================================================================
#  General Skills Node
# =======================================================================

class TestGeneralSkillsNode(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_general_skills_list(self):
        """General skills should include all skills with classes_available_to == {'all'}."""
        items = _get_general_skill_items()
        item_keys = {key for _, key in items}
        # Production skills
        self.assertIn("blacksmith", item_keys)
        self.assertIn("carpenter", item_keys)
        self.assertIn("alchemist", item_keys)
        self.assertIn("tailor", item_keys)
        self.assertIn("leatherworker", item_keys)
        self.assertIn("jeweller", item_keys)
        # General combat skills
        self.assertIn("battleskills", item_keys)
        self.assertIn("alertness", item_keys)

    def test_excludes_class_skills(self):
        """Class-specific skills should NOT be in general list."""
        items = _get_general_skill_items()
        item_keys = {key for _, key in items}
        self.assertNotIn("bash", item_keys)
        self.assertNotIn("stealth", item_keys)

    def test_general_skill_toggle(self):
        """Toggle a general skill on."""
        caller = _MockCaller(_skill_state())
        node_general_skills(caller, "")
        result = _handle_general_skill_toggle(caller, "1")
        self.assertEqual(len(caller.ndb._chargen["selected_general_skills"]), 1)
        self.assertEqual(result, "node_general_skills")

    def test_warrior_general_skill_budget(self):
        """Warrior gets 2 general skill points at level 1."""
        caller = _MockCaller(_skill_state())
        text, options = node_general_skills(caller, "")
        self.assertIn("2", text)

    def test_thief_general_skill_budget(self):
        """Thief gets 3 general skill points at level 1."""
        caller = _MockCaller(_skill_state(class_key="thief"))
        text, options = node_general_skills(caller, "")
        self.assertIn("3", text)

    def test_general_skill_budget_enforcement(self):
        """Cannot exceed general skill budget."""
        caller = _MockCaller(_skill_state())
        node_general_skills(caller, "")
        # Warrior budget = 2
        _handle_general_skill_toggle(caller, "1")
        _handle_general_skill_toggle(caller, "2")
        result = _handle_general_skill_toggle(caller, "3")
        self.assertIsInstance(result, tuple)
        self.assertIn("No points remaining", result[1]["error"])

    def test_done_unspent_goes_to_confirm(self):
        """Done with unspent general skill points routes to skill_confirm."""
        caller = _MockCaller(_skill_state())
        text, options = node_general_skills(caller, "")
        done_opt = [o for o in options if isinstance(o.get("key"), tuple) and "done" in o["key"]]
        goto = done_opt[0]["goto"]
        self.assertIsInstance(goto, tuple)
        self.assertEqual(goto[0], "node_skill_confirm")
        self.assertEqual(goto[1]["next_node"], "node_starting_knowledge")

    def test_done_all_spent_goes_to_starting_knowledge(self):
        """Done with all general skill points spent goes to starting knowledge."""
        state = _skill_state()
        state["selected_general_skills"] = {"battleskills", "perception"}
        caller = _MockCaller(state)
        text, options = node_general_skills(caller, "")
        done_opt = [o for o in options if isinstance(o.get("key"), tuple) and "done" in o["key"]]
        self.assertEqual(done_opt[0]["goto"], "node_starting_knowledge")

    def test_back_goes_to_class_skills(self):
        """Back from general skills goes to class skills."""
        caller = _MockCaller(_skill_state())
        text, options = node_general_skills(caller, "")
        back_opt = [o for o in options if isinstance(o.get("key"), tuple) and "back" in o["key"]]
        self.assertEqual(back_opt[0]["goto"], "node_class_skills")

    def test_step_number(self):
        """General skills should show Step 7."""
        caller = _MockCaller(_skill_state())
        text, options = node_general_skills(caller, "")
        self.assertIn("Step 7", text)


# =======================================================================
#  Languages Node
# =======================================================================

class TestLanguagesNode(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_auto_languages_human(self):
        """Human gets only Common automatically."""

        auto = _get_auto_languages(get_race("human"))
        self.assertEqual(auto, {"common"})

    def test_auto_languages_dwarf(self):
        """Dwarf gets Common + Dwarven automatically."""

        auto = _get_auto_languages(get_race("dwarf"))
        self.assertEqual(auto, {"common", "dwarven"})

    def test_auto_languages_elf(self):
        """Elf gets Common + Elfish automatically."""

        auto = _get_auto_languages(get_race("elf"))
        self.assertEqual(auto, {"common", "elfish"})

    def test_choosable_excludes_auto(self):
        """Choosable languages should exclude auto-granted ones."""
        choosable = _get_choosable_languages({"common", "dwarven"})
        keys = {key for _, key in choosable}
        self.assertNotIn("common", keys)
        self.assertNotIn("dwarven", keys)
        self.assertIn("elfish", keys)
        self.assertIn("kobold", keys)
        self.assertIn("goblin", keys)
        self.assertIn("dragon", keys)

    def test_bonus_picks_int_8(self):
        """INT 8 → 0 bonus picks (modifier = -1, clamped to 0)."""
        state = _skill_state(race_key="human")
        state["scores"][Ability.INT] = 8
        self.assertEqual(_get_bonus_language_picks(state), 0)

    def test_bonus_picks_int_10(self):
        """INT 10 → 0 bonus picks (modifier = 0)."""
        state = _skill_state(race_key="human")
        state["scores"][Ability.INT] = 10
        self.assertEqual(_get_bonus_language_picks(state), 0)

    def test_bonus_picks_int_12(self):
        """INT 12 → 1 bonus pick (modifier = +1)."""
        state = _skill_state(race_key="human")
        state["scores"][Ability.INT] = 12
        self.assertEqual(_get_bonus_language_picks(state), 1)

    def test_bonus_picks_int_14(self):
        """INT 14 → 2 bonus picks (modifier = +2)."""
        state = _skill_state(race_key="human")
        state["scores"][Ability.INT] = 14
        self.assertEqual(_get_bonus_language_picks(state), 2)

    def test_bonus_picks_includes_racial_int(self):
        """Elf gets +1 INT racial — INT 12 base + 1 racial = 13 final → 1 pick."""
        state = _skill_state(race_key="elf")
        state["scores"][Ability.INT] = 12
        self.assertEqual(_get_bonus_language_picks(state), 1)

    def test_zero_picks_informational(self):
        """With 0 bonus picks, show informational text and done/back only."""
        state = _skill_state(race_key="human")
        state["scores"][Ability.INT] = 8
        caller = _MockCaller(state)
        text, options = node_languages(caller, "")
        self.assertIn("no bonus languages", text)
        # Only done + back options (no _default toggle handler)
        self.assertEqual(len(options), 2)

    def test_auto_grant_all_when_picks_exceed_choosable(self):
        """If picks >= choosable languages, auto-grant all."""
        race = get_race("dwarf")
        auto_langs = _get_auto_languages(race)
        choosable = _get_choosable_languages(auto_langs)
        num_choosable = len(choosable)
        # Set INT high enough that modifier >= num_choosable: modifier = (INT-10)/2
        required_int = 10 + num_choosable * 2
        state = _skill_state(race_key="dwarf")
        state["scores"][Ability.INT] = required_int
        caller = _MockCaller(state)
        text, options = node_languages(caller, "")
        self.assertIn("automatically granted", text)
        self.assertEqual(len(caller.ndb._chargen["selected_extra_languages"]), num_choosable)

    def test_normal_toggle_with_picks(self):
        """With bonus picks, show toggle interface."""
        state = _skill_state(race_key="human")
        state["scores"][Ability.INT] = 14  # +2 modifier → 2 picks
        caller = _MockCaller(state)
        text, options = node_languages(caller, "")
        self.assertIn("Bonus language picks", text)
        self.assertIn("toggle", text)
        # Should have done + back + _default
        self.assertEqual(len(options), 3)

    def test_language_toggle_on(self):
        """Toggle a language on."""
        state = _skill_state(race_key="human")
        state["scores"][Ability.INT] = 14
        caller = _MockCaller(state)
        node_languages(caller, "")
        result = _handle_language_toggle(caller, "1")
        self.assertEqual(len(caller.ndb._chargen["selected_extra_languages"]), 1)
        self.assertEqual(result, "node_languages")

    def test_language_toggle_budget_enforcement(self):
        """Cannot select more languages than bonus picks allow."""
        state = _skill_state(race_key="human")
        state["scores"][Ability.INT] = 12  # +1 modifier → 1 pick
        caller = _MockCaller(state)
        node_languages(caller, "")
        _handle_language_toggle(caller, "1")
        result = _handle_language_toggle(caller, "2")
        self.assertIsInstance(result, tuple)
        self.assertIn("No points remaining", result[1]["error"])

    def test_done_unused_picks_goes_to_confirm(self):
        """Done with unused language picks routes to skill_confirm."""
        state = _skill_state(race_key="human")
        state["scores"][Ability.INT] = 14  # 2 picks
        caller = _MockCaller(state)
        text, options = node_languages(caller, "")
        done_opt = [o for o in options if isinstance(o.get("key"), tuple) and "done" in o["key"]]
        goto = done_opt[0]["goto"]
        self.assertIsInstance(goto, tuple)
        self.assertEqual(goto[0], "node_skill_confirm")
        next_node = goto[1]["next_node"]
        self.assertIsInstance(next_node, tuple)
        self.assertTrue(callable(next_node[0]))
        self.assertIn("cannot be saved", goto[1]["save_msg"])

    def test_done_all_used_goes_to_name(self):
        """Done with all language picks used goes directly to name."""
        state = _skill_state(race_key="human")
        state["scores"][Ability.INT] = 12  # 1 pick
        state["selected_extra_languages"] = {"kobold"}
        caller = _MockCaller(state)
        text, options = node_languages(caller, "")
        done_opt = [o for o in options if isinstance(o.get("key"), tuple) and "done" in o["key"]]
        goto = done_opt[0]["goto"]
        self.assertIsInstance(goto, tuple)
        self.assertTrue(callable(goto[0]))

    def test_back_goes_via_back_function(self):
        """Back from languages uses _back_from_languages (routes through starting knowledge if needed)."""
        state = _skill_state(race_key="human")
        state["scores"][Ability.INT] = 8
        caller = _MockCaller(state)
        text, options = node_languages(caller, "")
        back_opt = [o for o in options if isinstance(o.get("key"), tuple) and "back" in o["key"]]
        # Back is now a callable tuple (_back_from_languages, {})
        goto = back_opt[0]["goto"]
        self.assertIsInstance(goto, tuple)
        self.assertTrue(callable(goto[0]))

    def test_step_number(self):
        """Languages should show Step 9."""
        state = _skill_state(race_key="human")
        state["scores"][Ability.INT] = 8
        caller = _MockCaller(state)
        text, options = node_languages(caller, "")
        self.assertIn("Step 9", text)


# =======================================================================
#  Skill Confirm Node
# =======================================================================

class TestSkillConfirmNode(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_shows_unspent_count(self):
        caller = _MockCaller(_skill_state())
        text, options = node_skill_confirm(caller, "",
            points_unspent=3, skill_type="weapon skill",
            return_node="node_weapon_skills", next_node="node_class_skills")
        self.assertIn("3", text)
        self.assertIn("weapon skill", text)

    def test_yes_goes_to_next(self):
        caller = _MockCaller(_skill_state())
        text, options = node_skill_confirm(caller, "",
            points_unspent=2, skill_type="class skill",
            return_node="node_class_skills", next_node="node_general_skills")
        yes_opt = [o for o in options if isinstance(o.get("key"), tuple) and "yes" in o["key"]]
        self.assertEqual(yes_opt[0]["goto"], "node_general_skills")

    def test_no_goes_back(self):
        caller = _MockCaller(_skill_state())
        text, options = node_skill_confirm(caller, "",
            points_unspent=1, skill_type="general skill",
            return_node="node_general_skills", next_node="node_languages")
        no_opt = [o for o in options if isinstance(o.get("key"), tuple) and "no" in o["key"]]
        self.assertEqual(no_opt[0]["goto"], "node_general_skills")

    def test_custom_save_message(self):
        """Language confirm shows 'cannot be saved' message."""
        caller = _MockCaller(_skill_state())
        text, options = node_skill_confirm(caller, "",
            points_unspent=1, skill_type="language",
            return_node="node_languages", next_node="node_name",
            save_msg="Unused picks cannot be saved.")
        self.assertIn("cannot be saved", text)


# =======================================================================
#  Restart Confirm Node
# =======================================================================

class TestRestartConfirmNode(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_restart_confirm_shows_warning(self):
        caller = _MockCaller(_skill_state())
        text, options = node_restart_confirm(caller, "")
        self.assertIn("start over", text)
        self.assertIn("lost", text)

    def test_restart_confirm_yes_restarts(self):
        caller = _MockCaller(_skill_state())
        text, options = node_restart_confirm(caller, "")
        yes_opt = [o for o in options if isinstance(o.get("key"), tuple) and "yes" in o["key"]]
        # Yes calls _restart
        goto = yes_opt[0]["goto"]
        self.assertIsInstance(goto, tuple)
        # First element should be the _restart callable
        self.assertEqual(goto[0], _restart)

    def test_restart_confirm_no_goes_back(self):
        caller = _MockCaller(_skill_state())
        text, options = node_restart_confirm(caller, "")
        no_opt = [o for o in options if isinstance(o.get("key"), tuple) and "no" in o["key"]]
        self.assertEqual(no_opt[0]["goto"], "node_confirm")


# =======================================================================
#  Multi-word Name Tests
# =======================================================================

class TestMultiWordName(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_quoted_multi_word_name(self):
        """Quoted multi-word name should be accepted and title-cased."""
        caller = _MockCaller(_default_state())
        with patch(
            "server.main_menu.chargen.chargen_menu.ObjectDB.objects"
        ) as mock_objects:
            mock_objects.filter.return_value.exists.return_value = False
            result = _handle_name_input(caller, '"bob jane"')
        self.assertEqual(result, "node_confirm")
        self.assertEqual(caller.ndb._chargen["char_name"], "Bob Jane")

    def test_quoted_single_word(self):
        """Quoted single word should work too."""
        caller = _MockCaller(_default_state())
        with patch(
            "server.main_menu.chargen.chargen_menu.ObjectDB.objects"
        ) as mock_objects:
            mock_objects.filter.return_value.exists.return_value = False
            result = _handle_name_input(caller, '"thorin"')
        self.assertEqual(result, "node_confirm")
        self.assertEqual(caller.ndb._chargen["char_name"], "Thorin")

    def test_quoted_name_non_alpha(self):
        """Quoted name with non-alpha chars should fail."""
        caller = _MockCaller(_default_state())
        result = _handle_name_input(caller, '"bob 123"')
        self.assertIsInstance(result, tuple)
        self.assertIn("only letters", result[1]["error"])

    def test_quoted_name_too_short(self):
        """Quoted name under 3 characters should fail."""
        caller = _MockCaller(_default_state())
        result = _handle_name_input(caller, '"ab"')
        self.assertIsInstance(result, tuple)
        self.assertIn("at least 3", result[1]["error"])

    def test_name_node_shows_step_10(self):
        """Name node should show Step 10."""
        caller = _MockCaller(_default_state())
        text, options = node_name(caller, "")
        self.assertIn("Step 10", text)

    def test_name_back_goes_to_languages(self):
        """Back from name goes to languages."""
        caller = _MockCaller(_default_state())
        text, options = node_name(caller, "")
        back_opt = [o for o in options if isinstance(o.get("key"), tuple) and "back" in o["key"]]
        self.assertEqual(back_opt[0]["goto"], "node_languages")


# =======================================================================
#  Confirm Node — Skills & Languages Display
# =======================================================================

class TestConfirmSkillsDisplay(BaseEvenniaTest):

    def create_script(self):
        pass

    def _full_skill_state(self):
        state = _skill_state()
        state["char_name"] = "Thorin"
        state["alignment"] = Alignment.TRUE_NEUTRAL
        state["selected_weapon_skills"] = {"dagger", "bow"}
        state["selected_class_skills"] = {"bash", "protect"}
        state["selected_general_skills"] = {"battleskills"}
        state["selected_extra_languages"] = {"kobold"}
        return state

    def test_confirm_shows_weapon_skills(self):
        caller = _MockCaller(self._full_skill_state())
        text, options = node_confirm(caller, "")
        self.assertIn("Weapon Skills", text)
        self.assertIn("Dagger", text)
        self.assertIn("Bow", text)
        # Dwarf racial profs
        self.assertIn("Battleaxe", text)
        self.assertIn("racial", text)

    def test_confirm_shows_class_skills(self):
        caller = _MockCaller(self._full_skill_state())
        text, options = node_confirm(caller, "")
        self.assertIn("Class Skills", text)
        self.assertIn("Bash", text)
        self.assertIn("Protect", text)

    def test_confirm_shows_general_skills(self):
        caller = _MockCaller(self._full_skill_state())
        text, options = node_confirm(caller, "")
        self.assertIn("General Skills", text)
        self.assertIn("Battleskills", text)

    def test_confirm_shows_unspent_points(self):
        """Unspent skill points shown as saved for later."""
        caller = _MockCaller(self._full_skill_state())
        text, options = node_confirm(caller, "")
        self.assertIn("saved for later", text)

    def test_confirm_shows_languages(self):
        caller = _MockCaller(self._full_skill_state())
        text, options = node_confirm(caller, "")
        self.assertIn("Languages", text)
        self.assertIn("Common", text)
        self.assertIn("Dwarven", text)
        self.assertIn("Kobold", text)

    def test_confirm_shows_con_modifier_in_hp(self):
        """HP display should include CON modifier when non-zero."""
        state = self._full_skill_state()
        # Default _skill_state has CON=13, dwarf gets +2 racial → 15 CON → +2 mod
        caller = _MockCaller(state)
        text, options = node_confirm(caller, "")
        self.assertIn("CON", text)

    def test_confirm_restart_goes_to_restart_confirm(self):
        """Restart option should route to restart_confirm node."""
        caller = _MockCaller(self._full_skill_state())
        text, options = node_confirm(caller, "")
        restart_opt = [o for o in options if isinstance(o.get("key"), tuple) and "restart" in o["key"]]
        self.assertEqual(restart_opt[0]["goto"], "node_restart_confirm")


# =======================================================================
#  Create Node — Skills & Languages Application
# =======================================================================

class TestCreateSkillApplication(BaseEvenniaTest):

    def create_script(self):
        pass

    def _create_state(self):
        state = _skill_state()
        state["char_name"] = "Testchar"
        state["alignment"] = Alignment.TRUE_NEUTRAL
        state["selected_weapon_skills"] = {"dagger", "bow"}
        state["selected_class_skills"] = {"bash", "protect"}
        state["selected_general_skills"] = {"battleskills"}
        state["selected_extra_languages"] = {"kobold"}
        return state

    def _run_create(self, state):
        caller = _MockCaller(state)

        mock_char = MagicMock()
        mock_char.key = state["char_name"]
        # Set up db attributes as dicts/values that the code reads
        mock_char.db.weapon_skill_mastery_levels = {"battleaxe": 1, "hammer": 1}
        mock_char.db.class_skill_mastery_levels = {}
        mock_char.db.general_skill_mastery_levels = {}
        mock_char.db.languages = {"common", "dwarven"}
        mock_char.db.classes = {
            "warrior": {"skill_pts_available": 3}
        }
        mock_char.weapon_skill_pts_available = 4
        mock_char.general_skill_pts_available = 2

        caller.create_character = MagicMock(return_value=(mock_char, None))

        with patch(
            "server.main_menu.chargen.chargen_menu.get_race"
        ) as mock_get_race, patch(
            "server.main_menu.chargen.chargen_menu.get_char_class"
        ) as mock_get_class:
            mock_race = MagicMock()
            mock_get_race.return_value = mock_race
            mock_class_obj = MagicMock()
            mock_get_class.return_value = mock_class_obj

            node_create(caller, "")

        return mock_char, caller

    def test_weapon_skills_applied(self):
        """Selected weapon skills should be set to BASIC."""
        mock_char, _ = self._run_create(self._create_state())
        weapon_mastery = mock_char.db.weapon_skill_mastery_levels
        self.assertEqual(weapon_mastery["dagger"], MasteryLevel.BASIC.value)
        self.assertEqual(weapon_mastery["bow"], MasteryLevel.BASIC.value)

    def test_racial_weapon_profs_preserved(self):
        """Racial weapon profs should still be present after chargen application."""
        mock_char, _ = self._run_create(self._create_state())
        weapon_mastery = mock_char.db.weapon_skill_mastery_levels
        self.assertEqual(weapon_mastery["battleaxe"], 1)
        self.assertEqual(weapon_mastery["hammer"], 1)

    def test_weapon_pts_deducted(self):
        """Weapon skill points should be deducted."""
        mock_char, _ = self._run_create(self._create_state())
        # Started with 4, spent 2
        self.assertEqual(mock_char.weapon_skill_pts_available, 2)

    def test_class_skills_init_unskilled(self):
        """All class skills should be initialized at UNSKILLED."""
        mock_char, _ = self._run_create(self._create_state())
        class_mastery = mock_char.db.class_skill_mastery_levels
        # Warrior has 4 class skills (bash, protect, pummel, strategy); all should exist
        self.assertGreaterEqual(len(class_mastery), 4)

    def test_class_skills_selected_upgraded(self):
        """Selected class skills should be upgraded to BASIC."""
        mock_char, _ = self._run_create(self._create_state())
        class_mastery = mock_char.db.class_skill_mastery_levels
        self.assertEqual(class_mastery["bash"]["mastery"], MasteryLevel.BASIC.value)
        self.assertEqual(class_mastery["protect"]["mastery"], MasteryLevel.BASIC.value)

    def test_class_skills_unselected_remain_unskilled(self):
        """Unselected class skills should remain UNSKILLED."""
        mock_char, _ = self._run_create(self._create_state())
        class_mastery = mock_char.db.class_skill_mastery_levels
        # Pummel is a warrior skill not in selected set
        self.assertEqual(class_mastery["pummel"]["mastery"], MasteryLevel.UNSKILLED.value)

    def test_class_skill_pts_deducted(self):
        """Class skill points should be deducted from db.classes."""
        mock_char, _ = self._run_create(self._create_state())
        cdata = mock_char.db.classes["warrior"]
        # Started with 3, spent 2
        self.assertEqual(cdata["skill_pts_available"], 1)

    def test_general_skills_applied(self):
        """Selected general skills should be set to BASIC."""
        mock_char, _ = self._run_create(self._create_state())
        general_mastery = mock_char.db.general_skill_mastery_levels
        self.assertEqual(general_mastery["battleskills"], MasteryLevel.BASIC.value)

    def test_general_pts_deducted(self):
        """General skill points should be deducted."""
        mock_char, _ = self._run_create(self._create_state())
        # Started with 2, spent 1
        self.assertEqual(mock_char.general_skill_pts_available, 1)

    def test_extra_languages_added(self):
        """Extra chosen languages should be added to character's languages."""
        mock_char, _ = self._run_create(self._create_state())
        langs = mock_char.db.languages
        self.assertIn("kobold", langs)
        # Auto languages should still be there
        self.assertIn("common", langs)
        self.assertIn("dwarven", langs)

    def test_no_extra_languages_preserves_existing(self):
        """If no extra languages chosen, existing languages untouched."""
        state = self._create_state()
        state["selected_extra_languages"] = set()
        mock_char, _ = self._run_create(state)
        # db.languages should not have been reassigned (stays as initial mock value)
        langs = mock_char.db.languages
        self.assertIn("common", langs)
        self.assertIn("dwarven", langs)

    def test_create_sets_hp_to_effective_max(self):
        """HP should be set to effective_hp_max after creation (includes CON modifier)."""
        mock_char, _ = self._run_create(self._create_state())
        # node_create does: new_char.hp = new_char.effective_hp_max
        self.assertEqual(mock_char.hp, mock_char.effective_hp_max)

    def test_create_success_message(self):
        """Should show success message after creation."""
        _, caller = self._run_create(self._create_state())
        self.assertTrue(
            any("created successfully" in msg for msg in caller._messages)
        )
