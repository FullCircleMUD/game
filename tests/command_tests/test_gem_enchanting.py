"""
Tests for gem enchanting — roll tables, restrictions, and cmd_craft integration.

Covers:
    1. roll_gem_enchantment() — effect rolls, restriction rolls, edge cases
    2. Table data structure validation
    3. CmdCraft integration — enchanting in a wizard's workshop sets gem_effects
       and gem_restrictions on the spawned item
    4. Recipe validation — correct ingredients, skill, room type

evennia test --settings settings tests.command_tests.test_gem_enchanting
"""

from unittest import TestCase
from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.room_specific_cmds.crafting.cmd_craft import CmdCraft
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.recipes.enchanting.gem_tables import (
    RUBY_ENCHANT_TABLE,
    RESTRICTION_TABLE,
    roll_gem_enchantment,
)


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
TOKEN_ID = 201

# All 10 effects from the BASIC ruby table, in order
_RUBY_BASIC_EFFECTS = [entry[1] for entry in RUBY_ENCHANT_TABLE[1]]


def _give_resources(char, resources):
    for res_id, amount in resources.items():
        char.receive_resource_from_reserve(res_id, amount)


def _give_gold(char, amount):
    char.receive_gold_from_reserve(amount)


def _give_enchanting_skill(char, mastery=MasteryLevel.BASIC):
    if not char.db.general_skill_mastery_levels:
        char.db.general_skill_mastery_levels = {}
    char.db.general_skill_mastery_levels[skills.ENCHANTING.value] = mastery.value


def _learn_enchant_ruby(char):
    if not char.db.recipe_book:
        char.db.recipe_book = {}
    char.db.recipe_book["enchant_ruby"] = True


def _instant_delay(seconds, callback, *args, **kwargs):
    callback(*args, **kwargs)


# ── Table data structure validation ───────────────────────────────────

class TestTableStructure(TestCase):
    """Verify gem tables are in the correct format for DiceRoller."""

    def test_ruby_basic_has_10_entries(self):
        """BASIC ruby table should have 10 entries covering 1-100."""
        self.assertEqual(len(RUBY_ENCHANT_TABLE[1]), 10)

    def test_ruby_basic_entries_are_tuples(self):
        """Each entry should be a (range_str, effects_list) tuple."""
        for entry in RUBY_ENCHANT_TABLE[1]:
            self.assertIsInstance(entry, tuple)
            self.assertEqual(len(entry), 2)
            self.assertIsInstance(entry[0], str)
            self.assertIsInstance(entry[1], list)

    def test_ruby_basic_covers_full_range(self):
        """Table ranges should cover 1-100 with no gaps."""
        ranges = []
        for range_str, _ in RUBY_ENCHANT_TABLE[1]:
            parts = range_str.split("-")
            ranges.append((int(parts[0]), int(parts[1])))
        # Should start at 1 and end at 100
        self.assertEqual(ranges[0][0], 1)
        self.assertEqual(ranges[-1][1], 100)
        # No gaps between entries
        for i in range(1, len(ranges)):
            self.assertEqual(ranges[i][0], ranges[i - 1][1] + 1)

    def test_restriction_table_has_3_entries(self):
        """Restriction table should have 3 entries."""
        self.assertEqual(len(RESTRICTION_TABLE), 3)

    def test_restriction_table_covers_full_range(self):
        """Restriction table should cover 1-100."""
        ranges = []
        for range_str, _ in RESTRICTION_TABLE:
            parts = range_str.split("-")
            ranges.append((int(parts[0]), int(parts[1])))
        self.assertEqual(ranges[0][0], 1)
        self.assertEqual(ranges[-1][1], 100)

    def test_restriction_table_types(self):
        """Restriction table should contain race, class, and none types."""
        types = {entry[1] for entry in RESTRICTION_TABLE}
        self.assertEqual(types, {"race", "class", "none"})


# ── roll_gem_enchantment — effect rolls ───────────────────────────────

