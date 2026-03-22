"""
Tests for CmdTrain — verifies the full training system including:
- Listing available skills/weapons with costs and success chances
- Skill/weapon validation (enum-driven class/weapon restrictions)
- Gold cost calculation with CHA discount/surcharge
- Skill point validation
- Trainer mastery cap (can't teach beyond their own level)
- Y/N confirmation
- Cooldown on failure (per-trainer, 1 hour)
- Success/failure resolution (mastery advancement, point deduction)
- Progress bar via delay()

Uses EvenniaCommandTest which provides self.call() with obj= for NPC commands.
"""

import time
from unittest.mock import patch, MagicMock

from django.conf import settings

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.npc_cmds.cmdset_trainer import (
    CmdTrain,
    CmdBuyRecipe,
    _calculate_gold_cost,
    _get_success_chance,
    _match_in_list,
    _format_time,
    _check_cooldown,
    _set_cooldown,
    _TRAINING_GOLD_COST,
    _FAILURE_COOLDOWN,
)
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from enums.weapon_type import WeaponType


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


# ═══════════════════════════════════════════════════════════════════════
#  Unit tests for pure helper functions (no DB needed)
# ═══════════════════════════════════════════════════════════════════════

class TestHelperFunctions(EvenniaCommandTest):
    """Unit tests for module-level helper functions."""

    def create_script(self):
        pass

    def test_calculate_gold_cost_base(self):
        """CHA 10 (mod 0) → no discount → base cost."""
        self.assertEqual(_calculate_gold_cost(1, 10), 50)
        self.assertEqual(_calculate_gold_cost(2, 10), 100)
        self.assertEqual(_calculate_gold_cost(3, 10), 200)
        self.assertEqual(_calculate_gold_cost(4, 10), 350)
        self.assertEqual(_calculate_gold_cost(5, 10), 500)

    def test_calculate_gold_cost_high_cha(self):
        """CHA 20 → mod +5 → 25% discount."""
        self.assertEqual(_calculate_gold_cost(1, 20), 38)   # 50 * 0.75 = 37.5 → 38
        self.assertEqual(_calculate_gold_cost(2, 20), 75)   # 100 * 0.75
        self.assertEqual(_calculate_gold_cost(5, 20), 375)  # 500 * 0.75

    def test_calculate_gold_cost_low_cha(self):
        """CHA 6 → mod -2 → 10% surcharge."""
        self.assertEqual(_calculate_gold_cost(1, 6), 55)    # 50 * 1.10
        self.assertEqual(_calculate_gold_cost(2, 6), 110)   # 100 * 1.10

    def test_calculate_gold_cost_minimum_1(self):
        """Cost should never drop below 1."""
        self.assertGreaterEqual(_calculate_gold_cost(1, 50), 1)

    def test_success_chance_by_gap(self):
        """Success chance scales with trainer-trainee mastery gap."""
        self.assertEqual(_get_success_chance(0), 0)
        self.assertEqual(_get_success_chance(-1), 0)
        self.assertEqual(_get_success_chance(1), 50)
        self.assertEqual(_get_success_chance(2), 75)
        self.assertEqual(_get_success_chance(3), 90)
        self.assertEqual(_get_success_chance(4), 100)
        self.assertEqual(_get_success_chance(5), 100)

    def test_match_in_list_exact(self):
        """Exact match returns the key."""
        result = _match_in_list(["battleskills", "bash", "parry"], "battleskills")
        self.assertEqual(result, "battleskills")

    def test_match_in_list_prefix(self):
        """Unique prefix returns the match."""
        result = _match_in_list(["battleskills", "bash", "parry"], "bas")
        self.assertEqual(result, "bash")

    def test_match_in_list_no_match(self):
        """No match returns None."""
        result = _match_in_list(["battleskills", "bash", "parry"], "fireball")
        self.assertIsNone(result)

    def test_match_in_list_ambiguous(self):
        """Ambiguous prefix returns None."""
        result = _match_in_list(["stab", "stealth"], "st")
        self.assertIsNone(result)

    def test_match_in_list_spaces_to_underscores(self):
        """User input with spaces matches underscore keys."""
        result = _match_in_list(["long_sword", "dagger"], "long sword")
        self.assertEqual(result, "long_sword")

    def test_format_time_seconds(self):
        """Short durations shown as seconds."""
        self.assertEqual(_format_time(30), "30s")
        self.assertEqual(_format_time(59), "59s")

    def test_format_time_minutes(self):
        """Longer durations shown as minutes and seconds."""
        self.assertEqual(_format_time(60), "1m")
        self.assertEqual(_format_time(90), "1m 30s")
        self.assertEqual(_format_time(3600), "60m")


