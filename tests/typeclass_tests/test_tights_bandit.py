"""
Tests for TightsBandit — the greeting mook in Bobbin Goode's camp.

Its whole behaviour is one shout when a player walks in, so what is
under test is when that fires and which words it uses.

The greeting is directed at the arriver, which makes it the simplest
instance of a mob acting on what it can perceive: a concealed arrival is
never announced at all (the room dispatcher stops it), and one it can
hear but not see gets a pool of lines that ask who is there rather than
bowing to someone invisible.

evennia test --settings settings tests.typeclass_tests.test_tights_bandit
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition
from typeclasses.actors.mobs.tights_bandit import (
    _GREETINGS_SEEN,
    _GREETINGS_UNSEEN,
)


class TightsBanditTest(EvenniaTest):
    """A bandit in a lit camp, with a player about to walk in."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.bandit = create.create_object(
            "typeclasses.actors.mobs.tights_bandit.TightsBandit",
            key="a bandit in striped tights",
            location=self.room1,
            nohome=True,
        )
        self.bandit.is_alive = True

    def tearDown(self):
        if self.bandit.pk:
            self.bandit.delete()
        super().tearDown()

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False

    def _greet(self, who=None):
        """Announce an arrival, returning what the room was told."""
        with patch.object(
            type(self.room1), "msg_contents"
        ) as mock_room:
            self.bandit.at_new_arrival(who or self.char1)
        if not mock_room.call_args:
            return None
        return mock_room.call_args[0][0]


class TestWhenItGreets(TightsBanditTest):

    def test_a_player_is_greeted(self):
        self.assertIsNotNone(self._greet())

    def test_another_mob_is_not_greeted(self):
        rat = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a sewer rat",
            location=self.room1,
            nohome=True,
        )
        self.assertIsNone(self._greet(rat))

    def test_a_dead_bandit_says_nothing(self):
        self.bandit.is_alive = False
        self.assertIsNone(self._greet())

    def test_the_cooldown_stops_a_chorus(self):
        """A party walking in should not set off six greetings."""
        self.assertIsNotNone(self._greet())
        self.assertIsNone(self._greet(self.char2))


class TestTheBroadcast(TightsBanditTest):

    def test_the_bandit_is_named(self):
        self.assertIn(self.bandit.key, self._greet())

    def test_from_obj_is_passed_for_filtering(self):
        """Without from_obj the shout bypasses visibility filtering."""
        with patch.object(type(self.room1), "msg_contents") as mock_room:
            self.bandit.at_new_arrival(self.char1)
        self.assertEqual(mock_room.call_args[1]["from_obj"], self.bandit)


class TestWhichWords(TightsBanditTest):
    """
    Two pools. A half-bow aimed at someone you cannot see is nonsense;
    "Oi! Who's this then?" is exactly right.
    """

    def test_a_lit_camp_uses_the_seen_pool(self):
        line = self._greet()
        self.assertTrue(any(g in line for g in _GREETINGS_SEEN))

    def test_a_dark_camp_uses_the_unseen_pool(self):
        self._darken()
        line = self._greet()
        self.assertTrue(any(g in line for g in _GREETINGS_UNSEEN))

    def test_a_blinded_bandit_uses_the_unseen_pool(self):
        self.bandit.add_condition(Condition.BLINDED)
        line = self._greet()
        self.assertTrue(any(g in line for g in _GREETINGS_UNSEEN))

    def test_darkvision_uses_the_seen_pool(self):
        self._darken()
        self.bandit.add_condition(Condition.DARKVISION)
        line = self._greet()
        self.assertTrue(any(g in line for g in _GREETINGS_SEEN))

    def test_the_pools_do_not_overlap(self):
        """A line in both would make the sight branch untestable."""
        self.assertEqual(set(_GREETINGS_SEEN) & set(_GREETINGS_UNSEEN), set())

    def test_the_unseen_pool_asks_rather_than_gestures(self):
        """Nothing in it should assume the bandit can see the arriver."""
        for line in _GREETINGS_UNSEEN:
            self.assertNotIn("bow", line)
            self.assertNotIn("grins", line)


class TestConcealedArrivals(TightsBanditTest):
    """
    Concealment is handled above this mob, by the room dispatcher, so a
    sneaking player never reaches the greeting at all. These go through
    at_object_receive rather than calling the hook directly.
    """

    def setUp(self):
        super().setUp()
        self.char1.location = self.room2

    def _walk_in(self):
        with patch.object(type(self.room1), "msg_contents") as mock_room:
            self.char1.location = self.room1
            self.room1.at_object_receive(self.char1, self.room2)
        return mock_room.call_args

    def test_a_visible_player_is_greeted(self):
        self.assertIsNotNone(self._walk_in())

    def test_an_invisible_player_gets_no_greeting(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.assertIsNone(self._walk_in())

    def test_a_hidden_player_gets_no_greeting(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.assertIsNone(self._walk_in())
