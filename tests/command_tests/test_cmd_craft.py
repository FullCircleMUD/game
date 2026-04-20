"""
Tests for CmdCraft, CmdRecipes (character), and CmdAvailable (room).

CmdCraft validates recipes, ingredients, gold, room type/level, then
delays with a progress bar before spawning NFT items via BaseNFTItem
factory methods.

Mocks BaseNFTItem.assign_to_blank_token and BaseNFTItem.spawn_into
(never mock NFTService directly — all calls go through BaseNFTItem).

The crafting delay uses utils.delay() which is mocked to execute callbacks
immediately (no actual waiting in tests).

evennia test --settings settings tests.command_tests.test_cmd_craft
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.room_specific_cmds.crafting.cmd_craft import CmdCraft
from commands.room_specific_cmds.crafting.cmd_available import CmdAvailable
from commands.all_char_cmds.cmd_recipes import CmdRecipes
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
TOKEN_ID = 101


def _give_resources(char, resources):
    """Give resources via service layer so mirror DB stays in sync."""
    for res_id, amount in resources.items():
        char.receive_resource_from_reserve(res_id, amount)


def _give_gold(char, amount):
    """Give gold via service layer so mirror DB stays in sync."""
    char.receive_gold_from_reserve(amount)


def _give_carpenter_skill(char, mastery=MasteryLevel.BASIC):
    """Give a character carpenter skill at given mastery."""
    if not char.db.general_skill_mastery_levels:
        char.db.general_skill_mastery_levels = {}
    char.db.general_skill_mastery_levels[skills.CARPENTER.value] = mastery.value


def _learn_training_longsword(char):
    """Teach the training longsword recipe directly."""
    if not char.db.recipe_book:
        char.db.recipe_book = {}
    char.db.recipe_book["training_longsword"] = True


def _instant_delay(seconds, callback, *args, **kwargs):
    """Mock for utils.delay — executes callback immediately."""
    callback(*args, **kwargs)


# ── Craft Command — Success ─────────────────────────────────────────

class TestCmdCraftSuccess(EvenniaCommandTest):
    """Test successful crafting."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Configure room as woodshop
        self.room1.db.crafting_type = "woodshop"
        self.room1.db.mastery_level = 1  # BASIC
        self.room1.db.craft_cost = 2
        # Give character skill and recipe
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        # Give resources: 2 Timber (id=7) + enough gold (room fee = 2)
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_craft_success(self, mock_assign, mock_spawn, mock_delay):
        """Crafting should consume resources, gold, and spawn an item."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()

        self.call(CmdCraft(), "training longsword", inputs=["y"])

        # Resources consumed: 3 Timber
        self.assertEqual(self.char1.get_resource(7), 2)
        # Gold consumed: 2 (workshop fee only)
        self.assertEqual(self.char1.get_gold(), 18)
        mock_assign.assert_called_once_with("Training Longsword")
        mock_spawn.assert_called_once_with(TOKEN_ID, self.char1)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_craft_shows_success_message(self, mock_assign, mock_spawn,
                                         mock_delay):
        """Crafting should show a success message with the item name."""
        mock_assign.return_value = TOKEN_ID
        mock_item = MagicMock()
        mock_item.key = "Training Longsword"
        mock_spawn.return_value = mock_item

        result = self.call(CmdCraft(), "training longsword", inputs=["y"])
        self.assertIn("You carve a Training Longsword!", result)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_craft_substring_match(self, mock_assign, mock_spawn, mock_delay):
        """Partial recipe name should match."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()

        self.call(CmdCraft(), "longsword", inputs=["y"])

        mock_assign.assert_called_once()
        self.assertEqual(self.char1.get_resource(7), 2)


# ── Craft Command — Validation Failures ──────────────────────────────

