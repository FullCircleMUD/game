"""
Tests for resource processing commands — mill, bake, smelt, saw, tan, weave.

Verifies resource/gold validation, conversion logic, 'all' mode, rates display,
multi-input processing (bakery: flour + wood → bread), multi-recipe rooms
(smelter with multiple ore→ingot + alloy recipes), progress messages during
the processing delay, and busy-lock prevention.

The processing delay uses utils.delay() which is mocked to execute callbacks
immediately (no actual waiting in tests).

evennia test --settings settings tests.command_tests.test_cmd_process
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.room_specific_cmds.processing.cmd_process import CmdProcess
from commands.room_specific_cmds.processing.cmd_rates import CmdRates


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _give_resources(char, resources):
    """Give resources via service layer so mirror DB stays in sync."""
    for res_id, amount in resources.items():
        char.receive_resource_from_reserve(res_id, amount)


def _give_gold(char, amount):
    """Give gold via service layer so mirror DB stays in sync."""
    char.receive_gold_from_reserve(amount)


def _instant_delay(seconds, callback, *args, **kwargs):
    """Mock for utils.delay — executes callback immediately."""
    callback(*args, **kwargs)


class ProcessingTestBase(EvenniaCommandTest):
    """Base class that creates a windmill processing room."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_processing.RoomProcessing"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Configure room as a windmill: 1 Wheat (id=1) + 1 gold → 1 Flour (id=2)
        self.room1.db.processing_type = "windmill"
        self.room1.db.process_cost = 1
        self.room1.db.recipes = [
            {"inputs": {1: 1}, "output": 2, "amount": 1, "cost": 1},
        ]


# ── Basic Processing ────────────────────────────────────────────────

class TestProcessBasic(ProcessingTestBase):
    """Test basic single-input resource processing."""

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_process_one(self, mock_delay):
        """Processing 1 wheat + 1 gold should produce 1 flour."""
        _give_resources(self.char1, {1: 5})
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "")
        self.assertIn("1 Wheat", result)
        self.assertIn("1 Flour", result)
        self.assertIn("1 gold", result)
        self.assertEqual(self.char1.get_resource(1), 4)
        self.assertEqual(self.char1.get_resource(2), 1)
        self.assertEqual(self.char1.get_gold(), 9)

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_process_amount(self, mock_delay):
        """Processing 3 should consume 3 inputs and produce 3 outputs."""
        _give_resources(self.char1, {1: 10})
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "3")
        self.assertIn("3 Wheat", result)
        self.assertIn("3 Flour", result)
        self.assertEqual(self.char1.get_resource(1), 7)
        self.assertEqual(self.char1.get_resource(2), 3)
        self.assertEqual(self.char1.get_gold(), 7)

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_process_all(self, mock_delay):
        """'process all' should process as many as possible."""
        _give_resources(self.char1, {1: 5})
        _give_gold(self.char1, 3)  # gold is the bottleneck
        result = self.call(CmdProcess(), "all")
        self.assertIn("3 Wheat", result)
        self.assertIn("3 Flour", result)
        self.assertEqual(self.char1.get_resource(1), 2)
        self.assertEqual(self.char1.get_resource(2), 3)
        self.assertEqual(self.char1.get_gold(), 0)

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_process_all_resource_bottleneck(self, mock_delay):
        """'all' should be limited by available resources."""
        _give_resources(self.char1, {1: 2})
        _give_gold(self.char1, 100)
        result = self.call(CmdProcess(), "all")
        self.assertIn("2 Wheat", result)
        self.assertEqual(self.char1.get_resource(1), 0)
        self.assertEqual(self.char1.get_resource(2), 2)


# ── Validation ──────────────────────────────────────────────────────

class TestProcessValidation(ProcessingTestBase):
    """Test error messages for insufficient resources/gold."""

    def test_no_resources(self):
        """Should fail if character has no input resources."""
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "")
        self.assertIn("need", result.lower())

    def test_not_enough_resources(self):
        """Should fail if character doesn't have enough input resources."""
        _give_resources(self.char1, {1: 2})
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "5")
        self.assertIn("need 5 Wheat", result)

    def test_no_gold(self):
        """Should fail if character has no gold."""
        _give_resources(self.char1, {1: 5})
        result = self.call(CmdProcess(), "")
        self.assertIn("gold", result.lower())

    def test_not_enough_gold(self):
        """Should fail if character doesn't have enough gold."""
        _give_resources(self.char1, {1: 10})
        _give_gold(self.char1, 2)
        result = self.call(CmdProcess(), "5")
        self.assertIn("need 5 gold", result)

    def test_invalid_amount(self):
        """Non-numeric argument should try recipe match and fail gracefully."""
        result = self.call(CmdProcess(), "abc")
        self.assertIn("No recipe found", result)

    def test_zero_amount(self):
        """Zero amount should be rejected."""
        result = self.call(CmdProcess(), "0")
        self.assertIn("positive", result)

    def test_all_with_nothing(self):
        """'all' with no resources should give helpful message."""
        _give_gold(self.char1, 100)
        result = self.call(CmdProcess(), "all")
        self.assertIn("don't have", result.lower())


