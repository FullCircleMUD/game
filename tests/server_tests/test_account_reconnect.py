"""
Tests for reconnect-to-state behavior — auto-resume IC on linkdead / server
restart reconnect, while fresh connects and graceful logouts land at the OOC
menu.

evennia test --settings settings tests.server_tests.test_account_reconnect
"""

from unittest.mock import patch, MagicMock, PropertyMock

from evennia.utils.test_resources import BaseEvenniaTest


class TestReconnectPuppet(BaseEvenniaTest):
    account_typeclass = "typeclasses.accounts.accounts.Account"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def _patch_characters(self, chars):
        return patch.object(
            type(self.account), "characters",
            new_callable=PropertyMock, return_value=list(chars),
        )

    def test_graceful_logout_flag_is_consumed_without_puppet(self):
        """graceful_logout=True -> clear flag, do NOT auto-puppet."""
        self.account.db.graceful_logout = True
        self.account.db.active_puppet_id = self.char1.id
        session = MagicMock()

        with patch.object(type(self.account), "is_superuser",
                          new_callable=PropertyMock, return_value=False), \
             patch.object(self.account, "puppet_object") as mock_puppet:
            self.account._try_reconnect_puppet(session)

        self.assertFalse(self.account.db.graceful_logout)
        mock_puppet.assert_not_called()
        # active_puppet_id is preserved across a graceful logout;
        # it gets cleared by mark_graceful_logout() at exit time,
        # but this test exercises _try_reconnect_puppet in isolation.

    def test_valid_active_puppet_auto_resumes(self):
        """Flag absent + valid active_puppet_id -> puppet_object called."""
        self.account.attributes.remove("graceful_logout")
        self.account.db.active_puppet_id = self.char1.id
        session = MagicMock()

        with patch.object(type(self.account), "is_superuser",
                          new_callable=PropertyMock, return_value=False), \
             self._patch_characters([self.char1]), \
             patch("subscriptions.utils.is_subscribed", return_value=True), \
             patch.object(self.account, "puppet_object") as mock_puppet, \
             patch.object(self.char1, "execute_cmd") as mock_cmd:
            self.account._try_reconnect_puppet(session)

        mock_puppet.assert_called_once_with(session, self.char1)
        mock_cmd.assert_called_once_with("look")

    def test_expired_subscription_blocks_auto_resume(self):
        """Expired subscription -> no puppet, active_puppet_id cleared."""
        self.account.attributes.remove("graceful_logout")
        self.account.db.active_puppet_id = self.char1.id
        session = MagicMock()

        with patch.object(type(self.account), "is_superuser",
                          new_callable=PropertyMock, return_value=False), \
             self._patch_characters([self.char1]), \
             patch("subscriptions.utils.is_subscribed", return_value=False), \
             patch.object(self.account, "puppet_object") as mock_puppet:
            self.account._try_reconnect_puppet(session)

        mock_puppet.assert_not_called()
        self.assertIsNone(self.account.db.active_puppet_id)

    def test_stale_puppet_id_clears_and_no_resume(self):
        """active_puppet_id pointing to a non-existent char -> cleared, no puppet."""
        self.account.attributes.remove("graceful_logout")
        self.account.db.active_puppet_id = 999999  # non-existent
        session = MagicMock()

        with patch.object(type(self.account), "is_superuser",
                          new_callable=PropertyMock, return_value=False), \
             patch.object(self.account, "puppet_object") as mock_puppet:
            self.account._try_reconnect_puppet(session)

        mock_puppet.assert_not_called()
        self.assertIsNone(self.account.db.active_puppet_id)

    def test_unowned_character_clears_and_no_resume(self):
        """active_puppet_id pointing to a char not in self.characters -> cleared."""
        self.account.attributes.remove("graceful_logout")
        self.account.db.active_puppet_id = self.char1.id
        session = MagicMock()

        with patch.object(type(self.account), "is_superuser",
                          new_callable=PropertyMock, return_value=False), \
             self._patch_characters([]), \
             patch.object(self.account, "puppet_object") as mock_puppet:
            self.account._try_reconnect_puppet(session)

        mock_puppet.assert_not_called()
        self.assertIsNone(self.account.db.active_puppet_id)

    def test_no_active_puppet_id_no_resume(self):
        """No recorded puppet -> fall through quietly (fresh connect case)."""
        self.account.attributes.remove("graceful_logout")
        self.account.attributes.remove("active_puppet_id")
        session = MagicMock()

        with patch.object(type(self.account), "is_superuser",
                          new_callable=PropertyMock, return_value=False), \
             patch.object(self.account, "puppet_object") as mock_puppet:
            self.account._try_reconnect_puppet(session)

        mock_puppet.assert_not_called()

    def test_superuser_never_auto_resumes(self):
        """Superuser always lands at OOC admin menu."""
        self.account.attributes.remove("graceful_logout")
        self.account.db.active_puppet_id = self.char1.id
        session = MagicMock()

        with patch.object(type(self.account), "is_superuser",
                          new_callable=PropertyMock, return_value=True), \
             patch.object(self.account, "puppet_object") as mock_puppet:
            self.account._try_reconnect_puppet(session)

        mock_puppet.assert_not_called()

    def test_puppet_object_runtimeerror_falls_back(self):
        """If puppet_object raises, clear the pointer and message the player."""
        self.account.attributes.remove("graceful_logout")
        self.account.db.active_puppet_id = self.char1.id
        session = MagicMock()

        with patch.object(type(self.account), "is_superuser",
                          new_callable=PropertyMock, return_value=False), \
             self._patch_characters([self.char1]), \
             patch("subscriptions.utils.is_subscribed", return_value=True), \
             patch.object(self.account, "puppet_object",
                          side_effect=RuntimeError("boom")):
            self.account._try_reconnect_puppet(session)

        self.assertIsNone(self.account.db.active_puppet_id)

    def test_none_session_is_noop(self):
        """Called without a session (shouldn't happen in prod) -> safe no-op."""
        self.account.db.active_puppet_id = self.char1.id

        with patch.object(self.account, "puppet_object") as mock_puppet:
            self.account._try_reconnect_puppet(None)

        mock_puppet.assert_not_called()


