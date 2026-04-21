"""
Tests for Tutorial 3: Growth & Social.

Tests:
    - All 8 rooms are created with correct names
    - Shortcut Workshop has backpack, canteen, fountain, dummy
    - TrainerNPC present with correct trainable_skills and trainer_masteries
    - GuildmasterNPC present with correct guild_class
    - Companion NPC present
    - Graduation reward gated per account
    - First-run skill point + gold given, repeat not given
    - All rooms have tutorial_text and guide_context

evennia test --settings settings tests.tutorial_tests.test_tutorial_3
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


_NFT_ITEM_MAP = {
    "Backpack": "typeclasses.items.containers.container_nft_item.ContainerNFTItem",
    "Canteen": "typeclasses.items.water_containers.canteen_nft_item.CanteenNFTItem",
}


def _mock_spawn_nft(item_type_name, location, instance_tag):
    """Test replacement for _spawn_nft_item: create without blank tokens."""
    typeclass = _NFT_ITEM_MAP[item_type_name]
    obj = create_object(typeclass, key=item_type_name, location=location)
    obj.db.tutorial_item = True
    obj.tags.add(instance_tag, category="tutorial_item")
    return obj


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


class TestTutorial3Rooms(EvenniaTest):
    """Test that Tutorial 3 creates all rooms with correct properties."""

    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        _start_blockchain_mocks(self)
        super().setUp()
        # Mock _spawn_nft_item to avoid needing blank RESERVE tokens in test DB
        patcher = patch(
            "world.tutorial.tutorial_3_builder._spawn_nft_item",
            side_effect=_mock_spawn_nft,
        )
        self.mock_spawn_nft = patcher.start()
        self.addCleanup(patcher.stop)

        from world.tutorial.tutorial_hub_builder import build_tutorial_hub

        self.hub = build_tutorial_hub()

        self.script = create_script(
            TutorialInstanceScript,
            key="test_t3_rooms",
            autostart=False,
        )
        self.script.instance_key = self.script.key
        self.script.hub_room_id = self.hub.id
        self.script.start()
        self.script.start_tutorial(self.char1, chunk_num=3, immediate=True)

        # Collect all tagged rooms
        self.rooms = {
            r.key: r
            for r in search_tag(self.script.instance_key, category="tutorial_room")
        }

    def tearDown(self):
        if self.script.state != "done":
            self.script.collapse_instance(immediate=True)
        _stop_blockchain_mocks(self)
        super().tearDown()

    def test_shortcut_workshop_exists(self):
        self.assertIn("The Shortcut Workshop", self.rooms)

    def test_shortcut_workshop_has_fountain(self):
        """Shortcut Workshop should have a fountain fixture."""
        room = self.rooms["The Shortcut Workshop"]
        fountains = [obj for obj in room.contents if "fountain" in obj.key.lower()]
        self.assertEqual(len(fountains), 1)

    def test_shortcut_workshop_has_dummy(self):
        """Shortcut Workshop should have a practice dummy."""
        room = self.rooms["The Shortcut Workshop"]
        dummies = [obj for obj in room.contents if "dummy" in obj.key.lower()]
        self.assertEqual(len(dummies), 1)

    def test_shortcut_workshop_has_backpack(self):
        """Shortcut Workshop should have a backpack."""
        room = self.rooms["The Shortcut Workshop"]
        backpacks = [obj for obj in room.contents if "backpack" in obj.key.lower()]
        self.assertEqual(len(backpacks), 1)

    def test_shortcut_workshop_has_canteen(self):
        """Shortcut Workshop should have a canteen."""
        room = self.rooms["The Shortcut Workshop"]
        canteens = [obj for obj in room.contents if "canteen" in obj.key.lower()]
        self.assertEqual(len(canteens), 1)

    def test_shortcut_workshop_has_slate_board(self):
        """Shortcut Workshop should have a slate board."""
        room = self.rooms["The Shortcut Workshop"]
        boards = [obj for obj in room.contents if "slate" in obj.key.lower()]
        self.assertEqual(len(boards), 1)

    def test_hall_of_records_exists(self):
        self.assertIn("Hall of Records", self.rooms)

    def test_speaking_chamber_exists(self):
        self.assertIn("The Speaking Chamber", self.rooms)

    def test_hall_of_skills_exists(self):
        self.assertIn("Hall of Skills", self.rooms)

    def test_training_grounds_exists(self):
        self.assertIn("The Training Grounds", self.rooms)

    def test_guild_hall_exists(self):
        self.assertIn("The Guild Hall", self.rooms)

    def test_companion_room_exists(self):
        self.assertIn("The Companion Room", self.rooms)

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

    def test_mirror_fixture_exists(self):
        """Hall of Records should have a mirror fixture."""
        room = self.rooms["Hall of Records"]
        mirrors = [obj for obj in room.contents if "mirror" in obj.key.lower()]
        self.assertEqual(len(mirrors), 1)

    def test_message_board_fixture_exists(self):
        """Speaking Chamber should have a message board fixture."""
        room = self.rooms["The Speaking Chamber"]
        boards = [obj for obj in room.contents if "board" in obj.key.lower()]
        self.assertEqual(len(boards), 1)

    def test_skill_tome_fixture_exists(self):
        """Hall of Skills should have a skill tome fixture."""
        room = self.rooms["Hall of Skills"]
        tomes = [obj for obj in room.contents if "tome" in obj.key.lower()]
        self.assertEqual(len(tomes), 1)


class TestTutorial3NPCs(EvenniaTest):
    """Test NPCs in Tutorial 3."""

    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        _start_blockchain_mocks(self)
        super().setUp()
        patcher = patch(
            "world.tutorial.tutorial_3_builder._spawn_nft_item",
            side_effect=_mock_spawn_nft,
        )
        self.mock_spawn_nft = patcher.start()
        self.addCleanup(patcher.stop)

        from world.tutorial.tutorial_hub_builder import build_tutorial_hub

        self.hub = build_tutorial_hub()

        self.script = create_script(
            TutorialInstanceScript,
            key="test_t3_npcs",
            autostart=False,
        )
        self.script.instance_key = self.script.key
        self.script.hub_room_id = self.hub.id
        self.script.start()
        self.script.start_tutorial(self.char1, chunk_num=3, immediate=True)

        self.rooms = {
            r.key: r
            for r in search_tag(self.script.instance_key, category="tutorial_room")
        }

    def tearDown(self):
        if self.script.state != "done":
            self.script.collapse_instance(immediate=True)
        _stop_blockchain_mocks(self)
        super().tearDown()

    def test_trainer_exists(self):
        """Training Grounds should have Instructor Bren."""
        room = self.rooms["The Training Grounds"]
        trainers = [
            obj for obj in room.contents
            if obj.key == "Instructor Bren"
        ]
        self.assertEqual(len(trainers), 1)

    def test_trainer_skills(self):
        """Trainer should teach blacksmith, carpenter, alchemist."""
        room = self.rooms["The Training Grounds"]
        trainer = [
            obj for obj in room.contents
            if obj.key == "Instructor Bren"
        ][0]
        self.assertIn("blacksmith", trainer.trainable_skills)
        self.assertIn("carpenter", trainer.trainable_skills)
        self.assertIn("alchemist", trainer.trainable_skills)

    def test_trainer_masteries(self):
        """Trainer should have EXPERT (3) mastery in all skills."""
        room = self.rooms["The Training Grounds"]
        trainer = [
            obj for obj in room.contents
            if obj.key == "Instructor Bren"
        ][0]
        for skill in ["blacksmith", "carpenter", "alchemist"]:
            self.assertEqual(trainer.trainer_masteries[skill], 3)

    def test_trainer_is_general(self):
        """Trainer should have no class restriction."""
        room = self.rooms["The Training Grounds"]
        trainer = [
            obj for obj in room.contents
            if obj.key == "Instructor Bren"
        ][0]
        self.assertIsNone(trainer.trainer_class)

    def test_guildmaster_exists(self):
        """Guild Hall should have Guild Warden Aldric."""
        room = self.rooms["The Guild Hall"]
        guildmasters = [
            obj for obj in room.contents
            if obj.key == "Guild Warden Aldric"
        ]
        self.assertEqual(len(guildmasters), 1)

    def test_guildmaster_class(self):
        """Guildmaster should be for warrior class."""
        room = self.rooms["The Guild Hall"]
        gm = [
            obj for obj in room.contents
            if obj.key == "Guild Warden Aldric"
        ][0]
        self.assertEqual(gm.guild_class, "warrior")

    def test_companion_exists(self):
        """Companion Room should have Squire Finn."""
        room = self.rooms["The Companion Room"]
        companions = [
            obj for obj in room.contents
            if obj.key == "Squire Finn"
        ]
        self.assertEqual(len(companions), 1)

    def test_guide_spawned(self):
        """Tutorial guides (Pip) should be spawned — one per room."""
        mobs = list(
            search_tag(self.script.instance_key, category="tutorial_mob")
        )
        guides = [m for m in mobs if m.key == "Pip"]
        # Each tutorial room gets its own Pip
        self.assertGreater(len(guides), 0)


class TestTutorial3FirstRunGating(EvenniaTest):
    """Test first-run gating and graduation rewards."""

    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        _start_blockchain_mocks(self)
        super().setUp()
        patcher = patch(
            "world.tutorial.tutorial_3_builder._spawn_nft_item",
            side_effect=_mock_spawn_nft,
        )
        self.mock_spawn_nft = patcher.start()
        self.addCleanup(patcher.stop)

        from world.tutorial.tutorial_hub_builder import build_tutorial_hub

        self.hub = build_tutorial_hub()

    def tearDown(self):
        _stop_blockchain_mocks(self)
        super().tearDown()

    def _run_tutorial(self, char, key_suffix="a"):
        script = create_script(
            TutorialInstanceScript,
            key=f"test_t3_gate_{key_suffix}",
            autostart=False,
        )
        script.instance_key = script.key
        script.hub_room_id = self.hub.id
        script.start()
        script.start_tutorial(char, chunk_num=3, immediate=True)
        return script

    def test_first_run_no_gold(self):
        """First run should not give gold (no first-run bonus in tutorial 3)."""
        gold_before = self.char1.get_gold()
        script = self._run_tutorial(self.char1, "first")
        gold_after = self.char1.get_gold()
        self.assertEqual(gold_after, gold_before)
        script.collapse_instance(immediate=True)

    def test_graduation_reward_gives_gold(self):
        """Graduation should give 20 gold."""
        gold_before = self.char1.get_gold()
        script = self._run_tutorial(self.char1, "grad")
        script.collapse_instance(give_reward=True, immediate=True)
        gold_after = self.char1.get_gold()
        # Snapshot restore is a no-op (no first-run bonus), graduation adds 20
        self.assertEqual(gold_after - gold_before, 20)

    def test_graduation_reward_once_per_account(self):
        """Graduation reward should only be given once per account."""
        script1 = self._run_tutorial(self.char1, "grad1")
        script1.collapse_instance(give_reward=True, immediate=True)

        script2 = self._run_tutorial(self.char1, "grad2")
        gold_before = self.char1.get_gold()
        script2.collapse_instance(give_reward=True, immediate=True)
        gold_after = self.char1.get_gold()
        self.assertEqual(gold_after, gold_before)
