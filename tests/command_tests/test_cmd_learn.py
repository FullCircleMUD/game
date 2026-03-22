"""
Tests for CmdLearn — verifies the learn command finds recipe items,
confirms with the player, consumes the NFT, and delegates to
RecipeBookMixin.learn_recipe().

Uses EvenniaCommandTest with inputs=[] for yield-based Y/N prompts.
Creates CraftingRecipeNFTItem directly (bypassing hooks) for isolation.
"""

from unittest.mock import patch

from django.conf import settings

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_learn import CmdLearn
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


CHAIN_ID = settings.BLOCKCHAIN_CHAIN_ID
CONTRACT_NFT = settings.CONTRACT_NFT
WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
TOKEN_ID = 101


def _create_recipe_item(char, token_id=TOKEN_ID, recipe_key="training_longsword"):
    """Create a CraftingRecipeNFTItem in character's inventory."""
    obj = create.create_object(
        "typeclasses.items.consumables.crafting_recipe_nft_item.CraftingRecipeNFTItem",
        key="Training Longsword Recipe",
        nohome=True,
    )
    obj.token_id = token_id
    obj.chain_id = CHAIN_ID
    obj.contract_address = CONTRACT_NFT
    obj.db.recipe_key = recipe_key
    # Place directly in inventory bypassing at_post_move
    obj.db_location = char
    obj.save(update_fields=["db_location"])
    return obj


def _give_carpenter_skill(char, mastery=MasteryLevel.BASIC):
    """Give a character carpenter skill at given mastery."""
    if not char.db.general_skill_mastery_levels:
        char.db.general_skill_mastery_levels = {}
    char.db.general_skill_mastery_levels[skills.CARPENTER.value] = mastery.value


class TestCmdLearnSuccess(EvenniaCommandTest):
    """Test successful recipe learning."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        _give_carpenter_skill(self.char1)
        self.recipe_item = _create_recipe_item(self.char1)

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_learn_by_name(self, mock_craft):
        """learn recipe should consume the item and add recipe to book."""
        self.call(CmdLearn(), "recipe", inputs=["y"])
        self.assertTrue(self.char1.knows_recipe("training_longsword"))
        mock_craft.assert_called_once()

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_learn_removes_item_from_inventory(self, mock_craft):
        """After learning, recipe NFT should be gone from inventory."""
        self.call(CmdLearn(), "recipe", inputs=["y"])
        from typeclasses.items.consumables.crafting_recipe_nft_item import (
            CraftingRecipeNFTItem,
        )
        recipes = [
            obj for obj in self.char1.contents
            if isinstance(obj, CraftingRecipeNFTItem)
        ]
        self.assertEqual(len(recipes), 0)

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_learn_shows_success_message(self, mock_craft):
        """Learn should show the learn success message."""
        self.call(
            CmdLearn(), "recipe",
            "You learn how to craft Training Longsword!",
            inputs=["y"],
        )

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_learn_by_full_name(self, mock_craft):
        """learn training longsword recipe should work via substring match."""
        self.call(CmdLearn(), "training longsword", inputs=["y"])
        self.assertTrue(self.char1.knows_recipe("training_longsword"))


class TestCmdLearnFailures(EvenniaCommandTest):
    """Test learn command failure cases."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.recipe_item = _create_recipe_item(self.char1)

    def test_learn_insufficient_skill(self):
        """Learning without the required skill should fail and keep item."""
        # No carpenter skill set
        self.call(CmdLearn(), "recipe", inputs=["y"])
        self.assertFalse(self.char1.knows_recipe("training_longsword"))
        self.assertIn(self.recipe_item, self.char1.contents)

    def test_learn_insufficient_skill_shows_message(self):
        """Should show mastery requirement message."""
        self.call(CmdLearn(), "recipe", "You need at least", inputs=["y"])

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_learn_already_known(self, mock_craft):
        """Learning a recipe already in the book should fail and keep item."""
        _give_carpenter_skill(self.char1)
        # Learn it first
        self.char1.learn_recipe("training_longsword")
        # Try again via command
        self.call(CmdLearn(), "recipe", "You already know", inputs=["y"])
        # Item should still exist (consume failed, no delete)
        self.assertIn(self.recipe_item, self.char1.contents)
        mock_craft.assert_not_called()


class TestCmdLearnCancel(EvenniaCommandTest):
    """Test Y/N cancellation."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        _give_carpenter_skill(self.char1)
        self.recipe_item = _create_recipe_item(self.char1)

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_cancel_keeps_item(self, mock_craft):
        """Answering 'n' should cancel and leave recipe in inventory."""
        self.call(CmdLearn(), "recipe", inputs=["n"])
        mock_craft.assert_not_called()
        self.assertIn(self.recipe_item, self.char1.contents)
        self.assertFalse(self.char1.knows_recipe("training_longsword"))

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_cancel_shows_message(self, mock_craft):
        """Cancelling should show cancelled message."""
        self.call(CmdLearn(), "recipe", "Learning cancelled.", inputs=["n"])


class TestCmdLearnEdgeCases(EvenniaCommandTest):
    """Test edge cases for the learn command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_no_args(self):
        """Learn with no arguments should show usage."""
        self.call(CmdLearn(), "", "Learn from what?")

    def test_no_recipe_items(self):
        """Learn when carrying no recipe items should show message."""
        self.call(CmdLearn(), "recipe", "You aren't carrying any recipe scrolls.")

    def test_wrong_name(self):
        """Learn with non-matching name should show error."""
        _create_recipe_item(self.char1)
        self.call(CmdLearn(), "potion of healing", "You don't have a recipe by that name.")

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_blank_recipe_key(self, mock_craft):
        """Recipe with empty recipe_key should show error."""
        _give_carpenter_skill(self.char1)
        item = _create_recipe_item(self.char1, recipe_key="")
        self.call(CmdLearn(), "recipe", "This recipe scroll is blank.", inputs=["y"])
        # Item should stay (consume returns False for blank key)
        self.assertIn(item, self.char1.contents)
        mock_craft.assert_not_called()
