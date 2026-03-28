"""
Tests for Tutorial 2: The Economic Loop.

Tests:
    - All 6 rooms are created with correct names
    - Harvest rooms have correct resource_id, resource_count, harvest_command
    - Processing rooms have correct recipes and processing_type
    - Bank room is RoomBank typeclass
    - Completion exit exists and is tagged
    - Graduation reward gated per account
    - First-run gold given, repeat run gold not given
    - All rooms have tutorial_text and guide_context

evennia test --settings settings tests.tutorial_tests.test_tutorial_2
"""

from unittest.mock import patch, MagicMock

from evennia.utils.create import create_object, create_script
from evennia.utils.test_resources import EvenniaTest
from evennia.utils.search import search_tag

from typeclasses.scripts.tutorial_instance import TutorialInstanceScript

_CHAR = "typeclasses.actors.character.FCMCharacter"

# Minimal currency cache data so get_total_fungible_weight() works without xrpl DB
_TEST_CURRENCIES = {
    1: {"name": "Wheat", "unit": "bushels", "currency_code": "FCMWheat",
        "description": "", "weight_per_unit_kg": 0.5, "is_gold": False, "resource_id": 1},
    2: {"name": "Flour", "unit": "bags", "currency_code": "FCMFlour",
        "description": "", "weight_per_unit_kg": 0.5, "is_gold": False, "resource_id": 2},
    3: {"name": "Bread", "unit": "loaves", "currency_code": "FCMBread",
        "description": "", "weight_per_unit_kg": 0.3, "is_gold": False, "resource_id": 3},
    6: {"name": "Wood", "unit": "logs", "currency_code": "FCMWood",
        "description": "", "weight_per_unit_kg": 2.0, "is_gold": False, "resource_id": 6},
    7: {"name": "Timber", "unit": "planks", "currency_code": "FCMTimber",
        "description": "", "weight_per_unit_kg": 1.5, "is_gold": False, "resource_id": 7},
}


def _start_blockchain_mocks(test_case):
    """
    Patch blockchain service classes and currency cache so the full
    FungibleInventoryMixin runs without xrpl DB access.
    """
    test_case._patches = [
        patch.dict("blockchain.xrpl.currency_cache._by_resource_id", _TEST_CURRENCIES),
        patch("blockchain.xrpl.currency_cache._load", lambda: None),
        patch("blockchain.xrpl.services.gold.GoldService", MagicMock()),
        patch("blockchain.xrpl.services.resource.ResourceService", MagicMock()),
    ]
    for p in test_case._patches:
        p.start()


def _stop_blockchain_mocks(test_case):
    for p in test_case._patches:
        p.stop()


