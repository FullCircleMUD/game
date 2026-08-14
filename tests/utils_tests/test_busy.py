"""
Tests for the busy lock — actions that take time and take both hands.

The wait is the whole mechanism, so what matters is that the lock is
held for the duration, released afterwards, and that nothing about the
outcome escapes before the action finishes.

evennia test --settings settings tests.utils_tests.test_busy
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from utils.busy import (
    BUSY_MESSAGE,
    FUMBLE_SECONDS_MAX,
    FUMBLE_SECONDS_MIN,
    check_busy,
    fumble_seconds,
    start_busy,
)


class BusyTest(EvenniaTest):
    """A character being made busy, with the reactor delay under control."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.ran = []
        self.said = []
        self.char1.msg = lambda text, **kwargs: self.said.append(text)

    def _act(self):
        self.ran.append("acted")

    def _start(self, **kwargs):
        """
        Start a busy action, returning a callable that fires its deferred
        completion. ``delay`` is called as ``delay(interval, _tick, step)``,
        so the captured callback is bound to the step it was scheduled with.
        """
        with patch("utils.busy.delay") as mock_delay:
            self.started = start_busy(self.char1, 3, self._act, **kwargs)
        if not mock_delay.call_args:
            return None
        args = mock_delay.call_args[0]
        return lambda: args[1](*args[2:])


class TestCheckBusy(BusyTest):

    def test_a_free_character_is_not_busy(self):
        self.assertFalse(check_busy(self.char1))

    def test_an_occupied_character_is_busy(self):
        self.char1.ndb.is_processing = True
        self.assertTrue(check_busy(self.char1))

    def test_a_busy_character_is_told_why(self):
        self.char1.ndb.is_processing = True
        check_busy(self.char1)
        self.assertIn(BUSY_MESSAGE, self.said)

    def test_a_free_character_is_told_nothing(self):
        check_busy(self.char1)
        self.assertEqual(self.said, [])


class TestTheLock(BusyTest):

    def test_the_lock_is_held_for_the_duration(self):
        self._start()
        self.assertTrue(self.char1.ndb.is_processing)

    def test_the_lock_is_released_when_the_action_finishes(self):
        complete = self._start()
        complete()
        self.assertFalse(self.char1.ndb.is_processing)

    def test_a_busy_character_cannot_start_another_action(self):
        self.char1.ndb.is_processing = True
        complete = self._start()
        self.assertFalse(self.started)
        self.assertIsNone(complete)

    def test_a_refused_start_does_not_disturb_the_running_action(self):
        self.char1.ndb.is_processing = True
        self._start()
        self.assertTrue(self.char1.ndb.is_processing)

    def test_the_lock_is_clear_before_the_outcome_runs(self):
        """An outcome that starts its own action must not self-block."""
        seen = []
        with patch("utils.busy.delay") as mock_delay:
            start_busy(
                self.char1,
                3,
                lambda: seen.append(self.char1.ndb.is_processing),
            )
        args = mock_delay.call_args[0]
        args[1](*args[2:])
        self.assertEqual(seen, [False])


class TestTheOutcome(BusyTest):

    def test_the_outcome_does_not_run_before_the_delay(self):
        self._start()
        self.assertEqual(self.ran, [])

    def test_the_outcome_runs_after_the_delay(self):
        complete = self._start()
        complete()
        self.assertEqual(self.ran, ["acted"])

    def test_the_duration_is_passed_through(self):
        with patch("utils.busy.delay") as mock_delay:
            start_busy(self.char1, 7.5, self._act)
        self.assertEqual(mock_delay.call_args[0][0], 7.5)


class TestTheAnnouncement(BusyTest):

    def test_the_actor_is_told_up_front(self):
        self._start(self_msg="You begin gathering...")
        self.assertIn("You begin gathering...", self.said)

    def test_the_room_is_told_up_front(self):
        with patch.object(self.char1.location, "msg_contents") as mock_room:
            self._start(room_msg="Char begins gathering.")
        self.assertEqual(mock_room.call_args[0][0], "Char begins gathering.")

    def test_the_room_message_excludes_the_actor(self):
        with patch.object(self.char1.location, "msg_contents") as mock_room:
            self._start(room_msg="Char begins gathering.")
        self.assertEqual(mock_room.call_args[1]["exclude"], [self.char1])

    def test_the_room_message_carries_from_obj_for_filtering(self):
        """Without from_obj the broadcast bypasses perception filtering."""
        with patch.object(self.char1.location, "msg_contents") as mock_room:
            self._start(room_msg="Char begins gathering.")
        self.assertEqual(mock_room.call_args[1]["from_obj"], self.char1)

    def test_a_silent_action_announces_nothing(self):
        with patch.object(self.char1.location, "msg_contents") as mock_room:
            self._start()
        self.assertEqual(self.said, [])
        mock_room.assert_not_called()


class TestFumbleSeconds(BusyTest):

    def test_the_search_takes_three_to_four_seconds(self):
        for _ in range(20):
            seconds = fumble_seconds()
            self.assertGreaterEqual(seconds, FUMBLE_SECONDS_MIN)
            self.assertLessEqual(seconds, FUMBLE_SECONDS_MAX)