class TestRollGemEffects(TestCase):
    """Test that roll_gem_enchantment returns correct effects via DiceRoller."""

    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_initiative_bonus(self, mock_roll):
        """Should return initiative_bonus effects when rolled."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "none"]
        effects, restrictions = roll_gem_enchantment("enchanted_ruby", 1)
        self.assertEqual(effects, [{"type": "stat_bonus", "stat": "initiative_bonus", "value": 1}])
        self.assertEqual(restrictions, {})

    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_stealth_bonus(self, mock_roll):
        """Should return stealth_bonus effects when rolled."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[1], "none"]
        effects, _ = roll_gem_enchantment("enchanted_ruby", 1)
        self.assertEqual(effects, [{"type": "stat_bonus", "stat": "stealth_bonus", "value": 1}])

    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_perception_bonus(self, mock_roll):
        """Should return perception_bonus effects when rolled."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[2], "none"]
        effects, _ = roll_gem_enchantment("enchanted_ruby", 1)
        self.assertEqual(effects, [{"type": "stat_bonus", "stat": "perception_bonus", "value": 1}])

    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_detect_invis_condition(self, mock_roll):
        """Should return detect_invis condition when rolled."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[3], "none"]
        effects, _ = roll_gem_enchantment("enchanted_ruby", 1)
        self.assertEqual(effects, [{"type": "condition", "condition": "detect_invis"}])

    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_darkvision_condition(self, mock_roll):
        """Should return darkvision condition when rolled."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[4], "none"]
        effects, _ = roll_gem_enchantment("enchanted_ruby", 1)
        self.assertEqual(effects, [{"type": "condition", "condition": "darkvision"}])

    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_fly_condition(self, mock_roll):
        """Should return fly condition when rolled."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[5], "none"]
        effects, _ = roll_gem_enchantment("enchanted_ruby", 1)
        self.assertEqual(effects, [{"type": "condition", "condition": "fly"}])

    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_water_breathing_condition(self, mock_roll):
        """Should return water_breathing condition when rolled."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[6], "none"]
        effects, _ = roll_gem_enchantment("enchanted_ruby", 1)
        self.assertEqual(effects, [{"type": "condition", "condition": "water_breathing"}])

    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_blessed_condition(self, mock_roll):
        """Should return blessed condition when rolled."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[7], "none"]
        effects, _ = roll_gem_enchantment("enchanted_ruby", 1)
        self.assertEqual(effects, [{"type": "condition", "condition": "blessed"}])

    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_alert_condition(self, mock_roll):
        """Should return alert condition when rolled."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[8], "none"]
        effects, _ = roll_gem_enchantment("enchanted_ruby", 1)
        self.assertEqual(effects, [{"type": "condition", "condition": "alert"}])

    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_hit_and_damage_bonus(self, mock_roll):
        """Should return +1 hit AND +1 damage when rolled."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[9], "none"]
        effects, _ = roll_gem_enchantment("enchanted_ruby", 1)
        self.assertEqual(len(effects), 2)
        self.assertIn({"type": "stat_bonus", "stat": "total_hit_bonus", "value": 1}, effects)
        self.assertIn({"type": "stat_bonus", "stat": "total_damage_bonus", "value": 1}, effects)


# ── roll_gem_enchantment — restriction rolls ──────────────────────────