class TestCmdCraftValidation(EvenniaCommandTest):
    """Test craft command validation failures."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "woodshop"
        self.room1.db.mastery_level = 1
        self.room1.db.craft_cost = 2
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)

    def test_no_args(self):
        """Craft with no arguments should show usage."""
        self.call(CmdCraft(), "", "Craft what?")

    def test_unknown_recipe(self):
        """Craft with unknown recipe name should fail."""
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)
        self.call(
            CmdCraft(), "iron longsword",
            "You don't know a recipe by that name",
        )

    def test_insufficient_resources(self):
        """Craft without enough ingredients should fail."""
        _give_resources(self.char1, {7: 1})  # need 2 Timber
        _give_gold(self.char1, 20)
        self.call(CmdCraft(), "training longsword", "You don't have enough materials")

    def test_insufficient_gold(self):
        """Craft without enough gold should fail."""
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 1)  # need 2 (workshop fee)
        self.call(CmdCraft(), "training longsword", "You need 2 gold")

    def test_room_mastery_too_low(self):
        """Craft in a room below recipe mastery should fail."""
        self.room1.db.mastery_level = 0  # below BASIC (1)
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)
        self.call(
            CmdCraft(), "training longsword",
            "This workshop isn't advanced enough",
        )

    def test_no_known_recipes(self):
        """Craft with no recipes known for this room type should fail."""
        self.char1.db.recipe_book = {}
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)
        self.call(
            CmdCraft(), "training longsword",
            "You don't know any recipes",
        )

    def test_character_mastery_too_low(self):
        """Craft with insufficient character mastery should fail."""
        # Set carpenter to UNSKILLED (0) — recipe requires BASIC (1)
        _give_carpenter_skill(self.char1, MasteryLevel.UNSKILLED)
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)
        self.call(
            CmdCraft(), "training longsword",
            "You need at least",
        )


# ── Craft Command — Cancellation ─────────────────────────────────────

class TestCmdCraftCancel(EvenniaCommandTest):
    """Test craft command Y/N cancellation."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "woodshop"
        self.room1.db.mastery_level = 1
        self.room1.db.craft_cost = 2
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)

    def test_cancel_keeps_resources(self):
        """Answering 'n' should not consume resources or gold."""
        self.call(CmdCraft(), "training longsword", inputs=["n"])
        self.assertEqual(self.char1.get_resource(7), 5)
        self.assertEqual(self.char1.get_gold(), 20)

    def test_cancel_shows_message(self):
        """Cancelling should show cancelled message."""
        self.call(
            CmdCraft(), "training longsword",
            "Crafting cancelled.",
            inputs=["n"],
        )


# ── Craft Command — Spawn Failure Refund ─────────────────────────────

class TestCmdCraftRefund(EvenniaCommandTest):
    """Test that spawn failures refund resources and gold."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "woodshop"
        self.room1.db.mastery_level = 1
        self.room1.db.craft_cost = 2
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_assign_failure_refunds(self, mock_assign, mock_delay):
        """If assign_to_blank_token raises, resources and gold are refunded."""
        mock_assign.side_effect = ValueError("No blank tokens available")

        result = self.call(
            CmdCraft(), "training longsword",
            inputs=["y"],
        )
        self.assertIn("Crafting failed:", result)
        # Refunded
        self.assertEqual(self.char1.get_resource(7), 5)
        self.assertEqual(self.char1.get_gold(), 20)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_refund_clears_processing_flag(self, mock_assign, mock_delay):
        """Spawn failure should clear ndb.is_processing."""
        mock_assign.side_effect = ValueError("No blank tokens available")

        self.call(CmdCraft(), "training longsword", inputs=["y"])
        self.assertFalse(self.char1.ndb.is_processing)


# ── Craft Command — Progress Bar ─────────────────────────────────────

class TestCmdCraftProgress(EvenniaCommandTest):
    """Test progress bar messages during crafting delay."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "woodshop"
        self.room1.db.mastery_level = 1  # BASIC
        self.room1.db.craft_cost = 2
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_progress_bar_basic(self, mock_assign, mock_spawn, mock_delay):
        """BASIC recipe should show 2-tick progress bar."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()

        result = self.call(CmdCraft(), "training longsword", inputs=["y"])
        # BASIC = 2 ticks: tick 1 = [#####-----], tick 2 = [##########] Done!
        self.assertIn("[#####-----]", result)
        self.assertIn("[##########] Done!", result)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_progress_uses_room_verb(self, mock_assign, mock_spawn, mock_delay):
        """Progress messages should use the room-specific gerund."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()

        result = self.call(CmdCraft(), "training longsword", inputs=["y"])
        # Woodshop → "Carving"
        self.assertIn("Carving Training Longsword...", result)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_is_processing_cleared(self, mock_assign, mock_spawn, mock_delay):
        """ndb.is_processing should be cleared after crafting completes."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()

        self.call(CmdCraft(), "training longsword", inputs=["y"])
        self.assertFalse(self.char1.ndb.is_processing)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_delay_called_with_correct_interval(self, mock_assign, mock_spawn,
                                                mock_delay):
        """Delay should be called with CRAFT_TICK_SECONDS (3s) intervals."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()

        self.call(CmdCraft(), "training longsword", inputs=["y"])
        # BASIC = 2 ticks, each delay call uses 3 seconds
        for call_args in mock_delay.call_args_list:
            self.assertEqual(call_args[0][0], 3)


