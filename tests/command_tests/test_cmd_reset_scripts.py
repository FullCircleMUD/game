"""
Tests for CmdResetScripts — global service script reset command.

The command operates on an explicit allowlist (RESETTABLE_SCRIPTS)
of global service scripts. Per-actor and per-instance scripts
(combat handlers, dot scripts, dungeon instances, tutorial
instances) are out of scope and unreachable from this command.

Key behaviours under test:
- The full-reset prompt path runs through every script on the
  allowlist
- The targeted form rejects unknown script keys with a clear error
- The `force` keyword bypasses the Y/N confirmation
- Pipeline scripts are reset as a group: targeting any one of the
  three triggers all three
- The allowlist excludes per-actor scripts entirely (a name like
  `combat_handler` is rejected as unknown)

evennia test --settings settings tests.command_tests.test_cmd_reset_scripts
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_reset_scripts import (
    CmdResetScripts,
    RESETTABLE_SCRIPTS,
    _BY_KEY,
    _PIPELINE_KEYS,
)


class TestResetScriptsAllowlist(EvenniaCommandTest):
    """The allowlist is the safety mechanism — verify its shape."""

    def create_script(self):
        pass

    def test_pipeline_keys_match_allowlist(self):
        """_PIPELINE_KEYS is derived from RESETTABLE_SCRIPTS."""
        derived = {
            key for key, _, is_pipeline in RESETTABLE_SCRIPTS if is_pipeline
        }
        self.assertEqual(_PIPELINE_KEYS, derived)

    def test_pipeline_includes_all_three_scripts(self):
        """The full pipeline trio is in the allowlist."""
        self.assertIn("telemetry_aggregator_service", _PIPELINE_KEYS)
        self.assertIn("nft_saturation_service", _PIPELINE_KEYS)
        self.assertIn("unified_spawn_service", _PIPELINE_KEYS)
        self.assertEqual(len(_PIPELINE_KEYS), 3)

    def test_per_actor_scripts_not_in_allowlist(self):
        """
        Combat handlers, dot scripts, dungeon instances, and tutorial
        instances must not be reachable. Spot-check a few.
        """
        forbidden = [
            "combat_handler",
            "acid_dot",
            "poison_dot",
            "dungeon_instance",
            "tutorial_instance",
            "effect_timer",
        ]
        for name in forbidden:
            self.assertNotIn(name, _BY_KEY, f"{name} must not be resettable")


@patch("commands.account_cmds.cmd_reset_scripts.threads.deferToThread",
       lambda func, *a, **kw: MagicMock())
class TestResetScriptsArgParsing(EvenniaCommandTest):
    """Test argument parsing — unknown keys, force, named target."""

    def create_script(self):
        pass

    def test_unknown_script_rejected(self):
        """An unknown script key returns an error and lists allowlist."""
        result = self.call(
            CmdResetScripts(),
            "definitely_not_a_real_script",
            caller=self.account,
        )
        self.assertIn("Unknown script", result)
        # Allowlist should be shown
        self.assertIn("regeneration_service", result)

    def test_combat_handler_rejected_as_unknown(self):
        """
        Even though combat handlers exist as DefaultScripts, the
        allowlist must reject the key entirely.
        """
        result = self.call(
            CmdResetScripts(),
            "combat_handler",
            caller=self.account,
        )
        self.assertIn("Unknown script", result)

    def test_dungeon_instance_rejected_as_unknown(self):
        """Dungeon instance scripts are out of scope."""
        result = self.call(
            CmdResetScripts(),
            "dungeon_instance",
            caller=self.account,
        )
        self.assertIn("Unknown script", result)

    def test_force_keyword_bypasses_prompt(self):
        """`reset_scripts force` triggers immediate reset, no Y/N."""
        with patch.object(
            CmdResetScripts, "_do_reset_all"
        ) as mock_do:
            self.call(
                CmdResetScripts(),
                "force",
                caller=self.account,
            )
            mock_do.assert_called_once()

    def test_targeted_force_bypasses_prompt(self):
        """`reset_scripts <key> force` triggers immediate single reset."""
        with patch.object(
            CmdResetScripts, "_do_reset_targeted"
        ) as mock_do:
            self.call(
                CmdResetScripts(),
                "hunger_service force",
                caller=self.account,
            )
            mock_do.assert_called_once()
            # First positional arg is the key
            args, _ = mock_do.call_args
            self.assertEqual(args[0], "hunger_service")
            # Second positional arg is is_pipeline (False for hunger)
            self.assertFalse(args[1])


@patch("commands.account_cmds.cmd_reset_scripts.threads.deferToThread",
       lambda func, *a, **kw: MagicMock())
class TestResetScriptsPipelineGrouping(EvenniaCommandTest):
    """
    Targeting any pipeline script must reset all three together
    so the staggered offsets are preserved.
    """

    def create_script(self):
        pass

    def test_targeting_telemetry_marks_pipeline(self):
        with patch.object(
            CmdResetScripts, "_do_reset_targeted"
        ) as mock_do:
            self.call(
                CmdResetScripts(),
                "telemetry_aggregator_service force",
                caller=self.account,
            )
            mock_do.assert_called_once()
            args, _ = mock_do.call_args
            self.assertEqual(args[0], "telemetry_aggregator_service")
            # is_pipeline must be True
            self.assertTrue(args[1])

    def test_targeting_saturation_marks_pipeline(self):
        with patch.object(
            CmdResetScripts, "_do_reset_targeted"
        ) as mock_do:
            self.call(
                CmdResetScripts(),
                "nft_saturation_service force",
                caller=self.account,
            )
            mock_do.assert_called_once()
            args, _ = mock_do.call_args
            self.assertTrue(args[1])

    def test_targeting_spawn_marks_pipeline(self):
        with patch.object(
            CmdResetScripts, "_do_reset_targeted"
        ) as mock_do:
            self.call(
                CmdResetScripts(),
                "unified_spawn_service force",
                caller=self.account,
            )
            mock_do.assert_called_once()
            args, _ = mock_do.call_args
            self.assertTrue(args[1])

    def test_pipeline_worker_calls_reset_pipeline(self):
        """
        _reset_targeted_worker for a pipeline key calls _reset_pipeline,
        which delegates to _create_pipeline_scripts(skip_existing=False).
        """
        cmd = CmdResetScripts()
        with patch(
            "commands.account_cmds.cmd_reset_scripts._reset_pipeline"
        ) as mock_pipe:
            cmd._reset_targeted_worker("nft_saturation_service", True)
            mock_pipe.assert_called_once()

    def test_non_pipeline_worker_calls_reset_one(self):
        """
        _reset_targeted_worker for a non-pipeline key calls _reset_one,
        not _reset_pipeline.
        """
        cmd = CmdResetScripts()
        with patch(
            "commands.account_cmds.cmd_reset_scripts._reset_one"
        ) as mock_one, patch(
            "commands.account_cmds.cmd_reset_scripts._reset_pipeline"
        ) as mock_pipe:
            cmd._reset_targeted_worker("hunger_service", False)
            mock_one.assert_called_once_with("hunger_service")
            mock_pipe.assert_not_called()