# ── Multi-Input Processing (Bakery) ─────────────────────────────────

class TestProcessMultiInput(ProcessingTestBase):
    """Test bakery-style processing with multiple input resources."""

    def setUp(self):
        super().setUp()
        # Reconfigure room as bakery: 1 Flour (2) + 1 Wood (6) + 1 gold → 1 Bread (3)
        self.room1.db.processing_type = "bakery"
        self.room1.db.recipes = [
            {"inputs": {2: 1, 6: 1}, "output": 3, "amount": 1, "cost": 1},
        ]

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_bake_one(self, mock_delay):
        """Baking 1 should consume 1 flour + 1 wood + 1 gold → 1 bread."""
        _give_resources(self.char1, {2: 5, 6: 5})
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "")
        self.assertIn("Bread", result)
        self.assertEqual(self.char1.get_resource(2), 4)  # flour
        self.assertEqual(self.char1.get_resource(6), 4)  # wood
        self.assertEqual(self.char1.get_resource(3), 1)  # bread
        self.assertEqual(self.char1.get_gold(), 9)

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_bake_all(self, mock_delay):
        """'all' should be limited by the scarcest input."""
        _give_resources(self.char1, {2: 10, 6: 3})  # wood is bottleneck
        _give_gold(self.char1, 100)
        result = self.call(CmdProcess(), "all")
        self.assertEqual(self.char1.get_resource(2), 7)   # 10 - 3
        self.assertEqual(self.char1.get_resource(6), 0)   # 3 - 3
        self.assertEqual(self.char1.get_resource(3), 3)   # produced
        self.assertEqual(self.char1.get_gold(), 97)

    def test_bake_missing_one_input(self):
        """Should fail if one input resource is missing."""
        _give_resources(self.char1, {2: 5})  # flour but no wood
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "")
        self.assertIn("need", result.lower())
        self.assertIn("Wood", result)


# ── Multi-Recipe Processing (Smelter) ──────────────────────────────

