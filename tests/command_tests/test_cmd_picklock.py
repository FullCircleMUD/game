"""
Tests for CmdPicklock — pick a lock using the SUBTERFUGE skill.

Covers the command layer: argument handling, target resolution, the
lockable/locked gates, and sightlessness. The roll itself belongs to
LockableMixin.picklock() and is exercised through it here rather than
mocked, with the DC pinned so the outcome is not a coin toss.

evennia test --settings settings tests.command_tests.test_cmd_picklock
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from commands.class_skill_cmdsets.class_skill_cmds.cmd_picklock import CmdPicklock
from enums.condition import Condition
from enums.skills_enum import skills


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class PicklockTestBase(EvenniaCommandTest):
    """A thief with a locked chest in front of them."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.class_skill_mastery_levels = {
            skills.SUBTERFUGE.value: {"mastery": 3},
        }
        self.chest = self._make_chest()

    def _make_chest(self, is_locked=True, lock_dc=5):
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="iron chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_locked = is_locked
        chest.is_open = False
        chest.lock_dc = lock_dc
        return chest

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False


class TestPicklockArguments(PicklockTestBase):

    def test_no_args(self):
        self.call(CmdPicklock(), "", "Pick the lock on what?")

    def test_a_target_that_is_not_here(self):
        self.call(CmdPicklock(), "banana", "You don't see 'banana' here.")

    def test_something_with_no_lock(self):
        create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="a stone pedestal",
            location=self.room1,
            nohome=True,
        )
        self.call(
            CmdPicklock(), "pedestal", "That doesn't have a lock to pick."
        )

    def test_something_already_unlocked(self):
        self.chest.is_locked = False
        self.call(CmdPicklock(), "chest", "iron chest is not locked.")


class TestPicklockSkill(PicklockTestBase):

    def test_an_easy_lock_opens(self):
        with patch(
            "utils.dice_roller.dice.roll_with_advantage_or_disadvantage",
            return_value=20,
        ):
            self.call(CmdPicklock(), "chest")
        self.assertFalse(self.chest.is_locked)

    def test_a_hard_lock_holds(self):
        self.chest.lock_dc = 30
        with patch(
            "utils.dice_roller.dice.roll_with_advantage_or_disadvantage",
            return_value=1,
        ):
            self.call(CmdPicklock(), "chest")
        self.assertTrue(self.chest.is_locked)

    def test_an_untrained_character_cannot_pick(self):
        self.char1.db.class_skill_mastery_levels = {}
        result = self.call(CmdPicklock(), "chest")
        self.assertIn("don't have the skill", result)
        self.assertTrue(self.chest.is_locked)


class TestPicklockSightless(PicklockTestBase):
    """
    Picking a lock needs eyes on the keyway, the same as using a key
    does, so sightlessness refuses it rather than costing time.
    """

    def test_a_dark_room_refuses_the_attempt(self):
        self._darken()
        result = self.call(CmdPicklock(), "chest")
        self.assertIn("too dark to make out", result.lower())

    def test_the_refusal_names_what_they_asked_for(self):
        self._darken()
        result = self.call(CmdPicklock(), "chest")
        self.assertIn("'chest'", result.lower())

    def test_the_refusal_does_not_claim_it_is_absent(self):
        self._darken()
        result = self.call(CmdPicklock(), "chest")
        self.assertNotIn("don't see", result.lower())

    def test_a_blinded_thief_is_refused_the_same_way(self):
        self.char1.add_condition(Condition.BLINDED)
        result = self.call(CmdPicklock(), "chest")
        self.assertIn("too dark to make out", result.lower())

    def test_nothing_is_unlocked_when_refused(self):
        self._darken()
        with patch(
            "utils.dice_roller.dice.roll_with_advantage_or_disadvantage",
            return_value=20,
        ):
            self.call(CmdPicklock(), "chest")
        self.assertTrue(self.chest.is_locked)

    def test_darkvision_picks_normally(self):
        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        with patch(
            "utils.dice_roller.dice.roll_with_advantage_or_disadvantage",
            return_value=20,
        ):
            self.call(CmdPicklock(), "chest")
        self.assertFalse(self.chest.is_locked)
