"""
Tests for the tutorial instance system.

Tests:
    - Hub builder creates room with correct tags
    - Instance script creates and collapses properly
    - Tutorial items are stripped on exit
    - Graduation reward given once per account
    - Training dummy mob exists and has correct attributes

evennia test --settings settings tests.tutorial_tests.test_tutorial_instance
"""

from unittest.mock import patch

from evennia.utils.create import create_object, create_script
from evennia.utils.test_resources import EvenniaTest
from evennia.utils.search import search_tag

from typeclasses.scripts.tutorial_instance import TutorialInstanceScript

_CHAR = "typeclasses.actors.character.FCMCharacter"

# Shared mock target for _spawn_nft_item in the tutorial builder.
_NFT_MOCK_TARGET = "world.tutorial.tutorial_1_builder._spawn_nft_item"


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


def _create_tutorial_script(**kwargs):
    """Create a TutorialInstanceScript using create_script (returns obj, not tuple)."""
    script = create_script(TutorialInstanceScript, **kwargs)
    return script


class TestTutorialHub(EvenniaTest):
    """Test the tutorial hub builder."""

    def create_script(self):
        pass

    def test_build_hub_creates_room(self):
        """build_tutorial_hub() should create a room with the correct tag."""
        from world.tutorial.tutorial_hub_builder import build_tutorial_hub

        hub = build_tutorial_hub()
        self.assertIsNotNone(hub)
        self.assertEqual(hub.key, "Tutorial Hub")
        tags = hub.tags.get(category="tutorial_hub", return_list=True)
        self.assertIn("tutorial_hub", tags)

    def test_build_hub_idempotent(self):
        """Calling build_tutorial_hub() twice should return the same room."""
        from world.tutorial.tutorial_hub_builder import build_tutorial_hub

        hub1 = build_tutorial_hub()
        hub2 = build_tutorial_hub()
        self.assertEqual(hub1.id, hub2.id)

    def test_hub_has_tutorial_text(self):
        """Hub should have tutorial_text set."""
        from world.tutorial.tutorial_hub_builder import build_tutorial_hub

        hub = build_tutorial_hub()
        self.assertTrue(hub.db.tutorial_text)

    def test_hub_is_safe_zone(self):
        """Hub should not allow combat."""
        from world.tutorial.tutorial_hub_builder import build_tutorial_hub

        hub = build_tutorial_hub()
        self.assertFalse(hub.allow_combat)


class TestTutorialInstanceScript(EvenniaTest):
    """Test the TutorialInstanceScript lifecycle."""

    character_typeclass = _CHAR
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from world.tutorial.tutorial_hub_builder import build_tutorial_hub

        self.hub = build_tutorial_hub()

        # Mock _spawn_nft_item to avoid needing blank RESERVE tokens
        patcher = patch(_NFT_MOCK_TARGET, side_effect=_mock_spawn_nft)
        self.mock_spawn_nft = patcher.start()
        self.addCleanup(patcher.stop)

    def test_instance_creates_rooms(self):
        """Starting tutorial 1 should create tagged rooms."""
        script = _create_tutorial_script(
            key="test_tut_1",
            autostart=False,
        )
        script.instance_key = script.key
        script.hub_room_id = self.hub.id
        script.start()
        script.start_tutorial(self.char1, chunk_num=1)

        # Character should be in a tutorial room
        self.assertIsNotNone(self.char1.location)
        self.assertEqual(self.char1.location.key, "Welcome Hall")

        # Should have tagged rooms
        rooms = list(search_tag(script.instance_key, category="tutorial_room"))
        self.assertGreater(len(rooms), 0)

        # Cleanup
        script.collapse_instance()

    def test_instance_collapse_strips_items(self):
        """Collapsing should remove tutorial items from character."""
        script = _create_tutorial_script(
            key="test_tut_strip",
            autostart=False,
        )
        script.instance_key = script.key
        script.hub_room_id = self.hub.id
        script.start()
        script.start_tutorial(self.char1, chunk_num=1)

        # Give the character a tutorial item
        item = create_object(
            "evennia.objects.objects.DefaultObject",
            key="test tutorial item",
            location=self.char1,
            attributes=[("tutorial_item", True)],
        )

        # Collapse
        script.collapse_instance()

        # Item should be deleted
        self.assertFalse(item.pk)  # deleted objects have no pk

    @patch("blockchain.xrpl.services.resource.ResourceService.craft_input")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_instance_collapse_returns_resources(self, _mock_out, _mock_in):
        """Collapsing should strip tutorial resources."""
        script = _create_tutorial_script(
            key="test_tut_res",
            autostart=False,
        )
        script.instance_key = script.key
        script.hub_room_id = self.hub.id
        script.start()
        script.start_tutorial(self.char1, chunk_num=1)

        # Give the character some bread (resource 3)
        self.char1.receive_resource_from_reserve(3, 5)
        self.assertEqual(self.char1.get_resource(3), 5)

        # Collapse
        script.collapse_instance()

        # Bread should be gone
        self.assertEqual(self.char1.get_resource(3), 0)

    def test_instance_collapse_deletes_rooms(self):
        """Collapsing should delete all tagged rooms."""
        script = _create_tutorial_script(
            key="test_tut_rooms",
            autostart=False,
        )
        script.instance_key = script.key
        script.hub_room_id = self.hub.id
        script.start()
        script.start_tutorial(self.char1, chunk_num=1)

        instance_key = script.instance_key
        rooms_before = list(search_tag(instance_key, category="tutorial_room"))
        self.assertGreater(len(rooms_before), 0)

        # Collapse
        script.collapse_instance()

        # No tagged rooms should remain
        rooms_after = list(search_tag(instance_key, category="tutorial_room"))
        self.assertEqual(len(rooms_after), 0)

    def test_instance_collapse_returns_to_hub(self):
        """After collapse, character should be at the hub."""
        script = _create_tutorial_script(
            key="test_tut_hub",
            autostart=False,
        )
        script.instance_key = script.key
        script.hub_room_id = self.hub.id
        script.start()
        script.start_tutorial(self.char1, chunk_num=1)

        script.collapse_instance()

        self.assertEqual(self.char1.location, self.hub)


