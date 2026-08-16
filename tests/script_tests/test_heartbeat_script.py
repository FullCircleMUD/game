"""
Tests for HeartbeatMixin.

Covers:
    - record_repeat() / record_work() set only their own field
    - record_heartbeat() sets both together
    - values are real, timezone-aware timestamps

evennia test --settings settings tests.script_tests.test_heartbeat_script
"""

from types import SimpleNamespace
from unittest import TestCase

from django.utils import timezone

from typeclasses.scripts.heartbeat_script import HeartbeatMixin


class _FakeScript(HeartbeatMixin):
    """Minimal stand-in for a Script — just needs a settable ndb."""

    def __init__(self):
        self.ndb = SimpleNamespace()


class TestHeartbeatMixin(TestCase):

    def test_record_repeat_sets_last_repeat_only(self):
        script = _FakeScript()
        script.record_repeat()

        self.assertIsNotNone(script.ndb.last_repeat)
        self.assertFalse(hasattr(script.ndb, "last_work"))

    def test_record_work_sets_last_work_only(self):
        script = _FakeScript()
        script.record_work()

        self.assertIsNotNone(script.ndb.last_work)
        self.assertFalse(hasattr(script.ndb, "last_repeat"))

    def test_record_heartbeat_sets_both(self):
        script = _FakeScript()
        script.record_heartbeat()

        self.assertIsNotNone(script.ndb.last_repeat)
        self.assertIsNotNone(script.ndb.last_work)

    def test_record_heartbeat_stamps_are_equal(self):
        """Both fields come from the same now() call, not two separate ones."""
        script = _FakeScript()
        script.record_heartbeat()

        self.assertEqual(script.ndb.last_repeat, script.ndb.last_work)

    def test_timestamps_are_timezone_aware_and_recent(self):
        script = _FakeScript()
        before = timezone.now()
        script.record_repeat()
        after = timezone.now()

        self.assertIsNotNone(script.ndb.last_repeat.tzinfo)
        self.assertGreaterEqual(script.ndb.last_repeat, before)
        self.assertLessEqual(script.ndb.last_repeat, after)

    def test_record_work_does_not_clobber_existing_last_repeat(self):
        """Matches the pipeline-script shape: record_repeat() every tick,
        record_work() only inside the gate — one must not reset the other."""
        script = _FakeScript()
        script.record_repeat()
        first_repeat = script.ndb.last_repeat

        script.record_work()

        self.assertEqual(script.ndb.last_repeat, first_repeat)
        self.assertIsNotNone(script.ndb.last_work)
