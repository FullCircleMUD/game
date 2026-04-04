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
        mock_spawn.return_value = MagicMock()

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


class TestCmdCraftPotionScaling(EvenniaCommandTest):
    """Test that brewed potions get mastery-scaled effects."""

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
    def test_brew_basic_mastery(self, mock_assign, mock_spawn, mock_delay):
        """BASIC brewer should get +1 value, 60s duration."""
        mock_assign.return_value = TOKEN_ID
        mock_item = MagicMock()
        mock_spawn.return_value = mock_item
        _give_alchemist_skill(self.char1, MasteryLevel.BASIC)

        self.call(CmdCraft(), "cat's grace", inputs=["y"])

        # Verify scaling was applied to the spawned item
        self.assertEqual(mock_item.potion_effects,
                         [{"type": "stat_bonus", "stat": "dexterity", "value": 1}])
        self.assertEqual(mock_item.duration, 60)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_brew_skilled_mastery(self, mock_assign, mock_spawn, mock_delay):
        """SKILLED brewer should get +2 value, 120s duration."""
        mock_assign.return_value = TOKEN_ID
        mock_item = MagicMock()
        mock_spawn.return_value = mock_item
        _give_alchemist_skill(self.char1, MasteryLevel.SKILLED)

        self.call(CmdCraft(), "cat's grace", inputs=["y"])

        self.assertEqual(mock_item.potion_effects,
                         [{"type": "stat_bonus", "stat": "dexterity", "value": 2}])
        self.assertEqual(mock_item.duration, 120)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_brew_grandmaster_mastery(self, mock_assign, mock_spawn, mock_delay):
        """GRANDMASTER brewer should get +5 value, 300s duration."""
        mock_assign.return_value = TOKEN_ID
        mock_item = MagicMock()
        mock_spawn.return_value = mock_item
        _give_alchemist_skill(self.char1, MasteryLevel.GRANDMASTER)

        self.call(CmdCraft(), "cat's grace", inputs=["y"])

        self.assertEqual(mock_item.potion_effects,
                         [{"type": "stat_bonus", "stat": "dexterity", "value": 5}])
        self.assertEqual(mock_item.duration, 300)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_brew_restore_potion_scaling(self, mock_assign, mock_spawn,
                                         mock_delay):
        """Restore potion should get dice-based scaling at brew time."""
        mock_assign.return_value = TOKEN_ID
        mock_item = MagicMock()
        mock_spawn.return_value = mock_item
        _give_alchemist_skill(self.char1, MasteryLevel.EXPERT)

        # Learn Life's Essence recipe
        if not self.char1.db.recipe_book:
            self.char1.db.recipe_book = {}
        self.char1.db.recipe_book["lifes_essence"] = True
        # Ingredients: 1 Moonpetal Essence (13) + 2 Bloodmoss (14)
        _give_resources(self.char1, {14: 5})

        self.call(CmdCraft(), "life's essence", inputs=["y"])

        # EXPERT (mastery 3) = 6d4+3, duration 0
        self.assertEqual(mock_item.potion_effects,
                         [{"type": "restore", "stat": "hp", "dice": "6d4+3"}])
        self.assertEqual(mock_item.duration, 0)
