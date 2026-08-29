"""
Tests for CmdSyncReserves — role guard, plus sync report rendering.

get_role() is imported locally inside func() (not at module level), so
the role guard is patched at its source, evennia_shards.get_role, rather
than on the command module — same pattern as test_cmd_reconcile.py.

evennia test --settings settings tests.command_tests.test_cmd_sync_reserves
"""

from decimal import Decimal
from unittest import TestCase as PlainTestCase
from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_sync_reserves import (
    CmdSyncReserves,
    _on_sync_complete,
    _on_sync_error,
)


@patch("evennia_shards.get_role")
class TestSyncReservesRoleGuard(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_shard_blocked(self, mock_role):
        mock_role.return_value = "shard"
        result = self.call(CmdSyncReserves(), "", caller=self.account)
        self.assertIn("can only be run OOC on the router", result)

    def test_router_allowed(self, mock_role):
        mock_role.return_value = "router"
        with patch(
            "commands.account_cmds.cmd_sync_reserves.defer_to_db_thread"
        ) as mock_defer:
            result = self.call(CmdSyncReserves(), "", caller=self.account)
        self.assertIn("Querying vault on-chain balances", result)
        mock_defer.assert_called_once()

    def test_monolith_allowed(self, mock_role):
        mock_role.return_value = "monolith"
        with patch(
            "commands.account_cmds.cmd_sync_reserves.defer_to_db_thread"
        ) as mock_defer:
            result = self.call(CmdSyncReserves(), "", caller=self.account)
        self.assertIn("Querying vault on-chain balances", result)
        mock_defer.assert_called_once()


def _row(code="FCMGold", old=Decimal("100"), new=Decimal("100"), delta=Decimal("0")):
    return {"currency_code": code, "old_reserve": old, "new_reserve": new, "delta": delta}


class TestOnSyncComplete(PlainTestCase):
    """Direct calls to the module-level callback — no thread/defer plumbing."""

    def test_no_rows_shows_no_currencies(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_sync_complete(caller, [])
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("No currencies found", msgs)

    def test_disconnected_caller_is_noop(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 0
        _on_sync_complete(caller, [_row()])
        caller.msg.assert_not_called()

    def test_zero_delta_shows_no_changes(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_sync_complete(caller, [_row(delta=Decimal("0"))])
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("All reserves already in sync", msgs)

    def test_positive_delta_counts_as_changed(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_sync_complete(caller, [_row(delta=Decimal("10"))])
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("1 currency(s) updated", msgs)

    def test_negative_delta_counts_as_changed(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_sync_complete(caller, [_row(delta=Decimal("-10"))])
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("1 currency(s) updated", msgs)

    def test_mixed_changed_and_unchanged_counts_only_changed(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_sync_complete(
            caller, [_row(code="Gold", delta=Decimal("0")),
                     _row(code="Wheat", delta=Decimal("5"))],
        )
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("1 currency(s) updated", msgs)

    def test_row_shows_currency_code(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_sync_complete(caller, [_row(code="FCMWheat")])
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("FCMWheat", msgs)


class TestOnSyncError(PlainTestCase):

    def test_shows_error_message(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        failure = MagicMock()
        failure.getErrorMessage.return_value = "boom"
        _on_sync_error(caller, failure)
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("Sync Error", msgs)
        self.assertIn("boom", msgs)

    def test_disconnected_caller_is_noop(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 0
        failure = MagicMock()
        _on_sync_error(caller, failure)
        caller.msg.assert_not_called()
