"""
Tests for CmdAccounts — process-label header (get_role()/get_shard_id()
branching) plus the account listing itself.

get_role()/get_shard_id() are imported locally inside func() (not at
module level), so they're patched at their source, evennia_shards.*.

Relies on Evennia's idmapper: AccountDB.objects.all() inside func()
returns the SAME cached instance as an account object created directly
in the test (same pk), so patching that instance's .sessions.count()
before calling the command is visible to the command's own query.

evennia test --settings settings tests.command_tests.test_cmd_accounts
"""

from unittest.mock import patch

from evennia.accounts.models import AccountDB
from evennia.utils.create import create_account
from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_accounts import CmdAccounts


@patch("evennia_shards.get_role")
class TestAccountsProcessLabel(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_monolith_label(self, mock_role):
        mock_role.return_value = "monolith"
        result = self.call(CmdAccounts(), "", caller=self.account)
        self.assertIn("connected to this process: monolith", result)

    def test_router_label(self, mock_role):
        mock_role.return_value = "router"
        result = self.call(CmdAccounts(), "", caller=self.account)
        self.assertIn("connected to this process: router", result)

    @patch("evennia_shards.get_shard_id")
    def test_shard_label_uses_shard_id(self, mock_shard_id, mock_role):
        mock_role.return_value = "shard"
        mock_shard_id.return_value = "shard0"
        result = self.call(CmdAccounts(), "", caller=self.account)
        self.assertIn("connected to this process: shard0", result)

    @patch("evennia_shards.get_shard_id")
    def test_shard_label_falls_back_to_role_when_no_shard_id(self, mock_shard_id, mock_role):
        mock_role.return_value = "shard"
        mock_shard_id.return_value = None
        result = self.call(CmdAccounts(), "", caller=self.account)
        self.assertIn("connected to this process: shard", result)


@patch("evennia_shards.get_role", return_value="monolith")
class TestAccountsListing(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_shows_username_and_id(self, _mock_role):
        result = self.call(CmdAccounts(), "", caller=self.account)
        self.assertIn(self.account.username, result)
        self.assertIn(f"#{self.account.id}", result)

    def test_no_login_shows_never(self, _mock_role):
        acct = create_account("test_never_login", email=None, password="TestPassword123!")
        acct.last_login = None
        acct.save()
        try:
            result = self.call(CmdAccounts(), "", caller=self.account)
            self.assertIn("Last login: Never", result)
        finally:
            acct.delete()

    def test_online_marker_shown_when_session_connected(self, _mock_role):
        """self.call() renders through the msg pipeline, which strips
        color markup — so the visible signal is the '*' glyph itself,
        not the literal |g...|n wrapper around it."""
        acct = create_account("test_online", email=None, password="TestPassword123!")
        try:
            with patch.object(acct.sessions, "count", return_value=1):
                result = self.call(CmdAccounts(), "", caller=self.account)
            lines = [l for l in result.split("\n") if "test_online" in l]
            self.assertTrue(lines)
            self.assertTrue(lines[0].strip().startswith("*"))
        finally:
            acct.delete()

    def test_no_online_marker_when_no_session(self, _mock_role):
        acct = create_account("test_offline", email=None, password="TestPassword123!")
        try:
            with patch.object(acct.sessions, "count", return_value=0):
                result = self.call(CmdAccounts(), "", caller=self.account)
            lines = [l for l in result.split("\n") if "test_offline" in l]
            self.assertTrue(lines)
            self.assertFalse(lines[0].strip().startswith("*"))
        finally:
            acct.delete()

    def test_characters_column_lists_playable_characters(self, _mock_role):
        """Uses a real Character (self.char1) — a MagicMock isn't picklable
        into the account's _playable_characters Attribute."""
        acct = create_account("test_haschars", email=None, password="TestPassword123!")
        acct.db._playable_characters = [self.char1]
        try:
            result = self.call(CmdAccounts(), "", caller=self.account)
            lines = [l for l in result.split("\n") if "test_haschars" in l]
            self.assertTrue(lines)
            self.assertIn(self.char1.key, lines[0])
        finally:
            acct.delete()

    def test_characters_column_shows_dash_when_none(self, _mock_role):
        acct = create_account("test_nochars", email=None, password="TestPassword123!")
        try:
            result = self.call(CmdAccounts(), "", caller=self.account)
            lines = [l for l in result.split("\n") if "test_nochars" in l]
            self.assertTrue(lines)
            self.assertIn("Chars: -", lines[0])
        finally:
            acct.delete()

    def test_total_count_shown(self, _mock_role):
        result = self.call(CmdAccounts(), "", caller=self.account)
        expected_total = AccountDB.objects.all().count()
        self.assertIn(f"Total: {expected_total} accounts", result)

    def test_no_accounts_shows_message(self, _mock_role):
        with patch.object(
            AccountDB.objects, "all", return_value=AccountDB.objects.none(),
        ):
            result = self.call(CmdAccounts(), "", caller=self.account)
        self.assertIn("No accounts found", result)
