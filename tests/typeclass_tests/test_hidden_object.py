"""
Tests for HiddenObjectMixin — discovery tracking, visibility checks.

evennia test --settings settings tests.typeclass_tests.test_hidden_object
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestHiddenObject(EvenniaTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.character_key = "char1_key"

    def _make_hidden_fixture(self, is_hidden=True, find_dc=15):
        obj = create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="hidden chest",
            location=self.room1,
            nohome=True,
        )
        obj.is_hidden = is_hidden
        obj.find_dc = find_dc
        return obj

    def test_hidden_object_not_visible_by_default(self):
        obj = self._make_hidden_fixture()
        self.assertFalse(obj.is_hidden_visible_to(self.char1))

    def test_non_hidden_object_visible(self):
        obj = self._make_hidden_fixture(is_hidden=False)
        self.assertTrue(obj.is_hidden_visible_to(self.char1))

    def test_discover_makes_visible(self):
        obj = self._make_hidden_fixture()
        obj.discover(self.char1)
        self.assertFalse(obj.is_hidden)  # is_hidden set to False
        self.assertTrue(obj.is_hidden_visible_to(self.char1))

    def test_discover_adds_to_discovered_by(self):
        obj = self._make_hidden_fixture()
        obj.discover(self.char1)
        self.assertIn("char1_key", obj.discovered_by)

    def test_discovered_by_persists_visibility_when_rehidden(self):
        """If object is re-hidden, a previous discoverer can still see it."""
        obj = self._make_hidden_fixture()
        obj.discover(self.char1)
        # Re-hide it (e.g. by a builder or relock timer)
        obj.is_hidden = True
        self.assertTrue(obj.is_hidden_visible_to(self.char1))

    def test_undiscovered_char_cannot_see_rehidden_object(self):
        obj = self._make_hidden_fixture()
        obj.discover(self.char1)
        obj.is_hidden = True
        # char2 never discovered it
        self.char2.db.character_key = "char2_key"
        self.assertFalse(obj.is_hidden_visible_to(self.char2))

    def test_combined_visibility_hidden_blocks(self):
        """is_visible_to() returns False for hidden + undiscovered."""
        obj = self._make_hidden_fixture()
        self.assertFalse(obj.is_visible_to(self.char1))

    def test_combined_visibility_passes_when_not_hidden(self):
        obj = self._make_hidden_fixture(is_hidden=False)
        self.assertTrue(obj.is_visible_to(self.char1))