class TestMarkGracefulLogout(BaseEvenniaTest):
    account_typeclass = "typeclasses.accounts.accounts.Account"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def test_mark_graceful_logout_sets_flag_and_clears_id(self):
        self.account.db.active_puppet_id = self.char1.id
        self.account.attributes.remove("graceful_logout")

        self.account.mark_graceful_logout()

        self.assertTrue(self.account.db.graceful_logout)
        self.assertIsNone(self.account.db.active_puppet_id)


class TestSourceWiring(BaseEvenniaTest):
    """Source-level checks that the reconnect wiring is in place.

    End-to-end puppet flow is exercised in manual verification; here we
    just confirm the hooks/commands contain the required calls so the
    glue doesn't silently rot.
    """

    def create_script(self):
        pass

    def test_character_at_post_puppet_records_active_puppet_id(self):
        import inspect
        from typeclasses.actors.character import FCMCharacter
        source = inspect.getsource(FCMCharacter.at_post_puppet)
        self.assertIn("active_puppet_id", source)
        self.assertIn("graceful_logout", source)

    def test_cmd_quit_marks_graceful_logout(self):
        import inspect
        from commands.all_char_cmds.cmd_quit_ic import CmdQuitIC
        source = inspect.getsource(CmdQuitIC.func)
        self.assertIn("mark_graceful_logout", source)

    def test_cmd_rent_marks_graceful_logout(self):
        import inspect
        from commands.room_specific_cmds.inn.cmd_rent import CmdRent
        source = inspect.getsource(CmdRent.func)
        self.assertIn("mark_graceful_logout", source)

    def test_cmd_ooc_marks_graceful_logout(self):
        import inspect
        from commands.account_cmds.cmd_override_ooc import CmdOOC
        source = inspect.getsource(CmdOOC.func)
        self.assertIn("mark_graceful_logout", source)

    def test_chardelete_clears_active_puppet_id(self):
        import inspect
        from commands.account_cmds.cmd_override_chardelete import CmdCharDelete
        source = inspect.getsource(CmdCharDelete.func)
        self.assertIn("active_puppet_id", source)
