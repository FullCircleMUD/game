"""
Tests for the actual stop -> delete -> recreate sequence behind
`services reset <name>` — _get_script(), _is_running(), _stop_and_delete(),
and _reset_one() in cmd_services.py.

test_cmd_services.py covers name resolution, role gating, and that
_do_reset_targeted() is invoked with the right key, but mocks
_do_reset_targeted() itself — this file drives the real worker functions
against a real (non-persistent) global script, closing that gap.

evennia test --settings settings tests.command_tests.test_cmd_services_reset_worker
"""

from evennia import create_script
from evennia.utils.test_resources import EvenniaTest

from commands.account_cmds.cmd_services import (
    _get_script,
    _is_running,
    _reset_one,
    _stop_and_delete,
)

TEST_KEY = "test_reset_worker_script"
TEST_TYPECLASS = "evennia.DefaultScript"


def _make_test_script(interval=60):
    return create_script(
        TEST_TYPECLASS, key=TEST_KEY, obj=None,
        interval=interval, persistent=False,
    )


class TestResetWorker(EvenniaTest):

    def create_script(self):
        pass

    def tearDown(self):
        script = _get_script(TEST_KEY)
        if script:
            script.stop()
            script.delete()
        super().tearDown()

    # ── _get_script ─────────────────────────────────────────────────

    def test_get_script_finds_existing(self):
        _make_test_script()
        self.assertIsNotNone(_get_script(TEST_KEY))

    def test_get_script_missing_returns_none(self):
        self.assertIsNone(_get_script("definitely_does_not_exist_xyz"))

    # ── _is_running ─────────────────────────────────────────────────

    def test_is_running_false_when_script_is_none(self):
        self.assertFalse(_is_running(None))

    def test_is_running_true_for_live_ticker(self):
        script = _make_test_script(interval=60)
        self.assertTrue(_is_running(script))

    def test_is_running_false_after_stop(self):
        script = _make_test_script(interval=60)
        script.stop()
        self.assertFalse(_is_running(script))

    # ── _stop_and_delete ────────────────────────────────────────────

    def test_stop_and_delete_removes_the_script(self):
        _make_test_script()
        result = _stop_and_delete(TEST_KEY)
        self.assertTrue(result)
        self.assertIsNone(_get_script(TEST_KEY))

    def test_stop_and_delete_missing_script_returns_false(self):
        result = _stop_and_delete("definitely_does_not_exist_xyz")
        self.assertFalse(result)

    # ── _reset_one ──────────────────────────────────────────────────

    def test_reset_one_replaces_existing_script_with_a_new_row(self):
        old = _make_test_script()
        old_id = old.id

        _reset_one(TEST_KEY, TEST_TYPECLASS)

        new = _get_script(TEST_KEY)
        self.assertIsNotNone(new)
        self.assertNotEqual(new.id, old_id)

    def test_reset_one_creates_script_when_missing(self):
        self.assertIsNone(_get_script(TEST_KEY))

        _reset_one(TEST_KEY, TEST_TYPECLASS)

        self.assertIsNotNone(_get_script(TEST_KEY))
