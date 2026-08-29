"""Evennia's command-nesting counter must not pin actors in memory.

``cmdhandler._COMMAND_NESTING`` counts recursion depth per caller and never
removes the key, so a ``defaultdict`` keyed on the object holds a strong
reference to every character and mob that has ever run a command — for the
life of the process. ``_patch_command_nesting_leak`` swaps in a dict that
drops the key on returning to zero.

The upstream-shape tests exist so this fails loudly if a future Evennia
renames or restructures the counter. Without them the patch would silently
stop applying and the leak would return unnoticed.

evennia test --settings settings tests.server_tests.test_command_nesting_leak
"""

from collections import defaultdict

from evennia.utils.test_resources import EvenniaTest

from server.conf.at_server_startstop import _patch_command_nesting_leak


class TestUpstreamShapeUnchanged(EvenniaTest):
    """Guards the assumptions the patch depends on."""

    def test_counter_exists_and_is_a_defaultdict(self):
        import evennia.commands.cmdhandler as cmdhandler
        self.assertTrue(
            hasattr(cmdhandler, "_COMMAND_NESTING"),
            "Evennia no longer exposes _COMMAND_NESTING — the patch in "
            "at_server_startstop._patch_command_nesting_leak is now a no-op "
            "and the leak is back. Re-check upstream cmdhandler.",
        )
        self.assertIsInstance(cmdhandler._COMMAND_NESTING, dict)

    def test_running_a_real_command_leaves_no_entry_behind(self):
        """End-to-end: the patch holds when a command goes through cmdhandler.

        Asserted against a real command rather than by inspecting bytecode —
        ``cmdhandler.cmdhandler`` is wrapped by ``inlineCallbacks``, so
        introspecting its code object tests the decorator, not the function.
        """
        import evennia.commands.cmdhandler as cmdhandler
        original = cmdhandler._COMMAND_NESTING
        try:
            _patch_command_nesting_leak()
            self.char1.execute_cmd("look")
            self.assertNotIn(
                self.char1, cmdhandler._COMMAND_NESTING,
                "caller retained after a real command — the patch is not "
                "reaching cmdhandler, so the leak is live",
            )
        finally:
            cmdhandler._COMMAND_NESTING = original


class TestPatchedCounterClearsKeys(EvenniaTest):
    """The replacement drops a caller once its count returns to zero."""

    def setUp(self):
        super().setUp()
        import evennia.commands.cmdhandler as cmdhandler
        self._original = cmdhandler._COMMAND_NESTING
        _patch_command_nesting_leak()
        self.counter = cmdhandler._COMMAND_NESTING

    def tearDown(self):
        import evennia.commands.cmdhandler as cmdhandler
        cmdhandler._COMMAND_NESTING = self._original
        super().tearDown()

    def test_key_is_removed_when_count_returns_to_zero(self):
        self.counter[self.char1] += 1
        self.assertIn(self.char1, self.counter)
        self.counter[self.char1] -= 1
        self.assertNotIn(
            self.char1, self.counter,
            "caller still held after its command finished — this is the leak",
        )

    def test_nested_commands_still_balance(self):
        """Only the outermost decrement reaches zero."""
        self.counter[self.char1] += 1
        self.counter[self.char1] += 1
        self.counter[self.char1] -= 1
        self.assertIn(
            self.char1, self.counter,
            "dropped the caller while a nested command was still running",
        )
        self.assertEqual(self.counter[self.char1], 1)
        self.counter[self.char1] -= 1
        self.assertNotIn(self.char1, self.counter)

    def test_recursion_limit_still_reachable(self):
        """The counter must still count — the guard depends on it."""
        for _ in range(5):
            self.counter[self.char1] += 1
        self.assertEqual(self.counter[self.char1], 5)

    def test_unpatched_defaultdict_leaks_by_comparison(self):
        """Records upstream behaviour, so the difference stays visible."""
        vanilla = defaultdict(lambda: 0)
        vanilla[self.char1] += 1
        vanilla[self.char1] -= 1
        self.assertIn(
            self.char1, vanilla,
            "upstream now clears its own keys — this patch can be removed",
        )
