"""
Tests for Tutorial 1: Survival Basics room content.

Tests:
    - All 11 rooms are created with correct names
    - Rooms have tutorial_text set
    - Key items exist in correct rooms
    - Rings have correct wear_effects
    - Courtyard has correct max_height/max_depth
    - Dark room has natural_light=False
    - Combat arena allows combat
    - Pantry has bread resources

evennia test --settings settings tests.tutorial_tests.test_tutorial_1
"""

from unittest.mock import patch

from evennia.utils.create import create_object, create_script
from evennia.utils.test_resources import EvenniaTest
from evennia.utils.search import search_tag

from typeclasses.scripts.tutorial_instance import TutorialInstanceScript

_CHAR = "typeclasses.actors.character.FCMCharacter"


_NFT_ITEM_MAP = {
    "Quarterstaff": "typeclasses.items.weapons.staff_nft_item.StaffNFTItem",
    "Leather Cap": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "Wooden Torch": "typeclasses.items.holdables.torch_nft_item.TorchNFTItem",
    "Backpack": "typeclasses.items.containers.container_nft_item.ContainerNFTItem",
    "Wooden Shield": "typeclasses.items.holdables.holdable_nft_item.HoldableNFTItem",
    "Skydancer's Ring": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "Aquatic N95": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "Canteen": "typeclasses.items.water_containers.canteen_nft_item.CanteenNFTItem",
}


def _mock_spawn_nft(item_type_name, location, instance_tag):
    """Test replacement for _spawn_nft_item: create without blank tokens."""
    typeclass = _NFT_ITEM_MAP[item_type_name]
    obj = create_object(typeclass, key=item_type_name, location=location)
    obj.db.tutorial_item = True
    obj.tags.add(instance_tag, category="tutorial_item")
    return obj


class TestTutorial1Rooms(EvenniaTest):
    """Test that Tutorial 1 creates all rooms with correct properties."""

    character_typeclass = _CHAR
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from world.tutorial.tutorial_hub_builder import build_tutorial_hub

        self.hub = build_tutorial_hub()

        # Mock _spawn_nft_item to avoid needing blank RESERVE tokens in test DB
        patcher = patch(
            "world.tutorial.tutorial_1_builder._spawn_nft_item",
            side_effect=_mock_spawn_nft,
        )
        self.mock_spawn_nft = patcher.start()
        self.addCleanup(patcher.stop)

        self.script = create_script(
            TutorialInstanceScript,
            key="test_t1_rooms",
            autostart=False,
        )
        self.script.instance_key = self.script.key
        self.script.hub_room_id = self.hub.id
        self.script.start()
        self.script.start_tutorial(self.char1, chunk_num=1)

        # Collect all tagged rooms
        self.rooms = {
            r.key: r
            for r in search_tag(self.script.instance_key, category="tutorial_room")
        }

    def tearDown(self):
        if self.script.state != "done":
            self.script.collapse_instance()
        super().tearDown()

    def test_welcome_hall_exists(self):
        self.assertIn("Welcome Hall", self.rooms)

    def test_observation_chamber_exists(self):
        self.assertIn("Observation Chamber", self.rooms)

    def test_supply_room_exists(self):
        self.assertIn("Supply Room", self.rooms)

    def test_armoury_exists(self):
        self.assertIn("The Armoury", self.rooms)

    def test_courtyard_exists(self):
        self.assertIn("Open Courtyard", self.rooms)

    def test_dark_passage_exists(self):
        self.assertIn("The Dim Passage", self.rooms)

    def test_combat_arena_exists(self):
        self.assertIn("Training Arena", self.rooms)

    def test_pantry_exists(self):
        self.assertIn("The Pantry", self.rooms)

    def test_wellspring_exists(self):
        self.assertIn("The Wellspring", self.rooms)

    def test_wellspring_has_fountain(self):
        """Wellspring should have a fountain fixture."""
        room = self.rooms["The Wellspring"]
        fountains = [obj for obj in room.contents if "fountain" in obj.key.lower()]
        self.assertEqual(len(fountains), 1)

    def test_wellspring_has_canteen(self):
        """Wellspring should have a canteen."""
        room = self.rooms["The Wellspring"]
        canteens = [obj for obj in room.contents if "canteen" in obj.key.lower()]
        self.assertEqual(len(canteens), 1)

    def test_complete_room_exists(self):
        self.assertIn("Tutorial Complete", self.rooms)

    def test_all_rooms_have_tutorial_text(self):
        """Every tutorial room should have tutorial_text."""
        for name, room in self.rooms.items():
            self.assertTrue(
                room.db.tutorial_text,
                f"Room '{name}' missing tutorial_text",
            )

    def test_courtyard_vertical_range(self):
        """Courtyard should allow flying (max_height=1) and swimming (max_depth=-1)."""
        courtyard = self.rooms["Open Courtyard"]
        self.assertEqual(courtyard.db.max_height, 1)
        self.assertEqual(courtyard.db.max_depth, -1)

    def test_dark_passage_no_natural_light(self):
        dark = self.rooms["The Dim Passage"]
        self.assertFalse(dark.db.natural_light)

    def test_combat_arena_allows_combat(self):
        arena = self.rooms["Training Arena"]
        self.assertTrue(arena.allow_combat)

    def test_combat_arena_no_death(self):
        arena = self.rooms["Training Arena"]
        self.assertFalse(arena.allow_death)