# ═══════════════════════════════════════════════════════════════════════
#  Integration tests — CmdTrain listing
# ═══════════════════════════════════════════════════════════════════════

class TestCmdTrainListing(EvenniaCommandTest):
    """Test the `train` command listing (no args)."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 1000
        self.char1.db.resources = {}
        self.char1.db.classes = {
            "warrior": {"level": 1, "skill_pts_available": 10},
        }
        self.char1.general_skill_pts_available = 5
        self.char1.weapon_skill_pts_available = 5

        # Create trainer NPC in the same room
        self.trainer = create.create_object(
            "typeclasses.actors.npcs.trainer.TrainerNPC",
            key="Swordmaster",
            location=self.room1,
        )
        self.trainer.trainable_skills = ["battleskills", "bash"]
        self.trainer.trainable_weapons = ["long_sword"]
        self.trainer.trainer_class = "warrior"
        self.trainer.trainer_masteries = {"battleskills": 5, "bash": 3, "long_sword": 4}

    def test_listing_shows_skills(self):
        """train with no args should list trainable skills."""
        result = self.call(CmdTrain(), "", obj=self.trainer)
        self.assertIn("Trainable Skills", result)
        self.assertIn("battleskills", result)
        self.assertIn("bash", result)

    def test_listing_shows_weapons(self):
        """train listing should show trainable weapons."""
        result = self.call(CmdTrain(), "", obj=self.trainer)
        self.assertIn("Trainable Weapons", result)
        self.assertIn("long sword", result)

    def test_listing_shows_gold_cost(self):
        """Listing should show gold cost for BASIC (52 with default CHA 8)."""
        result = self.call(CmdTrain(), "", obj=self.trainer)
        # Default CHA is 8 → mod -1 → 5% surcharge → 50 * 1.05 = 52.5 → 52
        self.assertIn("52", result)

    def test_listing_shows_success_chance(self):
        """Listing should show success percentage."""
        result = self.call(CmdTrain(), "", obj=self.trainer)
        # Trainer mastery 5, char mastery 0 → gap 5 → 100%
        self.assertIn("100%", result)

    def test_listing_shows_maxed(self):
        """A skill at GRANDMASTER should show 'Maxed'."""
        self.char1.db.general_skill_mastery_levels = {
            "battleskills": MasteryLevel.GRANDMASTER.value,
        }
        result = self.call(CmdTrain(), "", obj=self.trainer)
        self.assertIn("Maxed", result)

    def test_listing_trainer_cant_teach(self):
        """When char mastery >= trainer mastery, show can't teach."""
        self.char1.db.general_skill_mastery_levels = {
            "battleskills": 5,  # same as trainer
        }
        # bash trainer mastery is 3, char mastery 3
        self.char1.db.class_skill_mastery_levels = {
            "bash": {"mastery": 3, "classes": ["Warrior"]},
        }
        result = self.call(CmdTrain(), "", obj=self.trainer)
        # dodge should show Maxed (at GRANDMASTER), bash should show can't teach
        self.assertIn("can't teach", result)

    def test_listing_no_class_access(self):
        """Char without warrior class can't see class skills as trainable."""
        self.char1.db.classes = {}  # no classes
        result = self.call(CmdTrain(), "", obj=self.trainer)
        # weapon should show "no qualifying class"
        self.assertIn("no qualifying class", result)

    def test_listing_trainer_not_in_room(self):
        """Trainer in different room shows error."""
        self.trainer.location = self.room2
        self.call(CmdTrain(), "", "There is no trainer here.", obj=self.trainer)

    def test_listing_recipes_for_sale(self):
        """Recipes for sale should appear in the listing."""
        self.trainer.recipes_for_sale = {"iron_sword": 50}
        result = self.call(CmdTrain(), "", obj=self.trainer)
        self.assertIn("Recipes for Sale", result)
        self.assertIn("Iron Sword", result)

    def test_listing_empty_trainer(self):
        """Trainer with nothing to teach shows appropriate message."""
        self.trainer.trainable_skills = []
        self.trainer.trainable_weapons = []
        self.trainer.recipes_for_sale = {}
        result = self.call(CmdTrain(), "", obj=self.trainer)
        self.assertIn("nothing to teach", result)