class TestMultiRecipeProcessing(ProcessingTestBase):
    """Test smelter-style rooms with multiple processing recipes."""

    def setUp(self):
        super().setUp()
        self.room1.db.processing_type = "smelter"
        self.room1.db.recipes = [
            {"inputs": {4: 1}, "output": 5, "amount": 1, "cost": 1},      # Iron Ore → Iron Ingot
            {"inputs": {23: 1}, "output": 24, "amount": 1, "cost": 1},     # Copper Ore → Copper Ingot
            {"inputs": {25: 1}, "output": 26, "amount": 1, "cost": 1},     # Tin Ore → Tin Ingot
            {"inputs": {24: 1, 26: 1}, "output": 32, "amount": 1, "cost": 1},  # Copper + Tin → Bronze
        ]

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_smelt_by_output_name(self, mock_delay):
        """'smelt iron ingot' should find the iron recipe by output name."""
        _give_resources(self.char1, {4: 5})
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "iron ingot")
        self.assertIn("Iron Ingot", result)
        self.assertEqual(self.char1.get_resource(4), 4)
        self.assertEqual(self.char1.get_resource(5), 1)

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_smelt_alloy_by_output_name(self, mock_delay):
        """'smelt bronze' should find the alloy recipe by output name."""
        _give_resources(self.char1, {24: 3, 26: 3})
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "bronze")
        self.assertIn("Bronze Ingot", result)
        self.assertEqual(self.char1.get_resource(24), 2)  # copper ingot
        self.assertEqual(self.char1.get_resource(26), 2)  # tin ingot
        self.assertEqual(self.char1.get_resource(32), 1)  # bronze

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_smelt_with_amount(self, mock_delay):
        """'smelt copper ingot 3' should process 3."""
        _give_resources(self.char1, {23: 5})
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "copper ingot 3")
        self.assertIn("3 Copper Ore", result)
        self.assertIn("Copper Ingot", result)
        self.assertEqual(self.char1.get_resource(23), 2)
        self.assertEqual(self.char1.get_resource(24), 3)

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_smelt_all_with_name(self, mock_delay):
        """'smelt tin ingot all' should process max."""
        _give_resources(self.char1, {25: 4})
        _give_gold(self.char1, 2)  # gold bottleneck
        result = self.call(CmdProcess(), "tin ingot all")
        self.assertEqual(self.char1.get_resource(25), 2)  # 4 - 2
        self.assertEqual(self.char1.get_resource(26), 2)  # produced

    def test_no_args_lists_recipes(self, ):
        """No args in multi-recipe room should list available recipes."""
        result = self.call(CmdProcess(), "")
        self.assertIn("Iron Ore", result)
        self.assertIn("Copper Ore", result)
        self.assertIn("Bronze", result)

    def test_no_match(self):
        """Unrecognised resource name should show error."""
        result = self.call(CmdProcess(), "adamantine")
        self.assertIn("No recipe found", result)

    def test_input_name_no_match(self):
        """Input-only names should not match — recipes match by output."""
        result = self.call(CmdProcess(), "iron ore")
        self.assertIn("No recipe found", result)

    def test_bare_amount_rejected(self):
        """Bare number in multi-recipe room should ask for specifics."""
        result = self.call(CmdProcess(), "5")
        self.assertIn("Specify", result)

    def test_bare_all_rejected(self):
        """Bare 'all' in multi-recipe room should ask for specifics."""
        result = self.call(CmdProcess(), "all")
        self.assertIn("Specify", result)

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_per_recipe_cost(self, mock_delay):
        """Recipe-level cost should override room default."""
        self.room1.db.recipes = [
            {"inputs": {4: 1}, "output": 5, "amount": 1, "cost": 3},
        ]
        _give_resources(self.char1, {4: 1})
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "")
        self.assertIn("3 gold", result)
        self.assertEqual(self.char1.get_gold(), 7)

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_cost_defaults_to_room(self, mock_delay):
        """Recipe without 'cost' key should use room's process_cost."""
        self.room1.db.process_cost = 2
        self.room1.db.recipes = [
            {"inputs": {4: 1}, "output": 5, "amount": 1},  # no "cost" key
        ]
        _give_resources(self.char1, {4: 1})
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "")
        self.assertIn("2 gold", result)
        self.assertEqual(self.char1.get_gold(), 8)


# ── Progress Messages ──────────────────────────────────────────────

class TestProcessProgress(ProcessingTestBase):
    """Test progress messages during processing delay."""

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_progress_single(self, mock_delay):
        """Processing 1 should show 'Done!'."""
        _give_resources(self.char1, {1: 1})
        _give_gold(self.char1, 1)
        result = self.call(CmdProcess(), "")
        self.assertIn("Done!", result)

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_progress_multiple(self, mock_delay):
        """Processing 3 should show progress ticks."""
        _give_resources(self.char1, {1: 3})
        _give_gold(self.char1, 3)
        result = self.call(CmdProcess(), "3")
        self.assertIn("1 of 3", result)
        self.assertIn("2 of 3", result)
        self.assertIn("Done!", result)

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_is_processing_cleared(self, mock_delay):
        """ndb.is_processing should be cleared after completion."""
        _give_resources(self.char1, {1: 1})
        _give_gold(self.char1, 1)
        self.call(CmdProcess(), "")
        self.assertFalse(self.char1.ndb.is_processing)


# ── Busy Lock ──────────────────────────────────────────────────────

class TestProcessBusy(ProcessingTestBase):
    """Test that concurrent processing is blocked."""

    def test_busy_rejected(self):
        """Should reject if already processing."""
        self.char1.ndb.is_processing = True
        _give_resources(self.char1, {1: 5})
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "")
        self.assertIn("already processing", result.lower())
        # Resources should NOT be consumed
        self.assertEqual(self.char1.get_resource(1), 5)
        self.assertEqual(self.char1.get_gold(), 10)


# ── Rates Command ───────────────────────────────────────────────────

class TestRatesCommand(ProcessingTestBase):
    """Test the rates display command."""

    def test_rates_shows_conversion(self):
        """Rates should show input → output and gold cost."""
        result = self.call(CmdRates(), "")
        self.assertIn("Wheat", result)
        self.assertIn("Flour", result)
        self.assertIn("1 gold", result)

    def test_rates_multi_input(self):
        """Rates should show multiple inputs for bakery."""
        self.room1.db.recipes = [
            {"inputs": {2: 1, 6: 1}, "output": 3, "amount": 1, "cost": 1},
        ]
        result = self.call(CmdRates(), "")
        self.assertIn("Flour", result)
        self.assertIn("Wood", result)
        self.assertIn("Bread", result)