# ── Craft Command — Busy Lock ────────────────────────────────────────

class TestCmdCraftBusy(EvenniaCommandTest):
    """Test that concurrent crafting/processing is blocked."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "woodshop"
        self.room1.db.mastery_level = 1
        self.room1.db.craft_cost = 2
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)

    def test_busy_rejected(self):
        """Should reject if already processing/crafting."""
        self.char1.ndb.is_processing = True
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)
        result = self.call(CmdCraft(), "training longsword")
        self.assertIn("already busy", result.lower())
        # Resources should NOT be consumed
        self.assertEqual(self.char1.get_resource(7), 5)
        self.assertEqual(self.char1.get_gold(), 20)


# ── Craft Command — XP Award ────────────────────────────────────────

class TestCmdCraftXP(EvenniaCommandTest):
    """Test XP awarded on successful crafting."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "woodshop"
        self.room1.db.mastery_level = 1
        self.room1.db.craft_cost = 2
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_xp_awarded(self, mock_assign, mock_spawn, mock_delay):
        """Crafting should award XP based on recipe mastery level."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        self.char1.experience_points = 0

        self.call(CmdCraft(), "training longsword", inputs=["y"])
        # BASIC (mastery 1) = 5 XP, multiplier 1.0
        self.assertEqual(self.char1.experience_points, 5)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_xp_room_multiplier(self, mock_assign, mock_spawn, mock_delay):
        """Room multiplier should scale craft XP."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        self.room1.db.craft_xp_multiplier = 2.0
        self.char1.experience_points = 0

        self.call(CmdCraft(), "training longsword", inputs=["y"])
        # BASIC (5) * 2.0 = 10
        self.assertEqual(self.char1.experience_points, 10)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_no_xp_on_failure(self, mock_assign, mock_delay):
        """Should not award XP when crafting fails (spawn error)."""
        mock_assign.side_effect = ValueError("No blank tokens")
        self.char1.experience_points = 0

        self.call(CmdCraft(), "training longsword", inputs=["y"])
        self.assertEqual(self.char1.experience_points, 0)


# ── Recipes Command (Character) ─────────────────────────────────────

