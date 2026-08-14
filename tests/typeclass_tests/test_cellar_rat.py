"""
Tests for CellarRat — the Harvest Moon cellar dungeon mob.

Covers its ai_wander target selection, including the perception gate,
and the room-clearance check that unblocks forward exits on death.

evennia test --settings settings tests.typeclass_tests.test_cellar_rat
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition


class CellarRatTest(EvenniaTest):
    """A cellar rat and a player sharing a room."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.rat = create.create_object(
            "typeclasses.actors.mobs.cellar_rat.CellarRat",
            key="a cellar rat",
            location=self.room1,
            home=self.room1,
            nohome=True,
        )
        self.rat.is_alive = True
        self.char2.location = self.room2


class TestTargetSelection(CellarRatTest):
    """ai_wander picks a player it can perceive, and nothing else."""

    def test_attacks_a_visible_player(self):
        with patch.object(self.rat, "_schedule_attack") as sched:
            self.rat.ai_wander()
        sched.assert_called_once_with(self.char1)

    def test_ignores_an_invisible_player(self):
        self.char1.add_condition(Condition.INVISIBLE)
        with patch.object(self.rat, "_schedule_attack") as sched:
            self.rat.ai_wander()
        sched.assert_not_called()

    def test_ignores_a_hidden_player(self):
        self.char1.add_condition(Condition.HIDDEN)
        with patch.object(self.rat, "_schedule_attack") as sched:
            self.rat.ai_wander()
        sched.assert_not_called()

    def test_detect_invis_restores_the_target(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.rat.add_condition(Condition.DETECT_INVIS)
        with patch.object(self.rat, "_schedule_attack") as sched:
            self.rat.ai_wander()
        sched.assert_called_once_with(self.char1)

    def test_ignores_other_mobs(self):
        """p_is_character means a second rat is not a target."""
        create.create_object(
            "typeclasses.actors.mobs.cellar_rat.CellarRat",
            key="another cellar rat",
            location=self.room1,
            nohome=True,
        )
        self.char1.location = self.room2
        with patch.object(self.rat, "_schedule_attack") as sched:
            self.rat.ai_wander()
        sched.assert_not_called()

    def test_does_nothing_while_in_combat(self):
        with patch.object(self.rat.scripts, "get", return_value=["handler"]):
            with patch.object(self.rat, "_schedule_attack") as sched:
                self.rat.ai_wander()
        sched.assert_not_called()

    def test_does_nothing_when_dead(self):
        self.rat.is_alive = False
        with patch.object(self.rat, "_schedule_attack") as sched:
            self.rat.ai_wander()
        sched.assert_not_called()


class TestRoomClearance(CellarRatTest):
    """The last mob dying unblocks the room."""

    def setUp(self):
        super().setUp()
        self.room1.tags.add("not_clear", category="dungeon_room")

    @staticmethod
    def _kill(mob):
        """Both halves of death, as die() sets them.

        The clearance check reads hp, so a test that flips only the
        is_alive flag leaves a mob that is dead by one measure and alive
        by the other. die() zeroes hp first and then clears the flag, so
        a simulated death has to do both.
        """
        mob.hp = 0
        mob.is_alive = False

    def test_last_mob_death_clears_the_room(self):
        from typeclasses.actors.mobs.cellar_rat import _check_room_cleared

        self._kill(self.rat)
        _check_room_cleared(self.room1)
        self.assertFalse(
            self.room1.tags.has("not_clear", category="dungeon_room")
        )

    def test_a_surviving_mob_keeps_the_room_blocked(self):
        from typeclasses.actors.mobs.cellar_rat import _check_room_cleared

        survivor = create.create_object(
            "typeclasses.actors.mobs.cellar_rat.CellarRat",
            key="another cellar rat",
            location=self.room1,
            nohome=True,
        )
        survivor.is_alive = True
        self._kill(self.rat)
        _check_room_cleared(self.room1)
        self.assertTrue(
            self.room1.tags.has("not_clear", category="dungeon_room")
        )

    def test_a_living_player_does_not_block_clearance(self):
        """Only living mobs gate the room — the player standing in it doesn't."""
        from typeclasses.actors.mobs.cellar_rat import _check_room_cleared

        self.assertEqual(self.char1.location, self.room1)
        self._kill(self.rat)
        _check_room_cleared(self.room1)
        self.assertFalse(
            self.room1.tags.has("not_clear", category="dungeon_room")
        )