class TestRollGemRestrictions(TestCase):
    """Test restriction table outcomes."""

    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_no_restriction(self, mock_roll):
        """Restriction type 'none' should give empty restrictions dict."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "none"]
        _, restrictions = roll_gem_enchantment("enchanted_ruby", 1)
        self.assertEqual(restrictions, {})

    @patch("world.recipes.enchanting.gem_tables.random.choice")
    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_race_restriction(self, mock_roll, mock_choice):
        """Restriction type 'race' should give a race restriction."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "race"]
        mock_choice.return_value = "human"
        _, restrictions = roll_gem_enchantment("enchanted_ruby", 1)
        self.assertIn("required_races", restrictions)
        self.assertEqual(restrictions["required_races"], ["human"])

    @patch("world.recipes.enchanting.gem_tables.random.choice")
    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_class_restriction(self, mock_roll, mock_choice):
        """Restriction type 'class' should give a class restriction."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "class"]
        mock_choice.return_value = "warrior"
        _, restrictions = roll_gem_enchantment("enchanted_ruby", 1)
        self.assertIn("required_classes", restrictions)
        self.assertEqual(restrictions["required_classes"], ["warrior"])

    @patch("world.recipes.enchanting.gem_tables.random.choice")
    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_race_restriction_uses_non_remort_races(self, mock_roll, mock_choice):
        """Race restriction should pick from get_available_races(0) pool."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "race"]
        mock_choice.return_value = "elf"
        roll_gem_enchantment("enchanted_ruby", 1)
        call_args = mock_choice.call_args[0][0]
        self.assertIsInstance(call_args, list)
        self.assertGreater(len(call_args), 0)

    @patch("world.recipes.enchanting.gem_tables.random.choice")
    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_class_restriction_uses_base_classes(self, mock_roll, mock_choice):
        """Class restriction should pick from get_available_char_classes(0) pool."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "class"]
        mock_choice.return_value = "mage"
        roll_gem_enchantment("enchanted_ruby", 1)
        call_args = mock_choice.call_args[0][0]
        self.assertIsInstance(call_args, list)
        self.assertGreater(len(call_args), 0)


# ── roll_gem_enchantment — edge cases ─────────────────────────────────

class TestRollGemEdgeCases(TestCase):
    """Test error handling and mastery fallback."""

    def test_unknown_table_key_raises(self):
        """Unknown table key should raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            roll_gem_enchantment("enchanted_sapphire", 1)
        self.assertIn("Unknown gem enchant table", str(ctx.exception))

    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_mastery_fallback(self, mock_roll):
        """Mastery level 3 should fall back to level 1 table (only one defined)."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "none"]
        effects, _ = roll_gem_enchantment("enchanted_ruby", 3)
        self.assertEqual(effects, [{"type": "stat_bonus", "stat": "initiative_bonus", "value": 1}])

    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_mastery_5_falls_back(self, mock_roll):
        """GM mastery should still work by falling back to BASIC table."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[9], "none"]
        effects, _ = roll_gem_enchantment("enchanted_ruby", 5)
        self.assertEqual(len(effects), 2)  # hit + damage

    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    def test_dice_roller_called_with_correct_args(self, mock_roll):
        """Should call dice.roll_random_table with '1d100' and the correct tables."""
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "none"]
        roll_gem_enchantment("enchanted_ruby", 1)
        # First call: effects table
        self.assertEqual(mock_roll.call_args_list[0][0][0], "1d100")
        self.assertEqual(mock_roll.call_args_list[0][0][1], RUBY_ENCHANT_TABLE[1])
        # Second call: restriction table
        self.assertEqual(mock_roll.call_args_list[1][0][0], "1d100")
        self.assertEqual(mock_roll.call_args_list[1][0][1], RESTRICTION_TABLE)


# ── CmdCraft integration — enchanting in wizard's workshop ────────────