class TestCmdRecipes(EvenniaCommandTest):
    """Test character-level recipes command."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()

    def test_empty_recipe_book(self):
        """Recipes with no learned recipes should show empty message."""
        self.call(CmdRecipes(), "", "Your recipe book is empty.")

    def test_summary_shows_skill_and_count(self):
        """Bare recipes shows summary with skill name and tier count."""
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        result = self.call(CmdRecipes(), "")
        self.assertIn("Carpenter", result)
        self.assertIn("BASIC", result)
        self.assertIn("1", result)  # 1 BASIC recipe
        self.assertNotIn("Training Longsword", result)  # detail hidden

    def test_drill_down_shows_recipe_detail(self):
        """recipes <skill> shows full recipe details."""
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        result = self.call(CmdRecipes(), "carpenter")
        self.assertIn("Training Longsword", result)
        self.assertIn("Carpenter", result)
        self.assertIn("BASIC", result)

    def test_shows_mastery_level(self):
        """Summary should show the character's mastery level for each skill."""
        _give_carpenter_skill(self.char1, MasteryLevel.SKILLED)
        _learn_training_longsword(self.char1)
        result = self.call(CmdRecipes(), "")
        self.assertIn("SKILLED", result)

    def test_summary_multiple_skills(self):
        """Summary groups recipes by skill when multiple skills known."""
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        # Also learn a blacksmith recipe
        if not self.char1.db.general_skill_mastery_levels:
            self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.general_skill_mastery_levels[skills.BLACKSMITH.value] = MasteryLevel.BASIC.value
        self.char1.db.recipe_book["bronze_dagger"] = True
        result = self.call(CmdRecipes(), "")
        self.assertIn("Carpenter", result)
        self.assertIn("Blacksmith", result)

    def test_summary_multiple_tiers(self):
        """Summary shows separate counts for different mastery tiers."""
        _give_carpenter_skill(self.char1, MasteryLevel.SKILLED)
        _learn_training_longsword(self.char1)  # BASIC recipe
        # Also learn a SKILLED blacksmith recipe
        if not self.char1.db.general_skill_mastery_levels:
            self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.general_skill_mastery_levels[skills.BLACKSMITH.value] = MasteryLevel.SKILLED.value
        self.char1.db.recipe_book["bronze_dagger"] = True       # BASIC
        self.char1.db.recipe_book["bronze_greatsword"] = True   # SKILLED
        result = self.call(CmdRecipes(), "blacksmith")
        self.assertIn("BASIC", result)
        self.assertIn("SKILLED", result)
        self.assertIn("Bronze Dagger", result)
        self.assertIn("Bronze Greatsword", result)

    def test_drill_down_partial_match(self):
        """Partial skill name should match (e.g. 'carp' → carpenter)."""
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        result = self.call(CmdRecipes(), "carp")
        self.assertIn("Training Longsword", result)
        self.assertIn("Carpenter", result)

    def test_drill_down_unknown_skill(self):
        """Unknown skill argument shows error with hint."""
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        result = self.call(CmdRecipes(), "zzz_nonexistent")
        self.assertIn("don't have any recipes", result)
        self.assertIn("recipes", result)  # hint to use bare command

    def test_drill_down_shows_nft_ingredients(self):
        """Detail view should show NFT ingredients alongside resources."""
        if not self.char1.db.general_skill_mastery_levels:
            self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.general_skill_mastery_levels[skills.ENCHANTING.value] = MasteryLevel.BASIC.value
        if not self.char1.db.recipe_book:
            self.char1.db.recipe_book = {}
        self.char1.db.recipe_book["defenders_helm"] = True
        result = self.call(CmdRecipes(), "enchanting")
        self.assertIn("Defender's Helm", result)
        self.assertIn("Bronze Helm", result)  # NFT ingredient displayed

    def test_enchanting_recipes_in_summary(self):
        """Enchanting recipes should appear in the summary view."""
        if not self.char1.db.general_skill_mastery_levels:
            self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.general_skill_mastery_levels[skills.ENCHANTING.value] = MasteryLevel.BASIC.value
        if not self.char1.db.recipe_book:
            self.char1.db.recipe_book = {}
        self.char1.db.recipe_book["defenders_helm"] = True
        result = self.call(CmdRecipes(), "")
        self.assertIn("Enchanting", result)

    def test_summary_shows_hint_text(self):
        """Summary should include hint for drill-down command."""
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        result = self.call(CmdRecipes(), "")
        self.assertIn("recipes carpenter", result)


# ── Available Command (Room) ─────────────────────────────────────────

class TestCmdAvailable(EvenniaCommandTest):
    """Test room-specific available command."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "woodshop"
        self.room1.db.mastery_level = 1
        self.room1.db.craft_cost = 2

    def test_no_recipes_known(self):
        """Available with no known recipes should show message."""
        self.call(CmdAvailable(), "", "You don't know any recipes")

    def test_shows_available_recipe(self):
        """Available should show recipes matching this room type."""
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        _give_resources(self.char1, {7: 5})
        result = self.call(CmdAvailable(), "")
        self.assertIn("Training Longsword", result)
        self.assertIn("Timber", result)

    def test_shows_workshop_fee(self):
        """Available should show workshop fee."""
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        result = self.call(CmdAvailable(), "")
        self.assertIn("Workshop fee: 2 gold", result)

    def test_shows_room_level_warning(self):
        """Recipes above room level should show a warning."""
        self.room1.db.mastery_level = 0  # below BASIC
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        result = self.call(CmdAvailable(), "")
        self.assertIn("needs", result.lower())


# ── Craft Command — Potion Mastery Scaling ─────────────────────────

def _give_alchemist_skill(char, mastery=MasteryLevel.BASIC):
    """Give a character alchemist skill at given mastery."""
    if not char.db.general_skill_mastery_levels:
        char.db.general_skill_mastery_levels = {}
    char.db.general_skill_mastery_levels[skills.ALCHEMIST.value] = mastery.value


def _learn_cats_grace(char):
    """Teach the Cat's Grace potion recipe."""
    if not char.db.recipe_book:
        char.db.recipe_book = {}
    char.db.recipe_book["cats_grace"] = True


