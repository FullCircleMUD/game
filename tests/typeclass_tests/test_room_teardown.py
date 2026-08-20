"""
Tests for RoomBase.at_object_delete — the room empties itself on teardown.

Evennia relocates a deleted room's contents to their home, which lands
mobs and items in Limbo on every wb_build redeploy. The hook deletes them
first; characters are left alone and go home as before.
"""

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class TestRoomTeardown(EvenniaTest):
    """Test what survives a room deletion."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_object_in_room_is_deleted(self):
        """A plain object in the room goes with it."""
        obj = create_object(
            "typeclasses.objects.Object", key="a crate", location=self.room1
        )
        self.room1.delete()
        self.assertIsNone(obj.pk)

    def test_mob_in_room_is_deleted(self):
        """A mob in the room goes with it, rather than to Limbo."""
        mob = create_object(
            "typeclasses.actors.mob.CombatMob", key="a rat", location=self.room1
        )
        self.room1.delete()
        self.assertIsNone(mob.pk)

    def test_character_survives(self):
        """A character is skipped, and is relocated by Evennia as before."""
        self.char1.location = self.room1
        self.room1.delete()
        self.assertIsNotNone(self.char1.pk)
        self.assertNotEqual(self.char1.location, self.room1)

    def test_room_is_deleted(self):
        """The hook returns True, so the room delete still goes through."""
        self.assertTrue(self.room1.delete())