class TestCmdCraftEnchantRuby(EvenniaCommandTest):
    """Test enchanting a ruby via cmd_craft in a wizard's workshop."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Configure room as wizard's workshop
        self.room1.db.crafting_type = "wizards_workshop"
        self.room1.db.mastery_level = 1  # BASIC
        self.room1.db.craft_cost = 5
        # Give character enchanting skill and recipe
        _give_enchanting_skill(self.char1)
        _learn_enchant_ruby(self.char1)
        # Give resources: 2 Arcane Dust (15) + 1 Ruby (33)
        _give_resources(self.char1, {15: 5, 33: 3})
        _give_gold(self.char1, 50)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_enchant_sets_gem_effects(self, mock_assign, mock_spawn,
                                      mock_roll, mock_delay):
        """Successful enchant should set gem_effects on the spawned item."""
        mock_assign.return_value = TOKEN_ID
        mock_item = MagicMock()
        mock_spawn.return_value = mock_item
        fly_effects = [{"type": "condition", "condition": "fly"}]
        mock_roll.side_effect = [fly_effects, "none"]

        self.call(CmdCraft(), "enchanted ruby", inputs=["y"])

        self.assertEqual(mock_item.db.gem_effects, fly_effects)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_enchant_sets_gem_restrictions(self, mock_assign, mock_spawn,
                                           mock_roll, mock_delay):
        """Enchanting with a race restriction roll should set gem_restrictions."""
        mock_assign.return_value = TOKEN_ID
        mock_item = MagicMock()
        mock_spawn.return_value = mock_item
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "race"]

        with patch("world.recipes.enchanting.gem_tables.random.choice",
                   return_value="dwarf"):
            self.call(CmdCraft(), "enchanted ruby", inputs=["y"])

        self.assertEqual(mock_item.db.gem_restrictions, {"required_races": ["dwarf"]})

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_enchant_no_restriction(self, mock_assign, mock_spawn,
                                     mock_roll, mock_delay):
        """Restriction type 'none' should set empty gem_restrictions."""
        mock_assign.return_value = TOKEN_ID
        mock_item = MagicMock()
        mock_spawn.return_value = mock_item
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "none"]

        self.call(CmdCraft(), "enchanted ruby", inputs=["y"])

        self.assertEqual(mock_item.db.gem_restrictions, {})

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_enchant_consumes_resources(self, mock_assign, mock_spawn,
                                        mock_roll, mock_delay):
        """Enchanting should consume 2 Arcane Dust + 1 Ruby."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "none"]

        self.call(CmdCraft(), "enchanted ruby", inputs=["y"])

        # 2 Arcane Dust consumed (had 5)
        self.assertEqual(self.char1.get_resource(15), 3)
        # 1 Ruby consumed (had 3)
        self.assertEqual(self.char1.get_resource(33), 2)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_enchant_consumes_gold(self, mock_assign, mock_spawn,
                                    mock_roll, mock_delay):
        """Enchanting should consume workshop fee gold."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "none"]

        self.call(CmdCraft(), "enchanted ruby", inputs=["y"])

        # Workshop fee = 5, had 50
        self.assertEqual(self.char1.get_gold(), 45)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_enchant_shows_success_message(self, mock_assign, mock_spawn,
                                            mock_roll, mock_delay):
        """Success message should use 'enchant' verb."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "none"]

        result = self.call(CmdCraft(), "enchanted ruby", inputs=["y"])

        self.assertIn("You enchant a Enchanted Ruby!", result)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_enchant_progress_uses_enchanting_gerund(self, mock_assign,
                                                      mock_spawn,
                                                      mock_roll,
                                                      mock_delay):
        """Progress bar should use 'Enchanting' gerund."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "none"]

        result = self.call(CmdCraft(), "enchanted ruby", inputs=["y"])

        self.assertIn("Enchanting Enchanted Ruby...", result)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_enchant_spawns_correct_item_type(self, mock_assign, mock_spawn,
                                               mock_roll, mock_delay):
        """Should call assign_to_blank_token with 'Enchanted Ruby'."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "none"]

        self.call(CmdCraft(), "enchanted ruby", inputs=["y"])

        mock_assign.assert_called_once_with("Enchanted Ruby")
        mock_spawn.assert_called_once_with(TOKEN_ID, self.char1)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_enchant_awards_xp(self, mock_assign, mock_spawn,
                                mock_roll, mock_delay):
        """Enchanting should award BASIC craft XP (5)."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "none"]
        self.char1.experience_points = 0

        self.call(CmdCraft(), "enchanted ruby", inputs=["y"])

        self.assertEqual(self.char1.experience_points, 5)


# ── CmdCraft — enchanting validation failures ─────────────────────────

class TestCmdCraftEnchantValidation(EvenniaCommandTest):
    """Test validation failures specific to enchanting."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "wizards_workshop"
        self.room1.db.mastery_level = 1
        self.room1.db.craft_cost = 5
        _give_enchanting_skill(self.char1)
        _learn_enchant_ruby(self.char1)

    def test_insufficient_arcane_dust(self):
        """Should fail if not enough Arcane Dust."""
        _give_resources(self.char1, {15: 1, 33: 1})  # only 1 dust, need 2
        _give_gold(self.char1, 50)
        result = self.call(CmdCraft(), "enchanted ruby")
        self.assertIn("You don't have enough materials", result)

    def test_insufficient_ruby(self):
        """Should fail if no Ruby resource."""
        _give_resources(self.char1, {15: 5})  # dust but no ruby
        _give_gold(self.char1, 50)
        result = self.call(CmdCraft(), "enchanted ruby")
        self.assertIn("You don't have enough materials", result)

    def test_insufficient_gold(self):
        """Should fail if not enough gold for workshop fee."""
        _give_resources(self.char1, {15: 5, 33: 3})
        _give_gold(self.char1, 2)  # need 5
        result = self.call(CmdCraft(), "enchanted ruby")
        self.assertIn("You need 5 gold", result)

    def test_wrong_room_type(self):
        """Should not find recipe if in a smithy instead of wizard's workshop."""
        self.room1.db.crafting_type = "smithy"
        _give_resources(self.char1, {15: 5, 33: 3})
        _give_gold(self.char1, 50)
        result = self.call(CmdCraft(), "enchanted ruby")
        self.assertIn("You don't know any recipes", result)

    def test_no_enchanting_skill(self):
        """Should fail if character lacks enchanting skill mastery."""
        self.char1.db.general_skill_mastery_levels = {}  # clear skills
        _give_resources(self.char1, {15: 5, 33: 3})
        _give_gold(self.char1, 50)
        result = self.call(CmdCraft(), "enchanted ruby")
        self.assertIn("You need at least", result)


