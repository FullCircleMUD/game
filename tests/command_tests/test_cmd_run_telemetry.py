"""
Tests for CmdRunTelemetry — role guard, plus the dispatch + success/error
message rendering.

get_role() is imported locally inside func() (not at module level), so
the role guard is patched at its source, evennia_shards.get_role.

The success/error messages are wired via addCallback/addErrback on the
Deferred that threads.deferToThread() returns — a _FakeDeferred stands
in so those inline lambdas actually run during the test instead of only
being asserted as "some callback was registered".

evennia test --settings settings tests.command_tests.test_cmd_run_telemetry
"""

from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_run_telemetry import CmdRunTelemetry


class _FakeDeferred:
    """Runs the registered callback or errback immediately and synchronously."""

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


@patch("evennia_shards.get_role")
class TestRunTelemetryRoleGuard(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_shard_blocked(self, mock_role):
        mock_role.return_value = "shard"
        result = self.call(CmdRunTelemetry(), "", caller=self.account)
        self.assertIn("can only be run OOC on the router", result)

    @patch("commands.account_cmds.cmd_run_telemetry.threads.deferToThread")
    def test_router_allowed_dispatches_snapshot(self, mock_defer, mock_role):
        mock_role.return_value = "router"
        mock_defer.return_value = _FakeDeferred(result=None)

        from blockchain.xrpl.services.telemetry import TelemetryService

        result = self.call(CmdRunTelemetry(), "", caller=self.account)

        mock_defer.assert_called_once_with(TelemetryService.take_snapshot)
        self.assertIn("Taking telemetry snapshot", result)

    @patch("commands.account_cmds.cmd_run_telemetry.threads.deferToThread")
    def test_monolith_allowed_dispatches_snapshot(self, mock_defer, mock_role):
        mock_role.return_value = "monolith"
        mock_defer.return_value = _FakeDeferred(result=None)

        result = self.call(CmdRunTelemetry(), "", caller=self.account)

        mock_defer.assert_called_once()
        self.assertIn("Taking telemetry snapshot", result)


@patch("evennia_shards.get_role", return_value="monolith")
@patch("commands.account_cmds.cmd_run_telemetry.threads.deferToThread")
class TestRunTelemetryOutcomes(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_success_shows_complete_message(self, mock_defer, _mock_role):
        mock_defer.return_value = _FakeDeferred(result=None)
        result = self.call(CmdRunTelemetry(), "", caller=self.account)
        self.assertIn("Telemetry snapshot complete", result)

    def test_failure_shows_error_message(self, mock_defer, _mock_role):
        failure = MagicMock()
        failure.getErrorMessage.return_value = "boom"
        mock_defer.return_value = _FakeDeferred(error=failure)
        result = self.call(CmdRunTelemetry(), "", caller=self.account)
        self.assertIn("Telemetry snapshot failed", result)
        self.assertIn("boom", result)