# ═══════════════════════════════════════════════════════════════════════
#  Integration tests — CmdTrain skill training
# ═══════════════════════════════════════════════════════════════════════

class TestCmdTrainSkill(EvenniaCommandTest):
    """Test the `train <skill>` flow."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 1000
        self.char1.db.resources = {}
        self.char1.db.classes = {
            "warrior": {"level": 5, "skill_pts_available": 20},
        }
        self.char1.general_skill_pts_available = 10
        self.char1.weapon_skill_pts_available = 10
        self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.class_skill_mastery_levels = {}

        self.trainer = create.create_object(
            "typeclasses.actors.npcs.trainer.TrainerNPC",
            key="Swordmaster",
            location=self.room1,
        )
        self.trainer.trainable_skills = ["battleskills", "bash"]
        self.trainer.trainable_weapons = ["long_sword"]
        self.trainer.trainer_class = "warrior"
        self.trainer.trainer_masteries = {"battleskills": 5, "bash": 3, "long_sword": 4}

    def test_train_unknown_skill(self):
        """Training a skill not on the trainer's list shows error."""
        result = self.call(CmdTrain(), "fireball", obj=self.trainer)
        self.assertIn("not available", result)

    def test_train_cancelled(self):
        """Answering 'n' to confirmation cancels training."""
        result = self.call(
            CmdTrain(), "battleskills", obj=self.trainer, inputs=["n"]
        )
        self.assertIn("cancelled", result)
        # Gold should not be deducted
        self.assertEqual(self.char1.get_gold(), 1000)

    @patch("commands.npc_cmds.cmdset_trainer.delay")
    @patch("commands.npc_cmds.cmdset_trainer._resolve_skill_training")
    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_train_general_skill_deducts_gold(
        self, mock_craft, mock_resolve, mock_delay
    ):
        """Training dodge (general skill) should deduct gold."""
        # Make delay() call the callback immediately
        mock_delay.side_effect = (
            lambda secs, cb, *a, **kw: cb(*a, **kw)
        )
        self.call(CmdTrain(), "battleskills", obj=self.trainer, inputs=["y"])
        # Default CHA 8 → mod -1 → 5% surcharge → BASIC costs 52
        self.assertEqual(self.char1.get_gold(), 948)

    @patch("commands.npc_cmds.cmdset_trainer.delay")
    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_train_general_skill_success(self, mock_craft, mock_delay):
        """On success, mastery advances and skill points are deducted."""
        mock_delay.side_effect = (
            lambda secs, cb, *a, **kw: cb(*a, **kw)
        )
        # Patch randint to guarantee success (roll 1 <= 100% chance)
        with patch(
            "commands.npc_cmds.cmdset_trainer.randint", return_value=1
        ):
            result = self.call(
                CmdTrain(), "battleskills", obj=self.trainer, inputs=["y"]
            )
        # Mastery should be BASIC (1)
        levels = self.char1.db.general_skill_mastery_levels or {}
        self.assertEqual(levels.get("battleskills"), MasteryLevel.BASIC.value)
        # General skill points deducted (BASIC costs 1 point)
        self.assertEqual(self.char1.general_skill_pts_available, 9)

    @patch("commands.npc_cmds.cmdset_trainer.delay")
    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_train_general_skill_failure_sets_cooldown(
        self, mock_craft, mock_delay
    ):
        """On failure, cooldown is set, gold lost, points kept."""
        mock_delay.side_effect = (
            lambda secs, cb, *a, **kw: cb(*a, **kw)
        )
        # Patch randint to guarantee failure (roll 100 > any chance < 100)
        # Trainer mastery 5, char mastery 0 → gap 5 → 100% chance
        # To get failure, set trainer mastery to 1 (gap 1 → 50% chance)
        self.trainer.trainer_masteries = {
            "battleskills": 1, "bash": 3, "long_sword": 4,
        }
        with patch(
            "commands.npc_cmds.cmdset_trainer.randint", return_value=100
        ):
            result = self.call(
                CmdTrain(), "battleskills", obj=self.trainer, inputs=["y"]
            )
        # Mastery should NOT advance
        levels = self.char1.db.general_skill_mastery_levels or {}
        self.assertEqual(levels.get("battleskills", 0), 0)
        # Skill points should NOT be deducted
        self.assertEqual(self.char1.general_skill_pts_available, 10)
        # Gold IS deducted (non-refundable) — CHA 8 → 52 gold
        self.assertEqual(self.char1.get_gold(), 948)
        # Cooldown should be set
        cooldowns = self.char1.db.training_cooldowns or {}
        self.assertIn(str(self.trainer.dbref), cooldowns)

    @patch("commands.npc_cmds.cmdset_trainer.delay")
    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_train_class_skill_success(self, mock_craft, mock_delay):
        """Training bash (warrior class skill) deducts class skill points."""
        mock_delay.side_effect = (
            lambda secs, cb, *a, **kw: cb(*a, **kw)
        )
        with patch(
            "commands.npc_cmds.cmdset_trainer.randint", return_value=1
        ):
            self.call(
                CmdTrain(), "bash", obj=self.trainer, inputs=["y"]
            )
        # Class skill mastery should advance
        levels = self.char1.db.class_skill_mastery_levels or {}
        self.assertIn("bash", levels)
        self.assertEqual(levels["bash"]["mastery"], MasteryLevel.BASIC.value)
        # Class skill points deducted from warrior pool
        class_data = self.char1.db.classes["warrior"]
        self.assertEqual(class_data["skill_pts_available"], 19)

    def test_train_class_skill_wrong_class(self):
        """Can't train warrior class skill without warrior class."""
        self.char1.db.classes = {
            "thief": {"level": 1, "skill_pts_available": 10},
        }
        result = self.call(CmdTrain(), "bash", obj=self.trainer)
        self.assertIn("not a", result)

    def test_train_not_enough_gold(self):
        """Training requires gold."""
        self.char1.db.gold = 0
        result = self.call(CmdTrain(), "battleskills", obj=self.trainer)
        self.assertIn("gold", result.lower())

    def test_train_not_enough_skill_points(self):
        """Training requires skill points."""
        self.char1.general_skill_pts_available = 0
        result = self.call(CmdTrain(), "battleskills", obj=self.trainer)
        self.assertIn("points", result.lower())

    def test_train_already_maxed(self):
        """Can't train a skill that's already at GRANDMASTER."""
        self.char1.db.general_skill_mastery_levels = {
            "battleskills": MasteryLevel.GRANDMASTER.value,
        }
        result = self.call(CmdTrain(), "battleskills", obj=self.trainer)
        self.assertIn("nothing more to learn", result)

    def test_train_trainer_cant_teach_further(self):
        """Can't train beyond trainer's mastery."""
        # Set char mastery = trainer mastery for bash (both 3)
        self.char1.db.class_skill_mastery_levels = {
            "bash": {"mastery": 3, "classes": ["Warrior"]},
        }
        result = self.call(CmdTrain(), "bash", obj=self.trainer)
        self.assertIn("not skilled enough", result)

    def test_train_busy(self):
        """Can't train while already processing."""
        self.char1.ndb.is_processing = True
        result = self.call(CmdTrain(), "battleskills", obj=self.trainer)
        self.assertIn("already busy", result)

    def test_train_cooldown_blocks(self):
        """Can't train with a trainer you recently failed with."""
        # Set a cooldown that's still active
        self.char1.db.training_cooldowns = {
            str(self.trainer.dbref): time.time(),
        }
        result = self.call(CmdTrain(), "battleskills", obj=self.trainer)
        self.assertIn("cannot train", result)

    def test_train_cooldown_expired_allows(self):
        """Expired cooldown doesn't block training."""
        # Set a cooldown from over an hour ago
        self.char1.db.training_cooldowns = {
            str(self.trainer.dbref): time.time() - _FAILURE_COOLDOWN - 1,
        }
        # Should reach confirmation prompt (not blocked)
        result = self.call(CmdTrain(), "battleskills", obj=self.trainer, inputs=["n"])
        self.assertIn("cancelled", result)


