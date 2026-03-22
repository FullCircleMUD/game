"""
Tests for CmdRepair — repair damaged items at crafting stations.

Repair restores durability to max using the item's crafting recipe.
Cost is total_materials - 1 (auto-computed) or explicit repair_ingredients.
Room fee always applies.

evennia test --settings settings tests.command_tests.test_cmd_repair
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.room_specific_cmds.crafting.cmd_repair import CmdRepair
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from enums.wearslot import HumanoidWearSlot


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


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


def _learn_recipe(char, recipe_key):
    """Teach a recipe directly."""
    if not char.db.recipe_book:
        char.db.recipe_book = {}
    char.db.recipe_book[recipe_key] = True


def _make_damaged_weapon(key, location, prototype_key, max_dur=50, cur_dur=25):
    """Create a weapon-like item with durability and prototype tag."""
    obj = create.create_object(
        "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
        key=key,
        nohome=True,
    )
    obj.wearslot = HumanoidWearSlot.HEAD
    obj.max_durability = max_dur
    obj.durability = cur_dur
    obj.tags.add(prototype_key, category="from_prototype")
    obj.move_to(location, quiet=True)
    return obj


def _instant_delay(seconds, callback, *args, **kwargs):
    """Mock for utils.delay — executes callback immediately."""
    callback(*args, **kwargs)


# ── Repair Command — Success ──────────────────────────────────────────

class TestCmdRepairSuccess(EvenniaCommandTest):
    """Test successful repair."""

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
        _learn_recipe(self.char1, "training_longsword")
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)

    @patch("commands.room_specific_cmds.crafting.cmd_repair.delay",
           side_effect=_instant_delay)
    def test_repair_success(self, mock_delay):
        """Repair should consume resources, gold, and restore durability."""
        item = _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )

        self.call(CmdRepair(), "training longsword", inputs=["y"])

        # Durability restored
        self.assertEqual(item.durability, 50)
        # Resources consumed: 2 Timber (3 craft - 1 = 2 repair)
        self.assertEqual(self.char1.get_resource(7), 3)
        # Gold consumed: 2 (workshop fee)
        self.assertEqual(self.char1.get_gold(), 18)

    @patch("commands.room_specific_cmds.crafting.cmd_repair.delay",
           side_effect=_instant_delay)
    def test_repair_shows_success_message(self, mock_delay):
        """Repair should show a success message."""
        _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )

        result = self.call(CmdRepair(), "training longsword", inputs=["y"])
        self.assertIn("pristine condition", result)

    @patch("commands.room_specific_cmds.crafting.cmd_repair.delay",
           side_effect=_instant_delay)
    def test_repair_zero_material_cost(self, mock_delay):
        """Recipe with 1 total material should have 0 repair resource cost."""
        _learn_recipe(self.char1, "training_dagger")
        item = _make_damaged_weapon(
            "Training Dagger", self.char1, "training_dagger",
            max_dur=30, cur_dur=10,
        )

        self.call(CmdRepair(), "training dagger", inputs=["y"])

        # Durability restored
        self.assertEqual(item.durability, 30)
        # No resources consumed (1 timber craft - 1 = 0 repair)
        self.assertEqual(self.char1.get_resource(7), 5)
        # Gold still consumed (workshop fee)
        self.assertEqual(self.char1.get_gold(), 18)


# ── Repair Command — Validation Failures ──────────────────────────────

class TestCmdRepairValidation(EvenniaCommandTest):
    """Test repair command validation failures."""

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
        _learn_recipe(self.char1, "training_longsword")
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)

    def test_no_args(self):
        """Repair with no arguments should show usage."""
        self.call(CmdRepair(), "", "Repair what?")

    def test_unbreakable_item(self):
        """Unbreakable items should be rejected."""
        item = _make_damaged_weapon(
            "Magic Ring", self.char1, "pewter_ring",
            max_dur=0, cur_dur=0,
        )
        item.durability = None
        self.call(CmdRepair(), "magic ring", "Magic Ring is unbreakable")

    def test_full_durability(self):
        """Items at full health should be rejected."""
        _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=50,
        )
        self.call(CmdRepair(), "training longsword", "Training Longsword is already")

    def test_not_repairable(self):
        """Items with repairable=False should be rejected."""
        item = _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )
        item.repairable = False
        self.call(CmdRepair(), "training longsword", "Training Longsword cannot be repaired")

    def test_no_prototype_tag(self):
        """Items without a prototype tag should be rejected."""
        obj = create.create_object(
            "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
            key="Mystery Item",
            nohome=True,
        )
        obj.wearslot = HumanoidWearSlot.HEAD
        obj.max_durability = 50
        obj.durability = 25
        obj.move_to(self.char1, quiet=True)
        self.call(CmdRepair(), "mystery item", "You don't know how to repair")

    def test_no_recipe_for_item(self):
        """Items with unknown prototype_key should be rejected."""
        _make_damaged_weapon(
            "Alien Blade", self.char1, "nonexistent_prototype",
            max_dur=50, cur_dur=25,
        )
        self.call(CmdRepair(), "alien blade", "You don't know how to repair")

    def test_wrong_room_type(self):
        """Item recipe requires a different room type."""
        _learn_recipe(self.char1, "leather_boots")
        if not self.char1.db.general_skill_mastery_levels:
            self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.general_skill_mastery_levels[
            skills.LEATHERWORKER.value
        ] = MasteryLevel.BASIC.value

        _make_damaged_weapon(
            "Leather Boots", self.char1, "leather_boots",
            max_dur=50, cur_dur=25,
        )
        # Room is woodshop, recipe requires leathershop
        self.call(CmdRepair(), "leather boots", "Leather Boots needs a")

    def test_recipe_not_known(self):
        """Character must know the recipe to repair."""
        self.char1.db.recipe_book = {}
        _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )
        self.call(CmdRepair(), "training longsword", "You don't know the recipe")

    def test_character_mastery_too_low(self):
        """Insufficient character mastery should reject repair."""
        _give_carpenter_skill(self.char1, MasteryLevel.UNSKILLED)
        _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )
        result = self.call(CmdRepair(), "training longsword")
        self.assertIn("You need at least", result)

    def test_room_mastery_too_low(self):
        """Room mastery below recipe requirement should reject."""
        self.room1.db.mastery_level = 0
        _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )
        self.call(CmdRepair(), "training longsword", "This workshop isn't advanced enough")

    def test_insufficient_resources(self):
        """Not enough resources should reject repair."""
        # Clear resources — repair needs 2 Timber
        self.char1.return_resource_to_reserve(7, 5)
        _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )
        self.call(
            CmdRepair(), "training longsword", "You don't have enough materials"
        )

    def test_insufficient_gold(self):
        """Not enough gold should reject repair."""
        self.char1.return_gold_to_reserve(19)  # only 1 gold left, need 2
        _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )
        self.call(CmdRepair(), "training longsword", "You need 2 gold")

    def test_busy_rejected(self):
        """Should reject if already processing."""
        self.char1.ndb.is_processing = True
        _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )
        result = self.call(CmdRepair(), "training longsword")
        self.assertIn("already busy", result.lower())


# ── Repair Command — Cancellation ─────────────────────────────────────

class TestCmdRepairCancel(EvenniaCommandTest):
    """Test repair command Y/N cancellation."""

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
        _learn_recipe(self.char1, "training_longsword")
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)

    def test_cancel_keeps_resources(self):
        """Answering 'n' should not consume resources or gold."""
        _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )
        self.call(CmdRepair(), "training longsword", inputs=["n"])
        self.assertEqual(self.char1.get_resource(7), 5)
        self.assertEqual(self.char1.get_gold(), 20)

    def test_cancel_keeps_durability(self):
        """Cancelling should not restore durability."""
        item = _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )
        self.call(CmdRepair(), "training longsword", inputs=["n"])
        self.assertEqual(item.durability, 25)

    def test_cancel_shows_message(self):
        """Cancelling should show cancelled message."""
        _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )
        self.call(
            CmdRepair(), "training longsword",
            "Repair cancelled.",
            inputs=["n"],
        )


# ── Repair Command — XP Award ────────────────────────────────────────

class TestCmdRepairXP(EvenniaCommandTest):
    """Test XP awarded on successful repair."""

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
        _learn_recipe(self.char1, "training_longsword")
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)

    @patch("commands.room_specific_cmds.crafting.cmd_repair.delay",
           side_effect=_instant_delay)
    def test_xp_awarded_half_of_craft(self, mock_delay):
        """Repair should award 50% of craft XP."""
        _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )
        self.char1.experience_points = 0

        self.call(CmdRepair(), "training longsword", inputs=["y"])
        # BASIC craft XP = 5, repair = 5 // 2 = 2
        self.assertEqual(self.char1.experience_points, 2)

    @patch("commands.room_specific_cmds.crafting.cmd_repair.delay",
           side_effect=_instant_delay)
    def test_xp_message(self, mock_delay):
        """Repair should show XP gain message."""
        _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )

        result = self.call(CmdRepair(), "training longsword", inputs=["y"])
        self.assertIn("+2 XP", result)


# ── Repair Command — Progress Bar ────────────────────────────────────

class TestCmdRepairProgress(EvenniaCommandTest):
    """Test progress bar during repair."""

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
        _learn_recipe(self.char1, "training_longsword")
        _give_resources(self.char1, {7: 5})
        _give_gold(self.char1, 20)

    @patch("commands.room_specific_cmds.crafting.cmd_repair.delay",
           side_effect=_instant_delay)
    def test_progress_bar(self, mock_delay):
        """Repair should show progress bar messages."""
        _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )

        result = self.call(CmdRepair(), "training longsword", inputs=["y"])
        self.assertIn("Repairing Training Longsword...", result)
        self.assertIn("[##########] Done!", result)

    @patch("commands.room_specific_cmds.crafting.cmd_repair.delay",
           side_effect=_instant_delay)
    def test_is_processing_cleared(self, mock_delay):
        """ndb.is_processing should be cleared after repair completes."""
        _make_damaged_weapon(
            "Training Longsword", self.char1, "training_longsword",
            max_dur=50, cur_dur=25,
        )

        self.call(CmdRepair(), "training longsword", inputs=["y"])
        self.assertFalse(self.char1.ndb.is_processing)


# ── Repair Cost Computation ───────────────────────────────────────────

class TestComputeRepairCost(EvenniaCommandTest):
    """Test compute_repair_cost utility function."""

    def create_script(self):
        pass

    def test_auto_compute_single_resource(self):
        """3 timber → 2 timber repair."""
        from world.recipes import compute_repair_cost
        recipe = {"ingredients": {7: 3}}
        self.assertEqual(compute_repair_cost(recipe), {7: 2})

    def test_auto_compute_one_ingredient(self):
        """1 timber → 0 repair (room fee only)."""
        from world.recipes import compute_repair_cost
        recipe = {"ingredients": {7: 1}}
        self.assertEqual(compute_repair_cost(recipe), {})

    def test_auto_compute_with_nft_ingredient(self):
        """1 ingot + 1 NFT shaft = 2 total → 1 ingot repair."""
        from world.recipes import compute_repair_cost
        recipe = {"ingredients": {5: 1}, "nft_ingredients": {"spear_shaft": 1}}
        self.assertEqual(compute_repair_cost(recipe), {5: 1})

    def test_auto_compute_multi_resource(self):
        """1 essence + 2 herb = 3 total → 2 repair resources."""
        from world.recipes import compute_repair_cost
        recipe = {"ingredients": {13: 1, 14: 2}}
        result = compute_repair_cost(recipe)
        # Total repair = 2, distributed: 1 essence (capped at 1) + 1 herb
        self.assertEqual(result, {13: 1, 14: 1})

    def test_explicit_repair_ingredients(self):
        """Explicit repair_ingredients should override auto-compute."""
        from world.recipes import compute_repair_cost
        recipe = {
            "ingredients": {7: 3},
            "repair_ingredients": {7: 1, 5: 2},
        }
        self.assertEqual(compute_repair_cost(recipe), {7: 1, 5: 2})

    def test_empty_recipe(self):
        """Recipe with no ingredients → empty repair cost."""
        from world.recipes import compute_repair_cost
        recipe = {"ingredients": {}}
        self.assertEqual(compute_repair_cost(recipe), {})