class TestCmdCraftPotionMasteryRouting(EvenniaCommandTest):
    """Test that potion recipes route to the correct tier-specific NFTItemType.

    Effects are baked into prototypes and NFTItemType.default_metadata —
    no post-spawn scaling. These tests verify the mastery_tiered routing
    picks the correct NFTItemType name for assign_to_blank_token.
    """

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Configure room as apothecary
        self.room1.db.crafting_type = "apothecary"
        self.room1.db.mastery_level = 5  # GM — allows all recipes
        self.room1.db.craft_cost = 2
        # Give resources: 1 Moonpetal Essence (13) + 2 Vipervine (18)
        _give_resources(self.char1, {13: 10, 18: 20})
        _give_gold(self.char1, 50)
        _learn_cats_grace(self.char1)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_brew_basic_routes_to_watery(self, mock_assign, mock_spawn, mock_delay):
        """BASIC brewer should route to Watery NFTItemType."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        _give_alchemist_skill(self.char1, MasteryLevel.BASIC)

        self.call(CmdCraft(), "cat's grace", inputs=["y"])

        mock_assign.assert_called_once_with("Watery Potion of Cat's Grace")

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_brew_skilled_routes_to_weak(self, mock_assign, mock_spawn, mock_delay):
        """SKILLED brewer should route to Weak NFTItemType."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        _give_alchemist_skill(self.char1, MasteryLevel.SKILLED)

        self.call(CmdCraft(), "cat's grace", inputs=["y"])

        mock_assign.assert_called_once_with("Weak Potion of Cat's Grace")

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_brew_expert_routes_to_standard(self, mock_assign, mock_spawn, mock_delay):
        """EXPERT brewer should route to Standard NFTItemType."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        _give_alchemist_skill(self.char1, MasteryLevel.EXPERT)

        self.call(CmdCraft(), "cat's grace", inputs=["y"])

        mock_assign.assert_called_once_with("Standard Potion of Cat's Grace")

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_brew_master_routes_to_potent(self, mock_assign, mock_spawn, mock_delay):
        """MASTER brewer should route to Potent NFTItemType."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        _give_alchemist_skill(self.char1, MasteryLevel.MASTER)

        self.call(CmdCraft(), "cat's grace", inputs=["y"])

        mock_assign.assert_called_once_with("Potent Potion of Cat's Grace")

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_brew_grandmaster_routes_to_ascendant(self, mock_assign, mock_spawn, mock_delay):
        """GRANDMASTER brewer should route to Ascendant NFTItemType."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        _give_alchemist_skill(self.char1, MasteryLevel.GRANDMASTER)

        self.call(CmdCraft(), "cat's grace", inputs=["y"])

        mock_assign.assert_called_once_with("Ascendant Potion of Cat's Grace")

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_brew_restore_potion_routes_by_mastery(self, mock_assign, mock_spawn,
                                                    mock_delay):
        """Restore potion should route to tier-specific NFTItemType."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        _give_alchemist_skill(self.char1, MasteryLevel.EXPERT)

        # Learn Life's Essence recipe
        if not self.char1.db.recipe_book:
            self.char1.db.recipe_book = {}
        self.char1.db.recipe_book["lifes_essence"] = True
        # Ingredients: 1 Moonpetal Essence (13) + 2 Bloodmoss (14)
        _give_resources(self.char1, {14: 5})

        self.call(CmdCraft(), "life's essence", inputs=["y"])

        mock_assign.assert_called_once_with("Standard Potion of Life's Essence")

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_non_tiered_recipe_unaffected(self, mock_assign, mock_spawn,
                                          mock_delay):
        """A recipe without mastery_tiered should use recipe name directly."""
        mock_assign.return_value = TOKEN_ID
        mock_item = MagicMock()
        mock_item.key = "Training Longsword"
        mock_spawn.return_value = mock_item

        # Switch room to woodshop and give carpenter skill + recipe
        self.room1.db.crafting_type = "woodshop"
        _give_carpenter_skill(self.char1)
        _learn_training_longsword(self.char1)
        _give_resources(self.char1, {7: 5})

        self.call(CmdCraft(), "training longsword", inputs=["y"])

        # Non-tiered recipe uses recipe name, NOT quality-prefixed
        mock_assign.assert_called_once_with("Training Longsword")

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_success_message_uses_item_key(self, mock_assign, mock_spawn,
                                            mock_delay):
        """Success message should use item.key for the display name."""
        mock_assign.return_value = TOKEN_ID
        mock_item = MagicMock()
        mock_item.key = "Watery Potion of Cat's Grace"
        mock_spawn.return_value = mock_item
        _give_alchemist_skill(self.char1, MasteryLevel.BASIC)

        result = self.call(CmdCraft(), "cat's grace", inputs=["y"])

        self.assertIn("Watery Potion of Cat's Grace", result)


