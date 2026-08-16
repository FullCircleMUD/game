"""
Tests for CmdReconcile — role guard, plus reconciliation report rendering.

get_role() is imported locally inside func() (not at module level), so
the role guard is patched at its source, evennia_shards.get_role, rather
than on the command module.

evennia test --settings settings tests.command_tests.test_cmd_reconcile
"""

from decimal import Decimal
from unittest import TestCase as PlainTestCase
from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_reconcile import (
    CmdReconcile,
    _on_reconcile_complete,
    _on_reconcile_error,
)


@patch("evennia_shards.get_role")
class TestReconcileRoleGuard(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_shard_blocked(self, mock_role):
        mock_role.return_value = "shard"
        result = self.call(CmdReconcile(), "", caller=self.account)
        self.assertIn("can only be run OOC on the router", result)

    def test_router_allowed(self, mock_role):
        mock_role.return_value = "router"
        with patch(
            "commands.account_cmds.cmd_reconcile.threads.deferToThread"
        ) as mock_defer:
            result = self.call(CmdReconcile(), "", caller=self.account)
        self.assertIn("Querying vault on-chain balances", result)
        mock_defer.assert_called_once()

    def test_monolith_allowed(self, mock_role):
        mock_role.return_value = "monolith"
        with patch(
            "commands.account_cmds.cmd_reconcile.threads.deferToThread"
        ) as mock_defer:
            result = self.call(CmdReconcile(), "", caller=self.account)
        self.assertIn("Querying vault on-chain balances", result)
        mock_defer.assert_called_once()


def _row(code="FCMGold", name="Gold", on_chain=Decimal("100"),
         reserve=Decimal("100"), distributed=Decimal("0"),
         sink=Decimal("0"), delta=Decimal("0")):
    return {
        "currency_code": code, "name": name, "on_chain": on_chain,
        "game_reserve": reserve, "game_distributed": distributed,
        "game_sink": sink, "delta": delta,
    }


class TestOnReconcileComplete(PlainTestCase):
    """Direct calls to the module-level callback — no thread/defer plumbing."""

    def test_no_rows_shows_no_currencies(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_reconcile_complete(caller, [])
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("No currencies found", msgs)

    def test_disconnected_caller_is_noop(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 0
        _on_reconcile_complete(caller, [_row()])
        caller.msg.assert_not_called()

    def test_zero_delta_shows_all_ok(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_reconcile_complete(caller, [_row(delta=Decimal("0"))])
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("All currencies OK", msgs)
        self.assertNotIn("investigate", msgs)

    def test_negative_delta_shows_warning(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_reconcile_complete(caller, [_row(delta=Decimal("-5"))])
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("1 currency(s) show negative delta", msgs)
        self.assertNotIn("All currencies OK", msgs)

    def test_positive_delta_does_not_warn(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_reconcile_complete(caller, [_row(delta=Decimal("5"))])
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("All currencies OK", msgs)

    def test_row_shows_currency_name(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_reconcile_complete(caller, [_row(name="Wheat")])
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("Wheat", msgs)

    def test_mixed_positive_and_negative_counts_only_negative(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_reconcile_complete(
            caller, [_row(name="Gold", delta=Decimal("5")),
                     _row(name="Wheat", delta=Decimal("-3"))],
        )
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("1 currency(s) show negative delta", msgs)


class TestOnReconcileError(PlainTestCase):

    def test_shows_error_message(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        failure = MagicMock()
        failure.getErrorMessage.return_value = "boom"
        _on_reconcile_error(caller, failure)
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("Reconciliation Error", msgs)
        self.assertIn("boom", msgs)

    def test_disconnected_caller_is_noop(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 0
        failure = MagicMock()
        _on_reconcile_error(caller, failure)
        caller.msg.assert_not_called()
