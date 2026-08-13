"""
Tests for RatKing — the cellar quest boss.

Covers both aggro paths: the push path (at_new_arrival) and the pull
path (ai_wander), which differ in whether they consult perception.

evennia test --settings settings tests.typeclass_tests.test_rat_king
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition


class RatKingTest(EvenniaTest):
    """The rat king and a player sharing a room."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.king = create.create_object(
            "typeclasses.actors.mobs.rat_king.RatKing",
            key="the rat king",
            location=self.room1,
            home=self.room1,
            nohome=True,
        )
        self.king.is_alive = True
        self.char2.location = self.room2


class TestAiWanderTargeting(RatKingTest):
    """The pull path selects only players the king can perceive."""

    def test_attacks_a_visible_player(self):
        with patch("typeclasses.actors.mobs.rat_king.delay") as mock_delay:
            self.king.ai_wander()
        self.assertEqual(mock_delay.call_args.args[2], self.char1)

    def test_ignores_an_invisible_player(self):
        self.char1.add_condition(Condition.INVISIBLE)
        with patch("typeclasses.actors.mobs.rat_king.delay") as mock_delay:
            self.king.ai_wander()
        mock_delay.assert_not_called()

    def test_ignores_a_hidden_player(self):
        self.char1.add_condition(Condition.HIDDEN)
        with patch("typeclasses.actors.mobs.rat_king.delay") as mock_delay:
            self.king.ai_wander()
        mock_delay.assert_not_called()

    def test_detect_invis_restores_the_target(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.king.add_condition(Condition.DETECT_INVIS)
        with patch("typeclasses.actors.mobs.rat_king.delay") as mock_delay:
            self.king.ai_wander()
        self.assertEqual(mock_delay.call_args.args[2], self.char1)

    def test_ignores_other_mobs(self):
        create.create_object(
            "typeclasses.actors.mobs.cellar_rat.CellarRat",
            key="a cellar rat",
            location=self.room1,
            nohome=True,
        )
        self.char1.location = self.room2
        with patch("typeclasses.actors.mobs.rat_king.delay") as mock_delay:
            self.king.ai_wander()
        mock_delay.assert_not_called()

    def test_does_nothing_when_dead(self):
        self.king.is_alive = False
        with patch("typeclasses.actors.mobs.rat_king.delay") as mock_delay:
            self.king.ai_wander()
        mock_delay.assert_not_called()


class TestAtNewArrival(RatKingTest):
    """
    The push path. It still tests the arriving object directly rather
    than asking whether the king can perceive it, so an invisible
    arrival is scheduled — the room dispatcher is where that gate goes.
    """

    def test_a_player_arriving_is_scheduled(self):
        with patch("typeclasses.actors.mobs.rat_king.delay") as mock_delay:
            self.king.at_new_arrival(self.char1)
        self.assertEqual(mock_delay.call_args.args[2], self.char1)

    def test_the_king_ignores_its_own_arrival(self):
        with patch("typeclasses.actors.mobs.rat_king.delay") as mock_delay:
            self.king.at_new_arrival(self.king)
        mock_delay.assert_not_called()

    def test_a_mob_arriving_is_ignored(self):
        rat = create.create_object(
            "typeclasses.actors.mobs.cellar_rat.CellarRat",
            key="a cellar rat",
            location=self.room1,
            nohome=True,
        )
        with patch("typeclasses.actors.mobs.rat_king.delay") as mock_delay:
            self.king.at_new_arrival(rat)
        mock_delay.assert_not_called()


class TestInitiateAttackRevalidates(RatKingTest):
    """The scheduled callback re-checks before committing."""

    def test_target_who_left_is_dropped(self):
        self.char1.location = self.room2
        with patch.object(self.king, "initiate_attack") as attack:
            self.king._initiate_attack(self.char1)
        attack.assert_not_called()

    def test_dead_target_is_dropped(self):
        self.char1.hp = 0
        with patch.object(self.king, "initiate_attack") as attack:
            self.king._initiate_attack(self.char1)
        attack.assert_not_called()

    def test_valid_target_is_attacked(self):
        self.char1.hp = 30
        with patch.object(self.king, "initiate_attack") as attack:
            self.king._initiate_attack(self.char1)
        attack.assert_called_once_with(self.char1)
