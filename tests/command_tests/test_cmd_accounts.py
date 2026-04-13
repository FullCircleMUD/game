"""
Tests for the accounts command (superuser-only account list).

evennia test --settings settings tests.command_tests.test_cmd_accounts
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.accounts.models import AccountDB

from commands.account_cmds.cmd_accounts import CmdAccounts


class TestCmdAccounts(EvenniaCommandTest):
    """Test the superuser accounts listing command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_lists_accounts(self):
        """Command returns output containing account names."""
        result = self.call(CmdAccounts(), "")
        self.assertIn("All Accounts", result)
        self.assertIn("Total:", result)

    def test_shows_account_name(self):
        """Output includes the calling account's username."""
        result = self.call(CmdAccounts(), "")
        self.assertIn(self.account.username, result)

    def test_shows_last_login(self):
        """Output includes last login or 'Never'."""
        result = self.call(CmdAccounts(), "")
        # Account should show either a date or "Never"
        has_date = any(c.isdigit() for c in result)
        has_never = "Never" in result
        self.assertTrue(has_date or has_never)

    def test_shows_total_count(self):
        """Output includes a total count of accounts."""
        result = self.call(CmdAccounts(), "")
        count = AccountDB.objects.count()
        self.assertIn(str(count), result)
