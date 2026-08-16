"""
Tests for CmdBroadcast and utils/broadcast.py — role guard, the
monolith-direct-call branch, and the sharded dispatch-to-every-shard
branch.

get_role()/send_message() are imported locally inside func() (not at
module level), so they're patched at their source, evennia_shards.*.

evennia test --settings settings tests.command_tests.test_cmd_broadcast
"""

from unittest.mock import MagicMock, patch

from django.test import override_settings
from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_broadcast import CmdBroadcast
from utils.broadcast import MESSAGE_KIND, broadcast_to_local_sessions


# ══════════════════════════════════════════════════════════════════════════
#  broadcast_to_local_sessions
# ══════════════════════════════════════════════════════════════════════════

class TestBroadcastToLocalSessions(EvenniaCommandTest):

    def create_script(self):
        pass

    @patch("evennia.server.sessionhandler.SESSION_HANDLER")
    def test_announces_formatted_message(self, mock_handler):
        mock_handler.count.return_value = 5

        broadcast_to_local_sessions("Tim", "server restart in 5")

        mock_handler.announce_all.assert_called_once()
        text = mock_handler.announce_all.call_args[0][0]
        self.assertIn("Tim", text)
        self.assertIn("server restart in 5", text)

    @patch("evennia.server.sessionhandler.SESSION_HANDLER")
    def test_returns_session_count(self, mock_handler):
        mock_handler.count.return_value = 3

        result = broadcast_to_local_sessions("Tim", "hi")

        self.assertEqual(result, 3)


# ══════════════════════════════════════════════════════════════════════════
#  Role guard + argument validation
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role")
class TestBroadcastRoleGuard(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_shard_blocked(self, mock_role):
        mock_role.return_value = "shard"
        result = self.call(CmdBroadcast(), "hello", caller=self.account)
        self.assertIn("can only be run OOC on the router", result)

    def test_no_message_shows_usage(self, mock_role):
        mock_role.return_value = "monolith"
        result = self.call(CmdBroadcast(), "", caller=self.account)
        self.assertIn("Broadcast what?", result)


# ══════════════════════════════════════════════════════════════════════════
#  Monolith — direct local call
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role", return_value="monolith")
class TestBroadcastMonolith(EvenniaCommandTest):

    def create_script(self):
        pass

    @patch("utils.broadcast.broadcast_to_local_sessions")
    def test_calls_local_broadcast_and_reports_count(self, mock_broadcast, _mock_role):
        mock_broadcast.return_value = 4
        result = self.call(CmdBroadcast(), "server restarting", caller=self.account)
        mock_broadcast.assert_called_once_with(self.account.key, "server restarting")
        self.assertIn("Broadcast sent to 4 session(s)", result)


# ══════════════════════════════════════════════════════════════════════════
#  Router — sharded dispatch
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role", return_value="router")
class TestBroadcastSharded(EvenniaCommandTest):

    def create_script(self):
        pass

    @patch("evennia_shards.send_message")
    @override_settings(SHARD_URLS={"shard0": "url0", "shard1": "url1"})
    def test_dispatches_to_every_shard(self, mock_send, _mock_role):
        result = self.call(CmdBroadcast(), "hello everyone", caller=self.account)

        self.assertEqual(mock_send.call_count, 2)
        called_shards = {c.kwargs.get("to_shard") for c in mock_send.call_args_list}
        self.assertEqual(called_shards, {"shard0", "shard1"})
        for c in mock_send.call_args_list:
            self.assertEqual(c.args[0], MESSAGE_KIND)
            self.assertEqual(
                c.args[1], {"caller_name": self.account.key, "message": "hello everyone"},
            )
        self.assertIn("Broadcast dispatched to 2 shard(s)", result)

    @patch("evennia_shards.send_message")
    @override_settings(SHARD_URLS={"shard0": "url0", "shard1": "url1"})
    def test_one_shard_failure_reported_but_others_still_sent(self, mock_send, _mock_role):
        mock_send.side_effect = [Exception("unreachable"), None]
        result = self.call(CmdBroadcast(), "hi", caller=self.account)

        self.assertIn("Failed dispatching to shard0", result)
        self.assertIn("Broadcast dispatched to 1 shard(s)", result)