class TestGraduationReward(EvenniaTest):
    """Test the graduation reward system."""

    character_typeclass = _CHAR
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from world.tutorial.tutorial_hub_builder import build_tutorial_hub

        self.hub = build_tutorial_hub()

        # Mock _spawn_nft_item to avoid needing blank RESERVE tokens
        patcher = patch(_NFT_MOCK_TARGET, side_effect=_mock_spawn_nft)
        self.mock_spawn_nft = patcher.start()
        self.addCleanup(patcher.stop)

    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_reward_gives_bread_and_gold(self, _mock_res, _mock_gold):
        """Graduation reward should give bread and gold."""
        script = _create_tutorial_script(
            key="test_tut_reward",
            autostart=False,
        )
        script.instance_key = script.key
        script.hub_room_id = self.hub.id
        script.start()
        script.start_tutorial(self.char1, chunk_num=1)

        # Collapse WITH reward
        script.collapse_instance(give_reward=True)

        # Should have 2 bread and 10 gold
        self.assertEqual(self.char1.get_resource(3), 2)
        self.assertEqual(self.char1.get_gold(), 10)

    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_input")
    def test_reward_only_once(self, _mock_in, _mock_res, _mock_gold):
        """Graduation reward should only be given once per account."""
        # First run
        script1 = _create_tutorial_script(
            key="test_tut_once1",
            autostart=False,
        )
        script1.instance_key = script1.key
        script1.hub_room_id = self.hub.id
        script1.start()
        script1.start_tutorial(self.char1, chunk_num=1)
        script1.collapse_instance(give_reward=True)

        gold_after_first = self.char1.get_gold()

        # Second run — should not get more gold
        script2 = _create_tutorial_script(
            key="test_tut_once2",
            autostart=False,
        )
        script2.instance_key = script2.key
        script2.hub_room_id = self.hub.id
        script2.start()
        script2.start_tutorial(self.char1, chunk_num=1)
        script2.collapse_instance(give_reward=True)

        self.assertEqual(self.char1.get_gold(), gold_after_first)

    def test_no_reward_when_not_requested(self):
        """Collapsing without give_reward should not give anything."""
        script = _create_tutorial_script(
            key="test_tut_noreward",
            autostart=False,
        )
        script.instance_key = script.key
        script.hub_room_id = self.hub.id
        script.start()
        script.start_tutorial(self.char1, chunk_num=1)

        script.collapse_instance(give_reward=False)

        self.assertEqual(self.char1.get_gold(), 0)
        self.assertEqual(self.char1.get_resource(3), 0)


