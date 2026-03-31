"""
Tests for RoomRecycleBin — orphaned object cleanup room.

evennia test --settings settings tests.typeclass_tests.test_recycle_bin
"""

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestRecycleBin(EvenniaTest):
    """Test the recycle bin room."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bin = create.create_object(
            "typeclasses.terrain.rooms.room_recycle_bin.RoomRecycleBin",
            key="Recycle Bin",
        )

    def tearDown(self):
        if self.bin.pk:
            self.bin.delete()
        super().tearDown()

    def test_character_teleported_to_safety(self):
        """Characters arriving in the bin should be moved to their home."""
        self.char1.home = self.room1
        self.char1.move_to(self.bin, quiet=True)
        # Should have been redirected out of the bin
        self.assertNotEqual(self.char1.location, self.bin)
        self.assertEqual(self.char1.location, self.room1)

    def test_character_with_no_home_goes_to_default(self):
        """Characters with no home should go to DEFAULT_HOME."""
        self.char1.home = None
        self.char1.move_to(self.bin, quiet=True)
        self.assertNotEqual(self.char1.location, self.bin)

    def test_world_item_deleted(self):
        """WorldItems arriving in the bin should be deleted."""
        from typeclasses.world_objects.base_world_item import WorldItem
        item = create.create_object(
            WorldItem,
            key="an orphaned token",
            location=self.room1,
        )
        item_pk = item.pk
        item.move_to(self.bin, quiet=True)
        # Item should have been deleted
        from evennia.objects.models import ObjectDB
        self.assertFalse(ObjectDB.objects.filter(pk=item_pk).exists())

    def test_world_fixture_deleted(self):
        """WorldFixtures arriving in the bin should be deleted."""
        from typeclasses.world_objects.base_fixture import WorldFixture
        fixture = create.create_object(
            WorldFixture,
            key="an orphaned lamp",
            location=self.room1,
        )
        fixture_pk = fixture.pk
        fixture.move_to(self.bin, quiet=True)
        from evennia.objects.models import ObjectDB
        self.assertFalse(ObjectDB.objects.filter(pk=fixture_pk).exists())

    def test_generic_object_deleted(self):
        """Any non-character, non-NFT object should be deleted."""
        obj = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="random junk",
            location=self.room1,
        )
        obj_pk = obj.pk
        obj.move_to(self.bin, quiet=True)
        from evennia.objects.models import ObjectDB
        self.assertFalse(ObjectDB.objects.filter(pk=obj_pk).exists())