# ═══════════════════════════════════════════════════════════════════════
#  Integration tests — CmdTrain weapon training
# ═══════════════════════════════════════════════════════════════════════

class TestCmdTrainWeapon(EvenniaCommandTest):
    """Test the `train weapon <name>` flow."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 1000
        self.char1.db.resources = {}
        self.char1.db.classes = {
            "warrior": {"level": 5, "skill_pts_available": 20},
        }
        self.char1.general_skill_pts_available = 10
        self.char1.weapon_skill_pts_available = 10
        self.char1.db.weapon_skill_mastery_levels = {}

        self.trainer = create.create_object(
            "typeclasses.actors.npcs.trainer.TrainerNPC",
            key="Swordmaster",
            location=self.room1,
        )
        self.trainer.trainable_skills = ["battleskills"]
        self.trainer.trainable_weapons = ["long_sword", "dagger"]
        self.trainer.trainer_class = "warrior"
        self.trainer.trainer_masteries = {
            "battleskills": 5, "long_sword": 4, "dagger": 3,
        }

    def test_train_weapon_unknown(self):
        """Training a weapon not on the trainer's list shows error."""
        result = self.call(
            CmdTrain(), "weapon halberd", obj=self.trainer
        )
        self.assertIn("not available", result)

    def test_train_weapon_cancelled(self):
        """Answering 'n' cancels weapon training."""
        result = self.call(
            CmdTrain(), "weapon long sword", obj=self.trainer, inputs=["n"]
        )
        self.assertIn("cancelled", result)
        self.assertEqual(self.char1.get_gold(), 1000)

    @patch("commands.npc_cmds.cmdset_trainer.delay")
    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_train_weapon_success(self, mock_craft, mock_delay):
        """Successful weapon training advances mastery and deducts points."""
        mock_delay.side_effect = (
            lambda secs, cb, *a, **kw: cb(*a, **kw)
        )
        with patch(
            "commands.npc_cmds.cmdset_trainer.randint", return_value=1
        ):
            self.call(
                CmdTrain(), "weapon long sword",
                obj=self.trainer, inputs=["y"],
            )
        levels = self.char1.db.weapon_skill_mastery_levels or {}
        self.assertEqual(levels.get("long_sword"), MasteryLevel.BASIC.value)
        self.assertEqual(self.char1.weapon_skill_pts_available, 9)

    @patch("commands.npc_cmds.cmdset_trainer.delay")
    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_train_weapon_failure(self, mock_craft, mock_delay):
        """Failed weapon training: gold lost, points kept, cooldown set."""
        mock_delay.side_effect = (
            lambda secs, cb, *a, **kw: cb(*a, **kw)
        )
        # Set trainer mastery to 1 so gap = 1 → 50% chance
        self.trainer.trainer_masteries = {
            "battleskills": 5, "long_sword": 1, "dagger": 3,
        }
        with patch(
            "commands.npc_cmds.cmdset_trainer.randint", return_value=100
        ):
            self.call(
                CmdTrain(), "weapon long sword",
                obj=self.trainer, inputs=["y"],
            )
        levels = self.char1.db.weapon_skill_mastery_levels or {}
        self.assertEqual(levels.get("long_sword", 0), 0)
        self.assertEqual(self.char1.weapon_skill_pts_available, 10)
        # Gold IS deducted (non-refundable) — CHA 8 → 52 gold
        self.assertEqual(self.char1.get_gold(), 948)
        cooldowns = self.char1.db.training_cooldowns or {}
        self.assertIn(str(self.trainer.dbref), cooldowns)

    def test_train_weapon_no_qualifying_class(self):
        """Can't train a weapon your classes don't support."""
        self.char1.db.classes = {
            "mage": {"level": 1, "skill_pts_available": 10},
        }
        result = self.call(
            CmdTrain(), "weapon long sword", obj=self.trainer
        )
        self.assertIn("None of your classes", result)

    def test_train_weapon_not_enough_points(self):
        """Training requires weapon skill points."""
        self.char1.weapon_skill_pts_available = 0
        result = self.call(
            CmdTrain(), "weapon long sword", obj=self.trainer
        )
        self.assertIn("weapon skill points", result)

    def test_train_weapon_already_maxed(self):
        """Can't train a weapon at GRANDMASTER."""
        self.char1.db.weapon_skill_mastery_levels = {
            "long_sword": MasteryLevel.GRANDMASTER.value,
        }
        result = self.call(
            CmdTrain(), "weapon long sword", obj=self.trainer
        )
        self.assertIn("nothing more to learn", result)