class TestCollapseUnequipsItems(EvenniaTest):
    """Test that collapse_instance properly unequips items before deleting."""

    character_typeclass = _CHAR
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from world.tutorial.tutorial_hub_builder import build_tutorial_hub

        self.hub = build_tutorial_hub()

        patcher = patch(_NFT_MOCK_TARGET, side_effect=_mock_spawn_nft)
        self.mock_spawn_nft = patcher.start()
        self.addCleanup(patcher.stop)

    def _make_script(self, key):
        script = _create_tutorial_script(key=key, autostart=False)
        script.instance_key = script.key
        script.hub_room_id = self.hub.id
        script.start()
        script.start_tutorial(self.char1, chunk_num=1)
        return script

    def _equip_tutorial_item(self, slot, wear_effects=None):
        """Create a tutorial wearable, put it in a wearslot, apply effects."""
        from typeclasses.items.wearables.wearable_nft_item import WearableNFTItem

        item = create_object(
            WearableNFTItem, key="test ring", location=self.char1,
        )
        item.db.tutorial_item = True
        item.wearslot = slot
        if wear_effects:
            item.wear_effects = wear_effects

        # Equip via the wearslot system so at_wear fires
        self.char1.wear(item)
        return item

    def test_collapse_removes_condition_from_equipped_item(self):
        """Equipped tutorial item with a condition effect should have that
        condition cleaned up on collapse."""
        script = self._make_script("test_cond_clean")
        item = self._equip_tutorial_item(
            "LEFT_RING_FINGER",
            wear_effects=[{"type": "condition", "condition": "water_breathing"}],
        )

        # Condition should be active
        self.assertTrue(self.char1.has_condition("water_breathing"))
        self.assertTrue(self.char1.is_worn(item))

        script.collapse_instance()

        # Condition should be gone and item deleted
        self.assertFalse(self.char1.has_condition("water_breathing"))
        self.assertFalse(item.pk)

    def test_collapse_removes_fly_condition(self):
        """Fly condition from equipped tutorial item should be removed on collapse."""
        script = self._make_script("test_fly_clean")
        self._equip_tutorial_item(
            "LEFT_RING_FINGER",
            wear_effects=[{"type": "condition", "condition": "fly"}],
        )

        self.assertTrue(self.char1.has_condition("fly"))

        script.collapse_instance()

        self.assertFalse(self.char1.has_condition("fly"))

    def test_collapse_removes_stat_bonus_from_equipped_item(self):
        """Stat bonuses from equipped tutorial items should be cleared on collapse."""
        script = self._make_script("test_stat_clean")
        base_str = self.char1.base_strength
        self._equip_tutorial_item(
            "LEFT_RING_FINGER",
            wear_effects=[{"type": "stat_bonus", "stat": "strength", "value": 4}],
        )

        self.assertEqual(self.char1.strength, base_str + 4)

        script.collapse_instance()

        self.assertEqual(self.char1.strength, base_str)

    def test_collapse_handles_unequipped_tutorial_item(self):
        """Tutorial items in inventory (not equipped) should just be deleted."""
        script = self._make_script("test_inv_clean")

        item = create_object(
            "evennia.objects.objects.DefaultObject",
            key="loose tutorial item",
            location=self.char1,
            attributes=[("tutorial_item", True)],
        )

        script.collapse_instance()

        self.assertFalse(item.pk)

    def test_collapse_clears_wearslot(self):
        """After collapse, the wearslot that held the tutorial item should be empty."""
        script = self._make_script("test_slot_clean")
        self._equip_tutorial_item(
            "LEFT_RING_FINGER",
            wear_effects=[{"type": "condition", "condition": "water_breathing"}],
        )

        wearslots = self.char1.db.wearslots or {}
        self.assertIsNotNone(wearslots.get("LEFT_RING_FINGER"))

        script.collapse_instance()

        wearslots = self.char1.db.wearslots or {}
        self.assertIsNone(wearslots.get("LEFT_RING_FINGER"))


class TestTrainingDummy(EvenniaTest):
    """Test the training dummy mob."""

    def create_script(self):
        pass

    def test_dummy_attributes(self):
        """Training dummy should have correct base attributes."""
        from typeclasses.actors.mobs.training_dummy import TrainingDummy

        dummy = create_object(TrainingDummy, key="test dummy")
        self.assertEqual(dummy.hp, 20)
        self.assertEqual(dummy.hp_max, 20)
        self.assertEqual(dummy.damage_dice, "1d2")
        self.assertFalse(dummy.is_aggressive_to_players)
        self.assertEqual(dummy.respawn_delay, 5)

    def test_dummy_does_not_wander(self):
        """Training dummy ai_wander should be a no-op."""
        from typeclasses.actors.mobs.training_dummy import TrainingDummy

        dummy = create_object(TrainingDummy, key="test dummy")
        room = create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase", key="TestRoom"
        )
        dummy.location = room
        # Should not raise or move
        dummy.ai_wander()
        self.assertEqual(dummy.location, room)
