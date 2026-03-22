"""
Tests for CloseableMixin — open/close state tracking and hooks.

evennia test --settings settings tests.typeclass_tests.test_closeable
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from typeclasses.mixins.closeable import CloseableMixin


class TestCloseable(EvenniaTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def _make_closeable(self, is_open=True):
        """Create a closeable object via WorldChest (has CloseableMixin)."""
        obj = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="a chest",
            location=self.room1,
            nohome=True,
        )
        obj.is_open = is_open
        return obj

    def test_open_when_closed(self):
        obj = self._make_closeable(is_open=False)
        success, msg = obj.open(self.char1)
        self.assertTrue(success)
        self.assertTrue(obj.is_open)

    def test_open_when_already_open(self):
        obj = self._make_closeable(is_open=True)
        success, msg = obj.open(self.char1)
        self.assertFalse(success)
        self.assertIn("already open", msg)

    def test_close_when_open(self):
        obj = self._make_closeable(is_open=True)
        success, msg = obj.close(self.char1)
        self.assertTrue(success)
        self.assertFalse(obj.is_open)

    def test_close_when_already_closed(self):
        obj = self._make_closeable(is_open=False)
        success, msg = obj.close(self.char1)
        self.assertFalse(success)
        self.assertIn("already closed", msg)

    def test_open_blocked_when_locked(self):
        obj = self._make_closeable(is_open=False)
        obj.is_locked = True
        success, msg = obj.open(self.char1)
        self.assertFalse(success)
        self.assertIn("locked", msg)
