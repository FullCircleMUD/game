"""
Tests for the failures command — the manual-reconciliation exceptions list.

evennia test --settings settings tests.command_tests.test_cmd_failures
"""

from evennia.utils.test_resources import EvenniaCommandTest

from blockchain.xrpl.models import ReconciliationFailure
from commands.account_cmds.cmd_failures import CmdFailures


def _make_failure(**overrides):
    fields = {
        "operation": "deposit_gold_from_chain",
        "wallet_address": "rTestWallet123",
        "character_key": "TestChar",
        "currency_code": "FCMGold",
        "amount": 20,
        "tx_hash": "TXHASH1",
        "error": "xrpl write failed",
    }
    fields.update(overrides)
    return ReconciliationFailure.objects.create(**fields)


class TestCmdFailures(EvenniaCommandTest):
    """Test listing, showing and resolving reconciliation failures."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_nothing_outstanding(self):
        """An empty list says so rather than printing an empty table."""
        self.call(CmdFailures(), "", "Nothing outstanding")

    def test_lists_unresolved(self):
        """An open failure appears with its operation and character."""
        _make_failure()
        result = self.call(CmdFailures(), "")
        self.assertIn("deposit_gold_from_chain", result)
        self.assertIn("TestChar", result)

    def test_resolved_hidden_by_default(self):
        """A resolved failure drops off the list."""
        _make_failure(resolved=True)
        self.call(CmdFailures(), "", "Nothing outstanding")

    def test_all_includes_resolved(self):
        """'failures all' shows them again."""
        _make_failure(resolved=True)
        result = self.call(CmdFailures(), "all")
        self.assertIn("deposit_gold_from_chain", result)

    def test_show_one_includes_error(self):
        """Detail view carries the error text and the tx hash."""
        row = _make_failure()
        result = self.call(CmdFailures(), str(row.id))
        self.assertIn("xrpl write failed", result)
        self.assertIn("TXHASH1", result)

    def test_show_unknown_id(self):
        """An id that isn't there says so."""
        self.call(CmdFailures(), "999", "No failure with id 999")

    def test_resolve_marks_and_notes(self):
        """Resolving records what was done."""
        row = _make_failure()
        result = self.call(
            CmdFailures(), f"done {row.id} = credited 20 gold by hand",
        )
        self.assertIn("marked resolved", result)
        row.refresh_from_db()
        self.assertTrue(row.resolved)
        self.assertEqual(row.resolved_note, "credited 20 gold by hand")

    def test_resolve_requires_a_note(self):
        """A bare id is refused — the note is the point."""
        row = _make_failure()
        self.call(CmdFailures(), f"done {row.id}", "Usage: failures done")
        row.refresh_from_db()
        self.assertFalse(row.resolved)

    def test_resolve_requires_a_non_empty_note(self):
        """An empty note is refused too."""
        row = _make_failure()
        result = self.call(CmdFailures(), f"done {row.id} = ")
        self.assertIn("the note is the point", result)
        row.refresh_from_db()
        self.assertFalse(row.resolved)
