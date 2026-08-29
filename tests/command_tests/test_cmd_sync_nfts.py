"""
Tests for CmdSyncNfts — role guard, plus the sync report rendering,
including the async-dispatch branch (objects_patched is None vs int).

get_role() is imported locally inside func() (not at module level), so
the role guard is patched at its source, evennia_shards.get_role.

evennia test --settings settings tests.command_tests.test_cmd_sync_nfts
"""

from unittest import TestCase as PlainTestCase
from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_sync_nfts import (
    CmdSyncNfts,
    _on_sync_complete,
    _on_sync_error,
)


@patch("evennia_shards.get_role")
class TestSyncNftsRoleGuard(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_shard_blocked(self, mock_role):
        mock_role.return_value = "shard"
        result = self.call(CmdSyncNfts(), "", caller=self.account)
        self.assertIn("can only be run OOC on the router", result)

    def test_router_allowed(self, mock_role):
        mock_role.return_value = "router"
        with patch(
            "commands.account_cmds.cmd_sync_nfts.defer_to_db_thread"
        ) as mock_defer:
            result = self.call(CmdSyncNfts(), "", caller=self.account)
        self.assertIn("Querying vault wallet on-chain", result)
        mock_defer.assert_called_once()

    def test_monolith_allowed(self, mock_role):
        mock_role.return_value = "monolith"
        with patch(
            "commands.account_cmds.cmd_sync_nfts.defer_to_db_thread"
        ) as mock_defer:
            result = self.call(CmdSyncNfts(), "", caller=self.account)
        self.assertIn("Querying vault wallet on-chain", result)
        mock_defer.assert_called_once()


def _result(on_chain_count=0, updated=0, created=0, unchanged=0, skipped=0,
            objects_patched=0):
    return {
        "on_chain_count": on_chain_count, "updated": updated, "created": created,
        "unchanged": unchanged, "skipped": skipped, "objects_patched": objects_patched,
    }


class TestOnSyncComplete(PlainTestCase):
    """Direct calls to the module-level callback — no thread/defer plumbing."""

    def test_disconnected_caller_is_noop(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 0
        _on_sync_complete(caller, _result())
        caller.msg.assert_not_called()

    def test_shows_counts(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_sync_complete(
            caller, _result(on_chain_count=10, updated=2, created=3, unchanged=5)
        )
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("10", msgs)
        self.assertIn("Updated (placeholder", msgs)
        self.assertIn("2", msgs)
        self.assertIn("Created (new to DB): 3", msgs)
        self.assertIn("Unchanged (already synced): 5", msgs)

    def test_skipped_shown_only_when_nonzero(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_sync_complete(caller, _result(skipped=0))
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertNotIn("Skipped", msgs)

    def test_skipped_shown_when_present(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_sync_complete(caller, _result(skipped=4))
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("Skipped (no game ID in URI):", msgs)
        self.assertIn("4", msgs)

    def test_objects_patched_none_shows_async_dispatch_message(self):
        """Sharded mode: dispatch_patch_sweep() returns None (async, no count)."""
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        result = _result()
        result["objects_patched"] = None
        _on_sync_complete(caller, result)
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("dispatched to all shards", msgs)
        self.assertNotIn("Evennia objects patched:", msgs)

    def test_objects_patched_positive_int_shows_count(self):
        """Monolith mode: dispatch_patch_sweep() returns a real synchronous count."""
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_sync_complete(caller, _result(objects_patched=6))
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("Evennia objects patched:", msgs)
        self.assertIn("6", msgs)
        self.assertNotIn("dispatched to all shards", msgs)

    def test_objects_patched_zero_shows_neither_message(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_sync_complete(caller, _result(objects_patched=0))
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertNotIn("dispatched to all shards", msgs)
        self.assertNotIn("Evennia objects patched:", msgs)

    def test_shows_complete_footer(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_sync_complete(caller, _result())
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("Sync Complete", msgs)


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