class TestTutorial1Items(EvenniaTest):
    """Test items placed in Tutorial 1 rooms."""

    character_typeclass = _CHAR
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from world.tutorial.tutorial_hub_builder import build_tutorial_hub

        self.hub = build_tutorial_hub()

        # Mock _spawn_nft_item to avoid needing blank RESERVE tokens in test DB
        patcher = patch(
            "world.tutorial.tutorial_1_builder._spawn_nft_item",
            side_effect=_mock_spawn_nft,
        )
        self.mock_spawn_nft = patcher.start()
        self.addCleanup(patcher.stop)

        self.script = create_script(
            TutorialInstanceScript,
            key="test_t1_items",
            autostart=False,
        )
        self.script.instance_key = self.script.key
        self.script.hub_room_id = self.hub.id
        self.script.start()
        self.script.start_tutorial(self.char1, chunk_num=1)

        self.rooms = {
            r.key: r
            for r in search_tag(self.script.instance_key, category="tutorial_room")
        }

    def tearDown(self):
        if self.script.state != "done":
            self.script.collapse_instance()
        super().tearDown()

    def test_observation_has_fixture_sword(self):
        """Observation Chamber should have a display sword fixture."""
        room = self.rooms["Observation Chamber"]
        items = [obj for obj in room.contents if obj.key == "an ornate display sword"]
        self.assertEqual(len(items), 1)

    def test_supply_room_has_backpack(self):
        """Supply Room should have a Backpack."""
        room = self.rooms["Supply Room"]
        packs = [obj for obj in room.contents if "Backpack" in obj.key]
        self.assertEqual(len(packs), 1)

    def test_supply_room_has_wooden_shield(self):
        """Supply Room should have a Wooden Shield."""
        room = self.rooms["Supply Room"]
        shields = [obj for obj in room.contents if "Wooden Shield" in obj.key]
        self.assertEqual(len(shields), 1)

    def test_supply_room_has_gold(self):
        """Supply Room should have gold on the floor."""
        room = self.rooms["Supply Room"]
        self.assertGreater(room.get_gold(), 0)

    def test_armoury_has_skydancers_ring(self):
        """Armoury should have a Skydancer's Ring."""
        room = self.rooms["The Armoury"]
        rings = [obj for obj in room.contents if "Skydancer" in obj.key]
        self.assertEqual(len(rings), 1)

    def test_armoury_has_aquatic_n95(self):
        """Armoury should have an Aquatic N95."""
        room = self.rooms["The Armoury"]
        masks = [obj for obj in room.contents if "N95" in obj.key]
        self.assertEqual(len(masks), 1)

    def test_armoury_has_quarterstaff(self):
        """Armoury should have a Quarterstaff."""
        room = self.rooms["The Armoury"]
        staves = [obj for obj in room.contents if "Quarterstaff" in obj.key]
        self.assertEqual(len(staves), 1)

    def test_armoury_has_leather_cap(self):
        """Armoury should have a Leather Cap."""
        room = self.rooms["The Armoury"]
        caps = [obj for obj in room.contents if "Leather Cap" in obj.key]
        self.assertEqual(len(caps), 1)

    def test_dark_passage_has_torch(self):
        """The Dim Passage should have a torch."""
        room = self.rooms["The Dim Passage"]
        torches = [obj for obj in room.contents if "torch" in obj.key.lower()]
        self.assertEqual(len(torches), 1)

    def test_combat_arena_has_training_dummy(self):
        """Training Arena should have a training dummy."""
        room = self.rooms["Training Arena"]
        dummies = [
            obj for obj in room.contents
            if "training dummy" in obj.key.lower()
        ]
        self.assertEqual(len(dummies), 1)

    def test_pantry_has_bread(self):
        """The Pantry should have bread resources."""
        room = self.rooms["The Pantry"]
        bread = room.get_resource(3)  # resource ID 3 = bread
        self.assertEqual(bread, 3)

    def test_tutorial_items_flagged(self):
        """Items in tutorial rooms should be flagged as tutorial items."""
        all_items = list(
            search_tag(self.script.instance_key, category="tutorial_item")
        )
        for item in all_items:
            self.assertTrue(
                getattr(item.db, "tutorial_item", False),
                f"Item '{item.key}' missing tutorial_item flag",
            )
