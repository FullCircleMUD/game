"""
Tests for WorldFixture, WorldSign, WorldChest, WorldItem, KeyItem.

evennia test --settings settings tests.typeclass_tests.test_world_fixtures
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class WorldFixtureTestBase(EvenniaTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)


class TestWorldFixture(WorldFixtureTestBase):

    def test_fixture_cannot_be_picked_up(self):
        fixture = create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="a statue",
            location=self.room1,
            nohome=True,
        )
        result = fixture.at_pre_get(self.char1)
        self.assertFalse(result)

    def test_fixture_has_get_false_lock(self):
        fixture = create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="a statue",
            location=self.room1,
            nohome=True,
        )
        self.assertFalse(fixture.access(self.char1, "get"))

    def test_fixture_visible_by_default(self):
        fixture = create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="a statue",
            location=self.room1,
            nohome=True,
        )
        self.assertTrue(fixture.is_visible_to(self.char1))


class TestWorldSign(WorldFixtureTestBase):

    def test_sign_renders_text(self):
        sign = create.create_object(
            "typeclasses.world_objects.sign.WorldSign",
            key="a sign",
            location=self.room1,
            nohome=True,
        )
        sign.sign_text = "Beware!"
        appearance = sign.return_appearance(self.char1)
        self.assertIn("Beware!", appearance)

    def test_sign_cannot_be_picked_up(self):
        sign = create.create_object(
            "typeclasses.world_objects.sign.WorldSign",
            key="a sign",
            location=self.room1,
            nohome=True,
        )
        self.assertFalse(sign.access(self.char1, "get"))


class TestWorldChest(WorldFixtureTestBase):

    def test_chest_starts_closed(self):
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="a chest",
            location=self.room1,
            nohome=True,
        )
        self.assertFalse(chest.is_open)

    def test_chest_cannot_be_picked_up(self):
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="a chest",
            location=self.room1,
            nohome=True,
        )
        self.assertFalse(chest.access(self.char1, "get"))

    def test_chest_open_and_close(self):
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="a chest",
            location=self.room1,
            nohome=True,
        )
        success, _ = chest.open(self.char1)
        self.assertTrue(success)
        self.assertTrue(chest.is_open)

        success, _ = chest.close(self.char1)
        self.assertTrue(success)
        self.assertFalse(chest.is_open)

    def test_chest_shows_closed_in_appearance(self):
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="a chest",
            location=self.room1,
            nohome=True,
        )
        appearance = chest.return_appearance(self.char1)
        self.assertIn("closed", appearance)

    def test_chest_shows_open_in_appearance(self):
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="a chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_open = True
        appearance = chest.return_appearance(self.char1)
        self.assertIn("open", appearance)


class TestWorldItem(WorldFixtureTestBase):

    def test_world_item_can_be_picked_up(self):
        item = create.create_object(
            "typeclasses.world_objects.base_world_item.WorldItem",
            key="a pebble",
            location=self.room1,
            nohome=True,
        )
        self.assertTrue(item.access(self.char1, "get"))

    def test_world_item_cannot_export(self):
        item = create.create_object(
            "typeclasses.world_objects.base_world_item.WorldItem",
            key="a pebble",
            location=self.room1,
            nohome=True,
        )
        self.assertFalse(item.can_export)


class TestKeyItem(WorldFixtureTestBase):

    def test_key_has_key_tag(self):
        key = create.create_object(
            "typeclasses.world_objects.key_item.KeyItem",
            key="brass key",
            location=self.char1,
            nohome=True,
        )
        key.key_tag = "brass_door"
        self.assertEqual(key.key_tag, "brass_door")

    def test_key_cannot_be_banked(self):
        key = create.create_object(
            "typeclasses.world_objects.key_item.KeyItem",
            key="brass key",
            location=self.char1,
            nohome=True,
        )
        self.assertFalse(key.can_bank)
