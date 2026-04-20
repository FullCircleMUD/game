"""
Tests for custom inputfuncs — semicolon command stacking and alias exemption.

evennia test --settings settings tests.server_tests.test_inputfuncs
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch, call


class TestSemicolonSplitting(TestCase):
    """Verify semicolon command stacking splits correctly and exempts alias/nick."""

    def _call_text(self, raw_input):
        """
        Call the text() inputfunc with a mock session, returning the list of
        command strings that were passed to cmdhandler.
        """
        session = MagicMock()
        session.account = None  # skip nick replacement

        with patch(
            "server.conf.inputfuncs.cmdhandler"
        ) as mock_handler:
            from server.conf.inputfuncs import text

            text(session, raw_input)

        return [c.args[1] for c in mock_handler.call_args_list]

    # ── Normal semicolon splitting ──────────────────────────────

    def test_single_command_no_semicolon(self):
        cmds = self._call_text("get sword")
        self.assertEqual(cmds, ["get sword"])

    def test_two_commands_split(self):
        cmds = self._call_text("get sword;wield sword")
        self.assertEqual(cmds, ["get sword", "wield sword"])

    def test_three_commands_split(self):
        cmds = self._call_text("get canteen bag;drink canteen;put canteen bag")
        self.assertEqual(cmds, ["get canteen bag", "drink canteen", "put canteen bag"])

    def test_whitespace_around_semicolons(self):
        cmds = self._call_text("get sword ; wield sword")
        self.assertEqual(cmds, ["get sword", "wield sword"])

    def test_trailing_semicolon_ignored(self):
        cmds = self._call_text("look;")
        self.assertEqual(cmds, ["look"])

    def test_empty_segments_filtered(self):
        cmds = self._call_text("look;;inventory")
        self.assertEqual(cmds, ["look", "inventory"])

    # ── Alias/nick commands are NOT split ───────────────────────

    def test_alias_not_split(self):
        cmds = self._call_text("alias dc get canteen bag;drink canteen;put canteen bag")
        self.assertEqual(cmds, ["alias dc get canteen bag;drink canteen;put canteen bag"])

    def test_nick_not_split(self):
        cmds = self._call_text("nick dc = get canteen bag;drink canteen")
        self.assertEqual(cmds, ["nick dc = get canteen bag;drink canteen"])

    def test_nickname_not_split(self):
        cmds = self._call_text("nickname dc = look;inventory")
        self.assertEqual(cmds, ["nickname dc = look;inventory"])

    def test_nicks_not_split(self):
        cmds = self._call_text("nicks dc = look;inventory")
        self.assertEqual(cmds, ["nicks dc = look;inventory"])

    def test_alias_case_insensitive(self):
        cmds = self._call_text("ALIAS dc get sword;wield sword")
        self.assertEqual(cmds, ["ALIAS dc get sword;wield sword"])

    # ── Edge cases ──────────────────────────────────────────────

    def test_alias_without_semicolons_unchanged(self):
        cmds = self._call_text("alias mm cast magic missile")
        self.assertEqual(cmds, ["alias mm cast magic missile"])

    def test_command_starting_with_alias_prefix_still_splits(self):
        """A command like 'aliased_thing' should still split on semicolons."""
        cmds = self._call_text("aliased_thing;look")
        self.assertEqual(cmds, ["aliased_thing", "look"])
