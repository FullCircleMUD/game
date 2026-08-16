"""
Tests for the stealth check on room entry — when it runs, and what the
room learns as a result.

The roll is against the occupants of the room being entered, so it asks
whether they catch you crossing the threshold. That means it has to
resolve before anything is said: a revealed thief should produce the same
arrival everyone else does, and mobs should be told about them. Resolve
it after and a failed roll leaves someone standing in plain sight that
nothing in the room was ever told about — sneaking in badly would be
safer than walking in openly.

It resolves in ``BaseActor.announce_move_to``. Followers are the
exception: they travel with ``quiet=True`` and Evennia skips the announce
hooks on a quiet move, so ``FCMCharacter.at_post_move`` catches them,
guarded on ``move_type == "follow"``. One roll per move either way.

evennia test --settings settings tests.typeclass_tests.test_hidden_on_entry
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition


class HiddenEntryTest(EvenniaTest):
    """A thief in one room, a mob waiting in the next."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.room2.always_lit = True

        if self.exit:
            self.exit.delete()
        self.north = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.room2,
        )

        self.mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a sewer rat",
            location=self.room2,
            nohome=True,
        )
        self.char1.location = self.room1
        self.char1.add_condition(Condition.HIDDEN)

    def tearDown(self):
        if self.mob.pk:
            self.mob.delete()
        if self.north.pk:
            self.north.delete()
        super().tearDown()

    def _rig(self, spotted):
        """Force the stealth roll to fail (spotted) or pass."""
        return patch(
            "utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
            return_value=1 if spotted else 100,
        )

    def _walk_north(self):
        """Move through the exit, returning the mob-notify mock."""
        with patch.object(type(self.mob), "at_new_arrival") as mock_notify:
            self.north.at_traverse(self.char1, self.room2)
        return mock_notify


class TestTheRollResolvesFirst(HiddenEntryTest):
    """
    The ordering this file exists for. The room decides who to notify
    using the arriver's concealment state, so the roll has to have
    happened by then.
    """

    def test_a_spotted_thief_is_announced_to_mobs(self):
        with self._rig(spotted=True):
            self.assertTrue(self._walk_north().called)

    def test_an_unspotted_thief_is_not(self):
        with self._rig(spotted=False):
            self.assertFalse(self._walk_north().called)

    def test_a_spotted_thief_loses_the_condition(self):
        with self._rig(spotted=True):
            self._walk_north()
        self.assertFalse(self.char1.has_condition(Condition.HIDDEN))

    def test_an_unspotted_thief_keeps_it(self):
        with self._rig(spotted=False):
            self._walk_north()
        self.assertTrue(self.char1.has_condition(Condition.HIDDEN))

    def test_an_unconcealed_arrival_is_unaffected(self):
        self.char1.remove_condition(Condition.HIDDEN)
        self.assertTrue(self._walk_north().called)


class TestItRunsOnce(HiddenEntryTest):
    """One roll per move. Two would double a thief's chance of being seen."""

    def test_a_normal_move_rolls_once(self):
        with patch.object(
            type(self.char1), "_check_hidden_on_entry"
        ) as mock_check:
            self.north.at_traverse(self.char1, self.room2)
        self.assertEqual(mock_check.call_count, 1)

    def test_an_unconcealed_move_does_not_roll(self):
        self.char1.remove_condition(Condition.HIDDEN)
        with patch.object(
            type(self.char1), "_check_hidden_on_entry"
        ) as mock_check:
            self.north.at_traverse(self.char1, self.room2)
        self.assertFalse(mock_check.called)


class TestFollowers(HiddenEntryTest):
    """
    Followers travel with quiet=True, so the announce seam never runs for
    them. Without the fallback a hidden character could follow a group
    across the map without rolling once.
    """

    def _follow_north(self):
        """Move as a follower does — quietly, with move_type=follow."""
        with patch.object(type(self.mob), "at_new_arrival") as mock_notify:
            self.char1.move_to(
                self.room2, move_type="follow", quiet=True,
            )
        return mock_notify

    def test_a_following_thief_still_rolls(self):
        with patch.object(
            type(self.char1), "_check_hidden_on_entry"
        ) as mock_check:
            self.char1.move_to(
                self.room2, move_type="follow", quiet=True,
            )
        self.assertEqual(mock_check.call_count, 1)

    def test_a_spotted_follower_loses_the_condition(self):
        with self._rig(spotted=True):
            self._follow_north()
        self.assertFalse(self.char1.has_condition(Condition.HIDDEN))

    def test_an_unspotted_follower_keeps_it(self):
        with self._rig(spotted=False):
            self._follow_north()
        self.assertTrue(self.char1.has_condition(Condition.HIDDEN))

    def test_the_mob_is_told_about_the_party_not_the_thief(self):
        """The check runs after the arrival, so the room notices late.

        Accepted deliberately: a group walking in is cover, and an
        aggressive mob attacking any member drags the thief into a fight
        that strips HIDDEN anyway.
        """
        with self._rig(spotted=True):
            self.assertFalse(self._follow_north().called)

    def test_a_teleport_does_not_roll(self):
        """Materialising in purgatory is not sneaking in."""
        with patch.object(
            type(self.char1), "_check_hidden_on_entry"
        ) as mock_check:
            self.char1.move_to(
                self.room2, move_type="teleport", quiet=True,
            )
        self.assertFalse(mock_check.called)
