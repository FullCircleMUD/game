"""
Tests for the movement message vocabulary — verb rules, direction phrasing,
and follow-chain resolution. Pure functions only; the seam that uses them is
covered by tests.typeclass_tests.test_movement_seam.

evennia test --settings settings tests.utils_tests.test_movement_messages
"""

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from utils.movement_messages import (
    DEFAULT_RULE,
    FLEE_MESSAGES,
    arrival_phrase,
    follows,
    followers_in,
    resolve_rule,
)


def _mover(position):
    mover = MagicMock()
    mover.room_vertical_position = position
    return mover


def _room(max_depth=0):
    room = MagicMock()
    room.max_depth = max_depth
    return room


class TestVerbRules(SimpleTestCase):
    """Rules describe how the mover is travelling, read from state."""

    def test_walking_is_the_default(self):
        rule = resolve_rule(_mover(0), _room())
        self.assertEqual((rule.departure, rule.arrival), ("leaves", "arrives"))

    def test_above_the_ground_is_flying(self):
        rule = resolve_rule(_mover(2), _room())
        self.assertEqual((rule.departure, rule.arrival), ("flies", "flies in"))

    def test_below_the_surface_is_swimming(self):
        rule = resolve_rule(_mover(-2), _room(max_depth=-3))
        self.assertEqual((rule.departure, rule.arrival), ("swims", "swims in"))

    def test_floating_on_a_room_with_depth_is_swimming(self):
        """Position 0 is the surface where the room has depth."""
        rule = resolve_rule(_mover(0), _room(max_depth=-3))
        self.assertEqual(rule.departure, "swims")

    def test_standing_on_a_room_without_depth_is_walking(self):
        """The same position 0 is dry ground where the room has none."""
        rule = resolve_rule(_mover(0), _room(max_depth=0))
        self.assertEqual(rule.departure, "leaves")

    def test_airborne_over_water_is_flying(self):
        """
        A room having depth does not make its occupants swimmers — the rule
        reads the mover, so someone above the surface of a lake is flying.
        """
        rule = resolve_rule(_mover(1), _room(max_depth=-3))
        self.assertEqual(rule.departure, "flies")

    def test_rules_are_state_only(self):
        """A predicate sees the mover and the room, and nothing else."""
        for rule in (r for r in (DEFAULT_RULE,) if r.matches):
            self.fail("the default rule should carry no predicate")


class TestDirectionPhrasing(SimpleTestCase):
    """The phrase describes where someone came from, given the way back."""

    def test_compass_directions_read_plainly(self):
        self.assertEqual(arrival_phrase("south"), "from the south")
        self.assertEqual(arrival_phrase("northwest"), "from the northwest")

    def test_travelling_up_means_arriving_from_below(self):
        """Went up, so the way back is down, so they came from below."""
        self.assertEqual(arrival_phrase("down"), "from below")

    def test_travelling_down_means_arriving_from_above(self):
        self.assertEqual(arrival_phrase("up"), "from above")


class TestFollowChain(SimpleTestCase):
    """Party membership walks the chain, not just direct followers."""

    def test_direct_follower(self):
        leader, follower = MagicMock(), MagicMock()
        follower.following = leader
        self.assertTrue(follows(follower, leader))

    def test_indirect_follower(self):
        leader, middle, tail = MagicMock(), MagicMock(), MagicMock()
        middle.following = leader
        tail.following = middle
        self.assertTrue(follows(tail, leader))

    def test_unrelated_actor(self):
        leader, other = MagicMock(), MagicMock()
        other.following = None
        self.assertFalse(follows(other, leader))

    def test_cycle_terminates(self):
        """A follow loop must not spin."""
        a, b, leader = MagicMock(), MagicMock(), MagicMock()
        a.following = b
        b.following = a
        self.assertFalse(follows(a, leader))

    def test_followers_in_room_excludes_the_leader(self):
        leader, follower = MagicMock(), MagicMock()
        follower.following = leader
        leader.following = None
        room = MagicMock()
        room.contents = [leader, follower]
        self.assertEqual(followers_in(leader, room), [follower])

    def test_followers_in_room_ignores_those_elsewhere(self):
        """Only what is standing in the room passed in counts."""
        leader, follower = MagicMock(), MagicMock()
        follower.following = leader
        room = MagicMock()
        room.contents = [leader]
        self.assertEqual(followers_in(leader, room), [])

    def test_no_room_means_no_party(self):
        self.assertEqual(followers_in(MagicMock(), None), [])


class TestSharedWording(SimpleTestCase):
    """Wording shared by several callers is defined once."""

    def test_flee_templates_are_templates(self):
        """Never pre-rendered — {name} has to resolve per recipient."""
        for template in FLEE_MESSAGES.values():
            self.assertIn("{name}", template)
            self.assertIn("{direction}", template)