# ── Experience Points ──────────────────────────────────────────────

class TestProcessXP(ProcessingTestBase):
    """Test XP awarded on successful processing."""

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_xp_awarded(self, mock_delay):
        """Should award process_xp on successful processing."""
        self.room1.db.process_xp = 5
        self.char1.experience_points = 0
        _give_resources(self.char1, {1: 1})
        _give_gold(self.char1, 1)
        self.call(CmdProcess(), "")
        self.assertEqual(self.char1.experience_points, 5)

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_xp_scales_with_amount(self, mock_delay):
        """XP should scale with amount processed."""
        self.room1.db.process_xp = 3
        self.char1.experience_points = 0
        _give_resources(self.char1, {1: 4})
        _give_gold(self.char1, 4)
        self.call(CmdProcess(), "4")
        self.assertEqual(self.char1.experience_points, 12)

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_no_xp_when_zero(self, mock_delay):
        """Should not show XP message when process_xp is 0."""
        self.room1.db.process_xp = 0
        _give_resources(self.char1, {1: 1})
        _give_gold(self.char1, 1)
        result = self.call(CmdProcess(), "")
        self.assertNotIn("XP", result)


    def test_rates_multi_recipe(self):
        """Rates should show all recipes in a multi-recipe room."""
        self.room1.db.recipes = [
            {"inputs": {4: 1}, "output": 5, "amount": 1, "cost": 1},
            {"inputs": {23: 1}, "output": 24, "amount": 1, "cost": 1},
            {"inputs": {24: 1, 26: 1}, "output": 32, "amount": 1, "cost": 1},
        ]
        result = self.call(CmdRates(), "")
        self.assertIn("Iron Ore", result)
        self.assertIn("Iron Ingot", result)
        self.assertIn("Copper Ore", result)
        self.assertIn("Copper Ingot", result)
        self.assertIn("Bronze Ingot", result)


# ── Substring Disambiguation (Sawmill) ──────────────────────────────

class TestSubstringDisambiguation(ProcessingTestBase):
    """
    Sawmill has Wood → Timber and Ironwood → Ironwood Timber. The query
    'timber' is a substring of both outputs; exact match must win as a
    tiebreaker so 'saw timber' routes to the Wood recipe rather than
    silently picking Ironwood Timber.
    """

    def setUp(self):
        super().setUp()
        self.room1.db.processing_type = "sawmill"
        self.room1.db.recipes = [
            {"inputs": {6: 1}, "output": 7, "amount": 1, "cost": 1},     # Wood → Timber
            {"inputs": {40: 1}, "output": 41, "amount": 1, "cost": 3},   # Ironwood → Ironwood Timber
        ]

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_saw_timber_picks_plain_timber(self, mock_delay):
        """'saw timber' must hit the Wood → Timber recipe, not Ironwood Timber."""
        _give_resources(self.char1, {6: 2, 40: 2})
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "timber")
        self.assertIn("1 Wood", result)
        self.assertIn("Timber", result)
        self.assertNotIn("Ironwood", result)
        self.assertEqual(self.char1.get_resource(6), 1)   # wood consumed
        self.assertEqual(self.char1.get_resource(7), 1)   # timber produced
        self.assertEqual(self.char1.get_resource(40), 2)  # ironwood untouched
        self.assertEqual(self.char1.get_resource(41), 0)  # no ironwood timber

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_saw_ironwood_picks_ironwood(self, mock_delay):
        """'saw ironwood' should resolve uniquely to the Ironwood recipe."""
        _give_resources(self.char1, {40: 2})
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "ironwood")
        self.assertIn("Ironwood Timber", result)
        self.assertEqual(self.char1.get_resource(40), 1)
        self.assertEqual(self.char1.get_resource(41), 1)

    @patch("commands.room_specific_cmds.processing.cmd_process.delay",
           side_effect=_instant_delay)
    def test_saw_ironwood_timber_picks_ironwood(self, mock_delay):
        """Full name 'ironwood timber' is an exact match for the ironwood recipe."""
        _give_resources(self.char1, {40: 2})
        _give_gold(self.char1, 10)
        result = self.call(CmdProcess(), "ironwood timber")
        self.assertIn("Ironwood Timber", result)
        self.assertEqual(self.char1.get_resource(41), 1)