# ── Blank Wand Crafting (Phase 1 of the wand system) ────────────────


def _learn_recipe(char, recipe_key):
    """Teach an arbitrary recipe to the character."""
    if not char.db.recipe_book:
        char.db.recipe_book = {}
    char.db.recipe_book[recipe_key] = True


class TestCmdCraftBlankWands(EvenniaCommandTest):
    """Test that carpenters can craft blank wands at each tier.

    Phase 1 only validates that the 5 recipes exist and produce the
    expected NFTItemType names. The blank wands are inert BaseNFTItem
    components — their only role is to feed Phase 2 (future mage
    enchantment). Each test patches the NFT spawn helpers so we don't
    depend on the blank-token pool during unit tests.
    """

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "woodshop"
        self.room1.db.mastery_level = 5  # allow any tier recipe
        self.room1.db.craft_cost = 2

    def _prepare(self, mastery, recipe_key, resources):
        """Give the character skill + recipe + inputs for a single test."""
        _give_carpenter_skill(self.char1, mastery=mastery)
        _learn_recipe(self.char1, recipe_key)
        _give_resources(self.char1, resources)
        _give_gold(self.char1, 100)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_craft_training_wand_basic(self, mock_assign, mock_spawn, mock_delay):
        """A BASIC carpenter crafts a Training Wand from 1 Timber."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()

        self._prepare(MasteryLevel.BASIC, "training_wand", {7: 3})
        self.call(CmdCraft(), "training wand", inputs=["y"])

        mock_assign.assert_called_once_with("Training Wand")
        mock_spawn.assert_called_once_with(TOKEN_ID, self.char1)
        self.assertEqual(self.char1.get_resource(7), 2)  # 3 - 1

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_craft_apprentices_wand_skilled(self, mock_assign, mock_spawn, mock_delay):
        """A SKILLED carpenter crafts an Apprentice's Wand from 1 Timber."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()

        self._prepare(MasteryLevel.SKILLED, "apprentices_wand", {7: 3})
        self.call(CmdCraft(), "apprentice's wand", inputs=["y"])

        mock_assign.assert_called_once_with("Apprentice's Wand")
        self.assertEqual(self.char1.get_resource(7), 2)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_craft_wizards_wand_expert_ironwood(self, mock_assign, mock_spawn, mock_delay):
        """An EXPERT carpenter crafts a Wizard's Wand from 1 Ironwood Timber."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()

        self._prepare(MasteryLevel.EXPERT, "wizards_wand", {41: 3})
        self.call(CmdCraft(), "wizard's wand", inputs=["y"])

        mock_assign.assert_called_once_with("Wizard's Wand")
        self.assertEqual(self.char1.get_resource(41), 2)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_craft_masters_wand_master_ironwood(self, mock_assign, mock_spawn, mock_delay):
        """A MASTER carpenter crafts a Master's Wand from 1 Ironwood Timber."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()

        self._prepare(MasteryLevel.MASTER, "masters_wand", {41: 3})
        self.call(CmdCraft(), "master's wand", inputs=["y"])

        mock_assign.assert_called_once_with("Master's Wand")
        self.assertEqual(self.char1.get_resource(41), 2)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_craft_archmages_wand_gm_ironwood(self, mock_assign, mock_spawn, mock_delay):
        """A GRANDMASTER carpenter crafts an Archmage's Wand from 1 Ironwood Timber."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()

        self._prepare(MasteryLevel.GRANDMASTER, "archmages_wand", {41: 3})
        self.call(CmdCraft(), "archmage's wand", inputs=["y"])

        mock_assign.assert_called_once_with("Archmage's Wand")
        self.assertEqual(self.char1.get_resource(41), 2)

    def test_basic_carpenter_cannot_craft_apprentices_wand(self):
        """Mastery gate — BASIC carpenter is rejected for SKILLED recipe."""
        # Room mastery must be high enough, otherwise room is the gate, not skill.
        _give_carpenter_skill(self.char1, mastery=MasteryLevel.BASIC)
        _learn_recipe(self.char1, "apprentices_wand")
        _give_resources(self.char1, {7: 3})
        _give_gold(self.char1, 100)

        result = self.call(CmdCraft(), "apprentice's wand")
        # Error wording: "You need at least SKILLED mastery in Carpenter ..."
        self.assertIn("skilled mastery", result.lower())

    def test_wizards_wand_rejects_regular_timber(self):
        """EXPERT carpenter with regular Timber cannot craft a Wizard's Wand."""
        _give_carpenter_skill(self.char1, mastery=MasteryLevel.EXPERT)
        _learn_recipe(self.char1, "wizards_wand")
        # Only regular Timber (id 7), no Ironwood Timber (id 41).
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 100)

        result = self.call(CmdCraft(), "wizard's wand")
        # Error wording: "You don't have enough materials ... Ironwood Timber (have 0)"
        self.assertIn("ironwood timber", result.lower())
        self.assertIn("have 0", result.lower())


