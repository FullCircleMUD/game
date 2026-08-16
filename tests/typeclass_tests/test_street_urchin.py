"""
Tests for StreetUrchin — the pickpocketing thief mob.

The urchin waits ten seconds after a player arrives, then rolls to lift
a coin. Most of the behaviour is in the guards around that roll: it does
not rob mobs, corpses, the penniless, or anyone standing next to the
watch, and it gives up if the mark leaves or a fight starts.

The delay and the dice are mocked; what is under test is which
conditions let the attempt happen at all.

evennia test --settings settings tests.typeclass_tests.test_street_urchin
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class StreetUrchinTest(EvenniaTest):
    """An urchin and a mark, in a lit street."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.urchin = create.create_object(
            "typeclasses.actors.mobs.street_urchin.StreetUrchin",
            key="a street urchin",
            location=self.room1,
            nohome=True,
        )
        self.urchin.is_alive = True
        self.char2.location = self.room2

    def tearDown(self):
        if self.urchin.pk:
            self.urchin.delete()
        super().tearDown()

    def _arrive(self, who=None):
        """Announce an arrival, returning the scheduled attempt or None."""
        with patch(
            "typeclasses.actors.mobs.street_urchin.delay"
        ) as mock_delay:
            self.urchin.at_new_arrival(who or self.char1)
        if not mock_delay.call_args:
            return None
        return mock_delay.call_args[0]


class TestWhoGetsRobbed(StreetUrchinTest):

    def test_a_player_is_marked(self):
        self.assertIsNotNone(self._arrive())

    def test_the_attempt_is_scheduled_against_the_arriver(self):
        args = self._arrive()
        self.assertEqual(args[2], self.char1)

    def test_the_attempt_waits_before_firing(self):
        """The delay is what gives the player time to walk away."""
        args = self._arrive()
        self.assertEqual(args[0], self.urchin._pickpocket_delay)

    def test_another_mob_is_not_marked(self):
        rat = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a sewer rat",
            location=self.room1,
            nohome=True,
        )
        self.assertIsNone(self._arrive(rat))

    def test_an_object_is_not_marked(self):
        self.assertIsNone(self._arrive(self.obj1))

    def test_a_dead_urchin_marks_nobody(self):
        self.urchin.is_alive = False
        self.assertIsNone(self._arrive())


class TestTheAttempt(StreetUrchinTest):
    """
    Ten seconds pass between marking and lifting, so the attempt
    re-checks everything that could have changed.
    """

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        # Enough to be worth the risk.
        patcher = patch.object(
            type(self.char1), "get_gold", return_value=100
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _attempt(self, target=None, roll=20):
        """Run the attempt with a fixed roll, returning the outcome mock."""
        with patch(
            "typeclasses.actors.mobs.street_urchin.dice.roll",
            return_value=roll,
        ), patch.object(type(self.urchin), "_steal_success") as success, \
                patch.object(type(self.urchin), "_steal_failure") as failure:
            self.urchin._try_pickpocket(target or self.char1)
        return success, failure

    def test_a_good_roll_steals(self):
        success, _ = self._attempt(roll=20)
        self.assertTrue(success.called)

    def test_a_bad_roll_is_caught(self):
        _, failure = self._attempt(roll=1)
        self.assertTrue(failure.called)

    def test_a_mark_who_left_is_not_robbed(self):
        self.char1.location = self.room2
        success, failure = self._attempt()
        self.assertFalse(success.called or failure.called)

    def test_a_mob_is_not_robbed(self):
        """The delayed re-check asks again who the mark is — a mob that
        wandered in where a player stood must not be lifted from."""
        rat = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a sewer rat",
            location=self.room1,
            nohome=True,
        )
        success, failure = self._attempt(rat)
        self.assertFalse(success.called or failure.called)

    def test_a_dead_mark_is_not_robbed(self):
        self.char1.hp = 0
        success, failure = self._attempt()
        self.assertFalse(success.called or failure.called)

    def test_a_dead_urchin_does_not_attempt(self):
        self.urchin.is_alive = False
        success, failure = self._attempt()
        self.assertFalse(success.called or failure.called)


class TestTheWatch(StreetUrchinTest):
    """Not stupid enough to steal in front of the city watch."""

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        patcher = patch.object(
            type(self.char1), "get_gold", return_value=100
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.watch = create.create_object(
            "typeclasses.actors.mobs.city_watch.CityWatch",
            key="a city watchman",
            location=self.room1,
            nohome=True,
        )

    def tearDown(self):
        if self.watch.pk:
            self.watch.delete()
        super().tearDown()

    def _attempt(self):
        with patch(
            "typeclasses.actors.mobs.street_urchin.dice.roll", return_value=20
        ), patch.object(type(self.urchin), "_steal_success") as success, \
                patch.object(type(self.urchin), "_steal_failure") as failure:
            self.urchin._try_pickpocket(self.char1)
        return success, failure

    def test_a_living_watchman_stops_the_attempt(self):
        self.watch.is_alive = True
        success, failure = self._attempt()
        self.assertFalse(success.called or failure.called)

    def test_a_dead_watchman_does_not(self):
        self.watch.is_alive = False
        success, _ = self._attempt()
        self.assertTrue(success.called)


class TestNotWorthTheRisk(StreetUrchinTest):
    """A waking mark with light pockets is left alone."""

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1

    def _attempt(self, gold):
        with patch.object(
            type(self.char1), "get_gold", return_value=gold
        ), patch(
            "typeclasses.actors.mobs.street_urchin.dice.roll", return_value=20
        ), patch.object(type(self.urchin), "_steal_success") as success, \
                patch.object(type(self.urchin), "_steal_failure") as failure:
            self.urchin._try_pickpocket(self.char1)
        return success, failure

    def test_a_thin_purse_is_not_worth_it(self):
        success, failure = self._attempt(gold=5)
        self.assertFalse(success.called or failure.called)

    def test_a_fat_purse_is(self):
        success, _ = self._attempt(gold=100)
        self.assertTrue(success.called)

    def test_a_sleeping_mark_is_robbed_regardless(self):
        self.char1.db.position = "sleeping"
        self.char1.position = "sleeping"
        success, _ = self._attempt(gold=5)
        self.assertTrue(success.called)
