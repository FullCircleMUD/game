"""
Tests for UnseenNameMixin — what a thing is called when it can't be made out.

The rule is code, the word is content: one implementation decides *whether*
to redact, and each typeclass (or spawn rule) says what it redacts *to*.

evennia test --settings settings tests.typeclass_tests.test_unseen_name
"""

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition


class UnseenNameTest(EvenniaTest):
    """Two characters and an item in a lit room."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True

    def _darken(self):
        # has_natural_light is a read-only property derived from this.
        self.room1.always_lit = False
        self.room1.natural_light = False


class TestActorsAreSomeone(UnseenNameTest):
    """BaseActor declares "Someone" — players, NPCs and pets inherit it."""

    def test_a_visible_character_is_named(self):
        self.assertEqual(
            self.char2.get_display_name(self.char1), self.char2.key
        )

    def test_an_invisible_character_is_someone(self):
        self.char2.add_condition(Condition.INVISIBLE)
        self.assertEqual(self.char2.get_display_name(self.char1), "Someone")

    def test_a_hidden_character_is_someone(self):
        self.char2.add_condition(Condition.HIDDEN)
        self.assertEqual(self.char2.get_display_name(self.char1), "Someone")

    def test_a_character_in_the_dark_is_someone(self):
        self._darken()
        self.assertEqual(self.char2.get_display_name(self.char1), "Someone")

    def test_a_blind_looker_sees_someone(self):
        self.char1.add_condition(Condition.BLINDED)
        self.assertEqual(self.char2.get_display_name(self.char1), "Someone")

    def test_you_always_know_your_own_name(self):
        """Self is exempt however concealed — you are not "Someone" to you."""
        self.char1.add_condition(Condition.INVISIBLE)
        self._darken()
        self.assertEqual(
            self.char1.get_display_name(self.char1), self.char1.key
        )

    def test_no_looker_gets_the_real_name(self):
        self.assertEqual(self.char2.get_display_name(None), self.char2.key)

    def test_the_counters_restore_the_name(self):
        self.char2.add_condition(Condition.INVISIBLE)
        self.char1.add_condition(Condition.DETECT_INVIS)
        self.assertEqual(
            self.char2.get_display_name(self.char1), self.char2.key
        )

    def test_darkvision_restores_the_name(self):
        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        self.assertEqual(
            self.char2.get_display_name(self.char1), self.char2.key
        )


class TestMobsAreSomething(UnseenNameTest):
    """Most mobs are animals, so CombatMob overrides the word."""

    def _mob(self, typeclass="typeclasses.actors.mob.CombatMob", key="a wolf"):
        return create.create_object(
            typeclass, key=key, location=self.room1, nohome=True
        )

    def test_a_mob_in_the_dark_is_something(self):
        wolf = self._mob()
        self._darken()
        self.assertEqual(wolf.get_display_name(self.char1), "something")

    def test_a_visible_mob_is_named(self):
        wolf = self._mob()
        self.assertEqual(wolf.get_display_name(self.char1), wolf.key)

    def test_a_humanoid_mob_can_be_someone_again(self):
        """Set per instance, so a spawn rule can do it from YAML."""
        guard = self._mob(key="a city guard")
        guard.unseen_name = "Someone"
        self._darken()
        self.assertEqual(guard.get_display_name(self.char1), "Someone")


class TestObjectsAreSomething(UnseenNameTest):
    """The item roots keep the mixin default."""

    def _item(self):
        return create.create_object(
            "typeclasses.world_objects.base_world_item.WorldItem",
            key="a brass key",
            location=self.room1,
            nohome=True,
        )

    def test_a_visible_item_is_named(self):
        item = self._item()
        self.assertEqual(item.get_display_name(self.char1), item.key)

    def test_an_item_in_the_dark_is_something(self):
        item = self._item()
        self._darken()
        self.assertEqual(item.get_display_name(self.char1), "something")

    def test_an_item_is_something_to_a_blind_looker(self):
        item = self._item()
        self.char1.add_condition(Condition.BLINDED)
        self.assertEqual(item.get_display_name(self.char1), "something")

    def test_a_hidden_item_is_something(self):
        item = self._item()
        item.is_hidden = True
        self.assertEqual(item.get_display_name(self.char1), "something")

    def test_the_word_is_content_not_code(self):
        """An animated statue can be "Someone" with no new typeclass."""
        item = self._item()
        item.unseen_name = "Someone"
        self._darken()
        self.assertEqual(item.get_display_name(self.char1), "Someone")


class TestRoomsAreSomewhere(UnseenNameTest):
    """Rooms name themselves too, and take a third word."""

    def test_a_lit_room_is_named(self):
        self.assertEqual(
            self.room1.get_display_name(self.char1), self.room1.key
        )

    def test_a_dark_room_is_somewhere(self):
        self._darken()
        self.assertEqual(self.room1.get_display_name(self.char1), "Somewhere")

    def test_a_blind_looker_is_somewhere(self):
        self.char1.add_condition(Condition.BLINDED)
        self.assertEqual(self.room1.get_display_name(self.char1), "Somewhere")