# ═══════════════════════════════════════════════════════════════════════
#  Integration tests — CmdBuyRecipe
# ═══════════════════════════════════════════════════════════════════════

class TestCmdBuyRecipe(EvenniaCommandTest):
    """Test the `buy recipe` command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 500
        self.char1.db.resources = {}

        self.trainer = create.create_object(
            "typeclasses.actors.npcs.trainer.TrainerNPC",
            key="Swordmaster",
            location=self.room1,
        )
        self.trainer.recipes_for_sale = {"iron_sword": 50, "iron_shield": 75}

    def test_buy_recipe_list(self):
        """buy recipe with no name lists available recipes."""
        result = self.call(CmdBuyRecipe(), "recipe", obj=self.trainer)
        self.assertIn("Recipes for Sale", result)
        self.assertIn("Iron Sword", result)
        self.assertIn("Iron Shield", result)

    def test_buy_recipe_no_recipes(self):
        """Trainer with no recipes shows appropriate message."""
        self.trainer.recipes_for_sale = {}
        result = self.call(CmdBuyRecipe(), "recipe", obj=self.trainer)
        self.assertIn("no recipes", result)

    def test_buy_recipe_not_enough_gold(self):
        """Can't buy a recipe you can't afford."""
        self.char1.db.gold = 10
        result = self.call(
            CmdBuyRecipe(), "recipe iron sword", obj=self.trainer
        )
        self.assertIn("gold", result.lower())

    def test_buy_recipe_unknown(self):
        """Trying to buy a non-existent recipe shows error."""
        result = self.call(
            CmdBuyRecipe(), "recipe moonstone", obj=self.trainer
        )
        self.assertIn("not available", result)

    def test_buy_recipe_wrong_usage(self):
        """buy without 'recipe' shows usage hint."""
        result = self.call(CmdBuyRecipe(), "sword", obj=self.trainer)
        self.assertIn("Usage", result)

    def test_buy_recipe_trainer_not_in_room(self):
        """Trainer in different room shows error."""
        self.trainer.location = self.room2
        self.call(
            CmdBuyRecipe(), "recipe iron sword",
            "There is no trainer here.", obj=self.trainer,
        )


# ═══════════════════════════════════════════════════════════════════════
#  Cooldown system tests
# ═══════════════════════════════════════════════════════════════════════

class TestCooldownSystem(EvenniaCommandTest):
    """Test the per-trainer cooldown system."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.trainer = create.create_object(
            "typeclasses.actors.npcs.trainer.TrainerNPC",
            key="Swordmaster",
            location=self.room1,
        )

    def test_no_cooldown_by_default(self):
        """No cooldown if none has been set."""
        blocked, remaining = _check_cooldown(self.char1, self.trainer)
        self.assertFalse(blocked)
        self.assertEqual(remaining, 0)

    def test_set_and_check_cooldown(self):
        """Setting a cooldown makes the trainer blocked."""
        _set_cooldown(self.char1, self.trainer)
        blocked, remaining = _check_cooldown(self.char1, self.trainer)
        self.assertTrue(blocked)
        self.assertGreater(remaining, 3500)

    def test_expired_cooldown_cleaned_up(self):
        """Expired cooldowns are cleaned up on check."""
        self.char1.db.training_cooldowns = {
            str(self.trainer.dbref): time.time() - _FAILURE_COOLDOWN - 10,
        }
        blocked, remaining = _check_cooldown(self.char1, self.trainer)
        self.assertFalse(blocked)
        # Entry should be cleaned up
        cooldowns = self.char1.db.training_cooldowns or {}
        self.assertNotIn(str(self.trainer.dbref), cooldowns)

    def test_cooldown_per_trainer(self):
        """Cooldown with trainer A doesn't block trainer B."""
        trainer_b = create.create_object(
            "typeclasses.actors.npcs.trainer.TrainerNPC",
            key="Axemaster",
            location=self.room1,
        )
        _set_cooldown(self.char1, self.trainer)
        blocked_a, _ = _check_cooldown(self.char1, self.trainer)
        blocked_b, _ = _check_cooldown(self.char1, trainer_b)
        self.assertTrue(blocked_a)
        self.assertFalse(blocked_b)