# ── Phase 2: Mage Wand Enchantment ────────────────────────────────────


def _give_enchanting_class_skill(char, mastery=MasteryLevel.BASIC):
    """Install enchanting as a class skill at the given mastery."""
    if not char.db.class_skill_mastery_levels:
        char.db.class_skill_mastery_levels = {}
    char.db.class_skill_mastery_levels[skills.ENCHANTING.value] = {
        "mastery": mastery.value,
        "classes": ["mage"],
    }


def _give_evocation_mastery(char, mastery=MasteryLevel.BASIC):
    """Install evocation school mastery."""
    if not char.db.class_skill_mastery_levels:
        char.db.class_skill_mastery_levels = {}
    char.db.class_skill_mastery_levels["evocation"] = {
        "mastery": mastery.value,
        "classes": ["mage"],
    }


def _learn_spell_direct(char, spell_key):
    """Put a spell directly into the character's spellbook."""
    if not char.db.spellbook:
        char.db.spellbook = {}
    char.db.spellbook[spell_key] = True


def _spawn_blank_wand(char, prototype_key):
    """Spawn a blank wand component (plain BaseNFTItem) into the character."""
    from evennia.utils import create
    obj = create.create_object(
        "typeclasses.items.base_nft_item.BaseNFTItem",
        key=prototype_key.replace("_", " ").title(),
        location=char,
    )
    obj.db.prototype_key = prototype_key
    return obj


