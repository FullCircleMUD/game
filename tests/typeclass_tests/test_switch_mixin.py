"""
Tests for SwitchMixin — toggle mechanism for fixtures.

evennia test --settings settings tests.typeclass_tests.test_switch_mixin
"""

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestSwitchMixin(EvenniaTest):
    """Test SwitchMixin activate/deactivate behavior."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.lever = create.create_object(
            "typeclasses.world_objects.switch_fixture.SwitchFixture",
            key="a rusty lever",
            location=self.room1,
        )
        self.lever.switch_verb = "pull"
        self.lever.switch_name = "lever"

    def test_starts_inactive(self):
        self.assertFalse(self.lever.is_activated)

    def test_activate(self):
        result = self.lever.activate(self.char1)
        self.assertTrue(result)
        self.assertTrue(self.lever.is_activated)

    def test_activate_twice_fails(self):
        self.lever.activate(self.char1)
        result = self.lever.activate(self.char1)
        self.assertFalse(result)

    def test_deactivate(self):
        self.lever.activate(self.char1)
        result = self.lever.deactivate(self.char1)
        self.assertTrue(result)
        self.assertFalse(self.lever.is_activated)

    def test_deactivate_when_inactive_fails(self):
        result = self.lever.deactivate(self.char1)
        self.assertFalse(result)

    def test_one_way_switch(self):
        """can_deactivate=False prevents toggling back."""
        self.lever.can_deactivate = False
        self.lever.activate(self.char1)
        result = self.lever.deactivate(self.char1)
        self.assertFalse(result)
        self.assertTrue(self.lever.is_activated)

    def test_at_activate_hook_called(self):
        """at_activate should fire on activation."""
        called = []
        self.lever.at_activate = lambda caller: called.append(caller)
        self.lever.activate(self.char1)
        self.assertEqual(called, [self.char1])

    def test_at_deactivate_hook_called(self):
        """at_deactivate should fire on deactivation."""
        called = []
        self.lever.at_deactivate = lambda caller: called.append(caller)
        self.lever.activate(self.char1)
        self.lever.deactivate(self.char1)
        self.assertEqual(called, [self.char1])

    def test_immovable(self):
        """SwitchFixture should be immovable."""
        self.assertFalse(self.lever.at_pre_get(self.char1))
