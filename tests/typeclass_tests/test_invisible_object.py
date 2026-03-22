"""
Tests for InvisibleObjectMixin — DETECT_INVIS gate on visibility.

evennia test --settings settings tests.typeclass_tests.test_invisible_object
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.condition import Condition


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestInvisibleObject(EvenniaTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def _make_invisible_fixture(self, is_invisible=True):
        obj = create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="invisible pedestal",
            location=self.room1,
            nohome=True,
        )
        obj.is_invisible = is_invisible
        return obj

    def test_invisible_object_not_visible_without_detect(self):
        obj = self._make_invisible_fixture()
        self.assertFalse(obj.is_invis_visible_to(self.char1))

    def test_invisible_object_visible_with_detect_invis(self):
        obj = self._make_invisible_fixture()
        self.char1.add_condition(Condition.DETECT_INVIS)
        self.assertTrue(obj.is_invis_visible_to(self.char1))

    def test_non_invisible_object_visible(self):
        obj = self._make_invisible_fixture(is_invisible=False)
        self.assertTrue(obj.is_invis_visible_to(self.char1))

    def test_combined_visibility_invisible_blocks(self):
        obj = self._make_invisible_fixture()
        self.assertFalse(obj.is_visible_to(self.char1))

    def test_combined_visibility_with_detect_invis(self):
        obj = self._make_invisible_fixture()
        self.char1.add_condition(Condition.DETECT_INVIS)
        self.assertTrue(obj.is_visible_to(self.char1))
