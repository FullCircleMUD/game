"""
Tests for CmdRunSaturation — role guard, plus the dispatch + snapshot
count reporting and success/error message rendering.

get_role() is imported locally inside func() (not at module level), so
the role guard is patched at its source, evennia_shards.get_role.

NFTSaturationService.take_snapshot() itself is mocked out — it's
already covered thoroughly by tests/script_tests/test_nft_saturation.py.
These tests are about the command's own logic: dispatch, the
hours/rows count query, and message formatting. threads.deferToThread
is patched with a side effect that actually runs the closure passed to
it (catching exceptions into a fake Failure), so the inline
_run()/_done() functions execute for real instead of being skipped.

evennia test --settings settings tests.command_tests.test_cmd_run_saturation
"""

from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaCommandTest

from blockchain.xrpl.models import SaturationSnapshot
from commands.account_cmds.cmd_run_saturation import CmdRunSaturation

TAKE_SNAPSHOT = "blockchain.xrpl.services.nft_saturation.NFTSaturationService.take_snapshot"


class _FakeDeferred:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error

    def addCallback(self, fn):
        if self._error is None:
            fn(self._result)
        return self

    def addErrback(self, fn):
        if self._error is not None:
            fn(self._error)
        return self


def _sync_defer(fn, *args, **kwargs):
    """Actually runs fn (the command's inner _run closure) synchronously,
    turning any exception into a fake Twisted Failure for the errback."""
    try:
        result = fn(*args, **kwargs)
    except Exception as exc:
        failure = MagicMock()
        failure.getErrorMessage.return_value = str(exc)
        return _FakeDeferred(error=failure)
    return _FakeDeferred(result=result)


def _saturation(hour, item_key="ZZZ Test Spell", category="spell"):
    return SaturationSnapshot.objects.create(
        hour=hour, item_key=item_key, category=category,
        active_players_7d=1, eligible_players=1, known_by=0,
        unlearned_copies=0, in_circulation=0, saturation=0.0,
        spawn_budget=0, spawn_quest_debt=0, spawn_placed=0, spawn_dropped=0,
    )


@patch("commands.account_cmds.cmd_run_saturation.threads.deferToThread",
       side_effect=_sync_defer)
@patch(TAKE_SNAPSHOT)
@patch("evennia_shards.get_role")
class TestRunSaturationRoleGuard(EvenniaCommandTest):
    databases = {"default", "xrpl"}

    def create_script(self):
        pass

    def test_shard_blocked(self, mock_role, mock_snapshot, _mock_defer):
        mock_role.return_value = "shard"
        result = self.call(CmdRunSaturation(), "", caller=self.account)
        self.assertIn("can only be run OOC on the router", result)
        mock_snapshot.assert_not_called()

    def test_router_allowed(self, mock_role, mock_snapshot, _mock_defer):
        mock_role.return_value = "router"
        result = self.call(CmdRunSaturation(), "", caller=self.account)
        self.assertIn("Running saturation snapshot", result)
        mock_snapshot.assert_called_once()

    def test_monolith_allowed(self, mock_role, mock_snapshot, _mock_defer):
        mock_role.return_value = "monolith"
        result = self.call(CmdRunSaturation(), "", caller=self.account)
        self.assertIn("Running saturation snapshot", result)
        mock_snapshot.assert_called_once()


@patch("commands.account_cmds.cmd_run_saturation.threads.deferToThread",
       side_effect=_sync_defer)
@patch(TAKE_SNAPSHOT)
@patch("evennia_shards.get_role", return_value="monolith")
class TestRunSaturationOutcomes(EvenniaCommandTest):
    databases = {"default", "xrpl"}

    def create_script(self):
        pass

    def test_success_shows_complete_and_counts(self, _mock_role, mock_snapshot, _mock_defer):
        from django.utils import timezone

        hour = timezone.now().replace(minute=0, second=0, microsecond=0)
        _saturation(hour, item_key="ZZZ Test A")
        _saturation(hour, item_key="ZZZ Test B")

        result = self.call(CmdRunSaturation(), "", caller=self.account)

        self.assertIn("Saturation snapshot complete", result)
        self.assertIn("2 items tracked across 1 hour(s)", result)

    def test_no_rows_reports_zero(self, _mock_role, mock_snapshot, _mock_defer):
        result = self.call(CmdRunSaturation(), "", caller=self.account)
        self.assertIn("0 items tracked across 0 hour(s)", result)

    def test_failure_shows_error_message(self, _mock_role, mock_snapshot, _mock_defer):
        mock_snapshot.side_effect = RuntimeError("boom")
        result = self.call(CmdRunSaturation(), "", caller=self.account)
        self.assertIn("Saturation snapshot failed", result)
        self.assertIn("boom", result)