class TestCmdCraftWandEnchant(EvenniaCommandTest):
    """Test wand enchantment — mage consumes blank + dust + spell → WandNFTItem.

    These tests verify the full craft flow for dynamic wand recipes:
      1. The wand post-spawn hook sets spell_key / charges correctly
      2. Pre-paid mana is deducted on success
      3. Insufficient mana aborts cleanly
      4. The blank wand is consumed on craft
      5. Mage-only mastery gate respects class_skill_mastery_levels
    """

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "wizards_workshop"
        self.room1.db.mastery_level = 5  # accept any tier
        self.room1.db.craft_cost = 2
        # Mage baseline
        _give_enchanting_class_skill(self.char1, MasteryLevel.GRANDMASTER)
        _give_evocation_mastery(self.char1, MasteryLevel.BASIC)
        _learn_spell_direct(self.char1, "magic_missile")
        _spawn_blank_wand(self.char1, "training_wand")
        _give_resources(self.char1, {16: 5})   # Arcane Dust
        _give_gold(self.char1, 100)
        # Plenty of mana for default test conditions
        self.char1.mana_max = 100
        self.char1.mana = 100

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_craft_wand_of_magic_missile(self, mock_assign, mock_spawn, mock_delay):
        """Mage crafts a Wand of Magic Missile — verify all state is set."""
        mock_assign.return_value = TOKEN_ID
        mock_item = MagicMock()
        mock_spawn.return_value = mock_item

        self.call(CmdCraft(), "wand of magic missile", inputs=["y"])

        # Generic NFTItemType "Enchanted Wand" is used, not the recipe name.
        mock_assign.assert_called_once_with("Enchanted Wand")
        mock_spawn.assert_called_once_with(TOKEN_ID, self.char1)

        # Wand state was set on the spawned item
        self.assertEqual(mock_item.spell_key, "magic_missile")
        self.assertEqual(mock_item.charges_remaining, 10)
        self.assertEqual(mock_item.charges_max, 10)
        self.assertEqual(mock_item.key, "Wand of Magic Missile")
        mock_item.persist_wand_state.assert_called_once()

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_wand_craft_deducts_prepaid_mana(self, mock_assign, mock_spawn, mock_delay):
        """Pre-paid mana should be deducted on successful craft.

        Magic Missile BASIC mana_cost = 5 per cast × 10 charges = 50 mana.
        """
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()
        self.char1.mana = 100

        self.call(CmdCraft(), "wand of magic missile", inputs=["y"])

        self.assertEqual(self.char1.mana, 50)

    def test_insufficient_mana_aborts_craft(self):
        """Character without enough mana should get an error and no state change."""
        self.char1.mana = 10
        original_blanks = len([
            o for o in self.char1.contents
            if getattr(o.db, "prototype_key", None) == "training_wand"
        ])
        original_dust = self.char1.get_resource(16)

        result = self.call(CmdCraft(), "wand of magic missile")

        self.assertIn("mana", result.lower())
        # State unchanged — no consumption happened
        self.assertEqual(self.char1.mana, 10)
        self.assertEqual(self.char1.get_resource(16), original_dust)
        remaining_blanks = len([
            o for o in self.char1.contents
            if getattr(o.db, "prototype_key", None) == "training_wand"
        ])
        self.assertEqual(remaining_blanks, original_blanks)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_blank_wand_is_consumed(self, mock_assign, mock_spawn, mock_delay):
        """The blank wand must be deleted from inventory after a successful craft."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()

        self.call(CmdCraft(), "wand of magic missile", inputs=["y"])

        blanks = [
            o for o in self.char1.contents
            if getattr(o.db, "prototype_key", None) == "training_wand"
        ]
        self.assertEqual(len(blanks), 0)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_arcane_dust_consumed(self, mock_assign, mock_spawn, mock_delay):
        """2 Arcane Dust should be consumed from inventory."""
        mock_assign.return_value = TOKEN_ID
        mock_spawn.return_value = MagicMock()

        self.call(CmdCraft(), "wand of magic missile", inputs=["y"])

        # Started with 5, consumed 2, should have 3 left
        self.assertEqual(self.char1.get_resource(16), 3)

    def test_enchanting_class_skill_passes_mastery_gate(self):
        """The class_skill_mastery_levels path for ENCHANTING must be honoured.

        Pre-refactor, cmd_craft only read general_skill_mastery_levels and
        would reject the mage even with ENCHANTING in class_skill_mastery_levels.
        This test protects against regression.
        """
        # Character has ENCHANTING in class_skill_mastery_levels (from setUp).
        # The test relies on the recipe being "known" via get_known_recipes()
        # and the mastery check reading from the right dict.
        known = self.char1.get_known_recipes()
        self.assertIn("wand_magic_missile", known)
        # And cmd_craft's mastery check should pass (tested indirectly by
        # the other craft tests above, but we verify the helper directly
        # here so a cmd_craft regression surfaces as a clear failure).
        from commands.room_specific_cmds.crafting.cmd_craft import (
            _get_crafting_mastery,
        )
        self.assertEqual(
            _get_crafting_mastery(self.char1, skills.ENCHANTING),
            MasteryLevel.GRANDMASTER.value,
        )