# ═══════════════════════════════════════════════════════════════════════
#  CHA discount integration test
# ═══════════════════════════════════════════════════════════════════════

class TestChaDiscount(EvenniaCommandTest):
    """Test that CHA modifier affects displayed and actual gold costs."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 1000
        self.char1.db.resources = {}
        self.char1.db.classes = {}
        self.char1.general_skill_pts_available = 10
        self.char1.db.general_skill_mastery_levels = {}

        self.trainer = create.create_object(
            "typeclasses.actors.npcs.trainer.TrainerNPC",
            key="Swordmaster",
            location=self.room1,
        )
        self.trainer.trainable_skills = ["battleskills"]
        self.trainer.trainable_weapons = []
        self.trainer.trainer_class = "warrior"
        self.trainer.trainer_masteries = {"battleskills": 5}

    @patch("commands.npc_cmds.cmdset_trainer.delay")
    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_high_cha_discount(self, mock_craft, mock_delay):
        """High CHA (20) gives 25% discount: 50 → 38 gold."""
        mock_delay.side_effect = (
            lambda secs, cb, *a, **kw: cb(*a, **kw)
        )
        self.char1.charisma = 20
        with patch(
            "commands.npc_cmds.cmdset_trainer.randint", return_value=1
        ):
            self.call(CmdTrain(), "battleskills", obj=self.trainer, inputs=["y"])
        # 50 * (1 - 5 * 0.05) = 50 * 0.75 = 37.5 → 38
        self.assertEqual(self.char1.get_gold(), 962)

    @patch("commands.npc_cmds.cmdset_trainer.delay")
    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_low_cha_surcharge(self, mock_craft, mock_delay):
        """Low CHA (6) gives 10% surcharge: 50 → 55 gold."""
        mock_delay.side_effect = (
            lambda secs, cb, *a, **kw: cb(*a, **kw)
        )
        self.char1.charisma = 6
        with patch(
            "commands.npc_cmds.cmdset_trainer.randint", return_value=1
        ):
            self.call(CmdTrain(), "battleskills", obj=self.trainer, inputs=["y"])
        self.assertEqual(self.char1.get_gold(), 945)