# ── CmdCraft — enchant alias works ────────────────────────────────────

class TestCmdCraftEnchantAlias(EvenniaCommandTest):
    """Test that 'enchant' command alias works in wizard's workshop."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "wizards_workshop"
        self.room1.db.mastery_level = 1
        self.room1.db.craft_cost = 5
        _give_enchanting_skill(self.char1)
        _learn_enchant_ruby(self.char1)
        _give_resources(self.char1, {15: 5, 33: 3})
        _give_gold(self.char1, 50)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("world.recipes.enchanting.gem_tables.dice.roll_random_table")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_enchant_alias_works(self, mock_assign, mock_spawn,
                                  mock_roll, mock_delay):
        """'enchant ruby' should work via the enchant alias."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        mock_roll.side_effect = [_RUBY_BASIC_EFFECTS[0], "none"]

        result = self.call(CmdCraft(), "enchanted ruby", cmdstring="enchant",
                           inputs=["y"])

        mock_assign.assert_called_once_with("Enchanted Ruby")
        self.assertIn("You enchant a Enchanted Ruby!", result)


# ── CmdCraft — spawn failure refund for enchanting ────────────────────

class TestCmdCraftEnchantRefund(EvenniaCommandTest):
    """Test that spawn failure during enchanting refunds all resources."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "wizards_workshop"
        self.room1.db.mastery_level = 1
        self.room1.db.craft_cost = 5
        _give_enchanting_skill(self.char1)
        _learn_enchant_ruby(self.char1)
        _give_resources(self.char1, {15: 5, 33: 3})
        _give_gold(self.char1, 50)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_spawn_failure_refunds_resources(self, mock_assign, mock_delay):
        """Spawn failure should refund Arcane Dust, Ruby, and gold."""
        mock_assign.side_effect = ValueError("No blank tokens")

        self.call(CmdCraft(), "enchanted ruby", inputs=["y"])

        # All resources refunded
        self.assertEqual(self.char1.get_resource(15), 5)
        self.assertEqual(self.char1.get_resource(33), 3)
        self.assertEqual(self.char1.get_gold(), 50)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_spawn_failure_clears_processing(self, mock_assign, mock_delay):
        """Spawn failure should clear ndb.is_processing."""
        mock_assign.side_effect = ValueError("No blank tokens")

        self.call(CmdCraft(), "enchanted ruby", inputs=["y"])

        self.assertFalse(self.char1.ndb.is_processing)
