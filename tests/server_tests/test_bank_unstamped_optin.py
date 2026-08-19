"""
Tests that both AccountBank creation paths opt in to the shards guard.

Banks are created on the router, which runs unscoped, so the row lands
``shard_id=NULL`` and the evennia-shards guard refuses the INSERT unless
it is wrapped in ``allow_unstamped_insert()``. Missing the wrapper in
``at_account_creation`` aborts account creation entirely.

The guard is only installed when the role is not monolith, and these
tests run under monolith settings, so they cannot let the guard fire.
They assert the opt-in is active at the moment of the insert instead —
which is what the router needs and what a future edit could silently
remove.

evennia test --settings settings tests.server_tests.test_bank_unstamped_optin
"""

from unittest.mock import PropertyMock, patch

from evennia.utils.test_resources import BaseEvenniaTest
from evennia_shards import unstamped_insert_allowed


class TestAtAccountCreationOptsIn(BaseEvenniaTest):
    """The bank made during account creation must opt in."""

    account_typeclass = "typeclasses.accounts.accounts.Account"
    databases = "__all__"

    def create_script(self):
        pass

    def test_bank_insert_opts_in(self):
        import typeclasses.accounts.accounts as accounts_module

        original = accounts_module.create_object
        seen = {}

        def recorder(*args, **kwargs):
            seen["opt_in"] = unstamped_insert_allowed()
            return original(*args, **kwargs)

        with patch.object(
            type(self.account),
            "is_superuser",
            new_callable=PropertyMock,
            return_value=False,
        ), patch.object(accounts_module, "create_object", recorder):
            self.account.at_account_creation()

        self.assertTrue(
            seen.get("opt_in"),
            "at_account_creation created the bank outside "
            "allow_unstamped_insert() — the router will refuse the INSERT "
            "and account creation will fail.",
        )

    def test_bank_is_created(self):
        with patch.object(
            type(self.account),
            "is_superuser",
            new_callable=PropertyMock,
            return_value=False,
        ):
            self.account.at_account_creation()

        self.assertIsNotNone(self.account.db.bank)


class TestEnsureBankOptsIn(BaseEvenniaTest):
    """The defence-in-depth bank in ensure_bank must opt in too."""

    account_typeclass = "typeclasses.accounts.accounts.Account"

    def create_script(self):
        pass

    def test_bank_insert_opts_in(self):
        import evennia.utils.create as create_module
        from commands.room_specific_cmds.bank.cmd_balance import ensure_bank

        original = create_module.create_object
        seen = {}

        def recorder(*args, **kwargs):
            seen["opt_in"] = unstamped_insert_allowed()
            return original(*args, **kwargs)

        self.account.db.bank = None
        with patch.object(create_module, "create_object", recorder):
            bank = ensure_bank(self.account)

        self.assertIsNotNone(bank)
        self.assertTrue(
            seen.get("opt_in"),
            "ensure_bank created the bank outside allow_unstamped_insert() "
            "— the router will refuse the INSERT.",
        )