class TestTutorial2Rooms(EvenniaTest):
    """Test that Tutorial 2 creates all rooms with correct properties."""

    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        _start_blockchain_mocks(self)
        super().setUp()
        from world.tutorial.tutorial_hub_builder import build_tutorial_hub

        self.hub = build_tutorial_hub()

        self.script = create_script(
            TutorialInstanceScript,
            key="test_t2_rooms",
            autostart=False,
        )
        self.script.instance_key = self.script.key
        self.script.hub_room_id = self.hub.id
        self.script.start()
        self.script.start_tutorial(self.char1, chunk_num=2)

        # Collect all tagged rooms
        self.rooms = {
            r.key: r
            for r in search_tag(self.script.instance_key, category="tutorial_room")
        }

    def tearDown(self):
        if self.script.state != "done":
            self.script.collapse_instance()
        _stop_blockchain_mocks(self)
        super().tearDown()

    def test_harvest_field_exists(self):
        self.assertIn("The Harvest Field", self.rooms)

    def test_woodlot_exists(self):
        self.assertIn("The Woodlot", self.rooms)

    def test_windmill_exists(self):
        self.assertIn("The Windmill", self.rooms)

    def test_bakery_exists(self):
        self.assertIn("The Bakery", self.rooms)

    def test_vault_exists(self):
        self.assertIn("The Vault", self.rooms)

    def test_complete_room_exists(self):
        self.assertIn("Tutorial Complete", self.rooms)

    def test_all_rooms_have_tutorial_text(self):
        """Every tutorial room should have tutorial_text."""
        for name, room in self.rooms.items():
            self.assertTrue(
                room.db.tutorial_text,
                f"Room '{name}' missing tutorial_text",
            )

    def test_all_rooms_have_guide_context(self):
        """Every tutorial room should have guide_context for the LLM guide."""
        for name, room in self.rooms.items():
            self.assertTrue(
                room.db.guide_context,
                f"Room '{name}' missing guide_context",
            )

    def test_harvest_field_resource_id(self):
        room = self.rooms["The Harvest Field"]
        self.assertEqual(room.resource_id, 1)  # Wheat

    def test_harvest_field_harvest_command(self):
        room = self.rooms["The Harvest Field"]
        self.assertEqual(room.harvest_command, "harvest")

    def test_harvest_field_has_resources(self):
        """First run should have resources."""
        room = self.rooms["The Harvest Field"]
        self.assertEqual(room.resource_count, 50)

    def test_woodlot_resource_id(self):
        room = self.rooms["The Woodlot"]
        self.assertEqual(room.resource_id, 6)  # Wood

    def test_woodlot_harvest_command(self):
        room = self.rooms["The Woodlot"]
        self.assertEqual(room.harvest_command, "chop")

    def test_windmill_processing_type(self):
        room = self.rooms["The Windmill"]
        self.assertEqual(room.processing_type, "windmill")

    def test_windmill_recipes(self):
        room = self.rooms["The Windmill"]
        self.assertEqual(len(room.recipes), 1)
        recipe = room.recipes[0]
        self.assertEqual(recipe["inputs"], {1: 1})  # 1 wheat
        self.assertEqual(recipe["output"], 2)  # flour

    def test_bakery_processing_type(self):
        room = self.rooms["The Bakery"]
        self.assertEqual(room.processing_type, "bakery")

    def test_bakery_recipes(self):
        room = self.rooms["The Bakery"]
        self.assertEqual(len(room.recipes), 1)
        recipe = room.recipes[0]
        self.assertEqual(recipe["inputs"], {2: 1, 6: 1})  # 1 flour + 1 wood
        self.assertEqual(recipe["output"], 3)  # bread

    def test_vault_is_bank(self):
        """Vault should be a RoomBank."""
        from typeclasses.terrain.rooms.room_bank import RoomBank

        room = self.rooms["The Vault"]
        self.assertIsInstance(room, RoomBank)

    def test_completion_exit_exists(self):
        """Complete room should have a tagged exit to the hub."""
        exits = list(
            search_tag(self.script.instance_key, category="tutorial_exit")
        )
        completion_exits = [
            e for e in exits if e.key == "Tutorial Hub"
        ]
        self.assertTrue(len(completion_exits) > 0)


class TestTutorial2FirstRunGating(EvenniaTest):
    """Test first-run gating and graduation rewards."""

    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        _start_blockchain_mocks(self)
        super().setUp()
        from world.tutorial.tutorial_hub_builder import build_tutorial_hub

        self.hub = build_tutorial_hub()

    def tearDown(self):
        _stop_blockchain_mocks(self)
        super().tearDown()

    def _run_tutorial(self, char, key_suffix="a"):
        script = create_script(
            TutorialInstanceScript,
            key=f"test_t2_gate_{key_suffix}",
            autostart=False,
        )
        script.instance_key = script.key
        script.hub_room_id = self.hub.id
        script.start()
        script.start_tutorial(char, chunk_num=2)
        return script

    def test_first_run_gives_gold(self):
        """First run should give 20 gold."""
        gold_before = self.char1.get_gold()
        script = self._run_tutorial(self.char1, "first")
        gold_after = self.char1.get_gold()
        self.assertEqual(gold_after - gold_before, 20)
        script.collapse_instance()

    def test_second_run_no_gold(self):
        """Second run should not give additional gold."""
        script1 = self._run_tutorial(self.char1, "first2")
        script1.collapse_instance()

        gold_before = self.char1.get_gold()
        script2 = self._run_tutorial(self.char1, "second")
        gold_after = self.char1.get_gold()
        self.assertEqual(gold_after, gold_before)
        script2.collapse_instance()

    def test_graduation_reward_gives_gold(self):
        """Graduation should give 100 gold (snapshot restore + reward)."""
        gold_before = self.char1.get_gold()
        script = self._run_tutorial(self.char1, "grad")
        script.collapse_instance(give_reward=True)
        gold_after = self.char1.get_gold()
        # Snapshot restore undoes the first-run bonus, graduation adds 100
        self.assertEqual(gold_after - gold_before, 100)

    def test_graduation_reward_once_per_account(self):
        """Graduation reward should only be given once per account."""
        script1 = self._run_tutorial(self.char1, "grad1")
        script1.collapse_instance(give_reward=True)

        script2 = self._run_tutorial(self.char1, "grad2")
        gold_before = self.char1.get_gold()
        script2.collapse_instance(give_reward=True)
        gold_after = self.char1.get_gold()
        # Should not get additional gold
        self.assertEqual(gold_after, gold_before)
