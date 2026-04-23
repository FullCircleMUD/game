"""
Tests for CmdServices — consolidated global service script command.

Key behaviours under test:
- Status report lists all scripts (both global and pipeline)
- The targeted form rejects unknown script keys with a clear error
- The ``force`` keyword bypasses the Y/N confirmation
- Pipeline scripts are reset as a group: targeting any one of the
  three triggers all three
- Per-actor scripts (combat handlers, dungeon instances, etc.) are
  unreachable because they are not in the registry
- Partial name matching resolves short aliases

evennia test --settings settings tests.command_tests.test_cmd_services
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_services import (
    CmdServices,
    _ALL_SCRIPTS,
    _BY_KEY,
    _PIPELINE_KEYS,
    _resolve_name,
)


class TestServicesRegistry(EvenniaCommandTest):
    """The registry is the safety mechanism — verify its shape."""

    def create_script(self):
        pass

    def test_pipeline_keys_derived_from_registry(self):
        """_PIPELINE_KEYS is derived from _ALL_SCRIPTS."""
        derived = {
            key for key, _, is_pipeline in _ALL_SCRIPTS if is_pipeline
        }
        self.assertEqual(_PIPELINE_KEYS, derived)

    def test_pipeline_includes_all_three_scripts(self):
        """The full pipeline trio is in the registry."""
        self.assertIn("telemetry_aggregator_service", _PIPELINE_KEYS)
        self.assertIn("nft_saturation_service", _PIPELINE_KEYS)
        self.assertIn("unified_spawn_service", _PIPELINE_KEYS)
        self.assertEqual(len(_PIPELINE_KEYS), 3)

    def test_all_scripts_present(self):
        """Both global and pipeline scripts are in _ALL_SCRIPTS."""
        self.assertEqual(len(_ALL_SCRIPTS), 11)

    def test_per_actor_scripts_not_in_registry(self):
        """
        Combat handlers, dot scripts, dungeon instances, and tutorial
        instances must not be reachable.
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


class TestServicesNameResolution(EvenniaCommandTest):
    """Partial name matching and short aliases."""

    def create_script(self):
        pass

    def test_exact_match(self):
        self.assertEqual(
            _resolve_name("survival_service"), "survival_service"
        )

    def test_short_alias_spawn(self):
        self.assertEqual(
            _resolve_name("spawn"), "unified_spawn_service"
        )

    def test_short_alias_regen(self):
        self.assertEqual(
            _resolve_name("regen"), "regeneration_service"
        )

    def test_partial_match(self):
        self.assertEqual(
            _resolve_name("telemetry"), "telemetry_aggregator_service"
        )

    def test_unknown_returns_none(self):
        self.assertIsNone(_resolve_name("definitely_not_a_real_script"))


@patch("commands.account_cmds.cmd_services.threads.deferToThread",
       lambda func, *a, **kw: MagicMock())
class TestServicesArgParsing(EvenniaCommandTest):
    """Test argument parsing — unknown keys, force, named target."""

    def create_script(self):
        pass

    def test_no_args_shows_report(self):
        """Bare ``services`` shows the status report."""
        result = self.call(
            CmdServices(),
            "",
            caller=self.account,
        )
        self.assertIn("Service Report", result)

    def test_unknown_script_rejected(self):
        """An unknown script key returns an error and lists registry."""
        result = self.call(
            CmdServices(),
            "reset definitely_not_a_real_script",
            caller=self.account,
        )
        self.assertIn("Unknown service", result)
        self.assertIn("regeneration_service", result)

    def test_combat_handler_rejected_as_unknown(self):
        result = self.call(
            CmdServices(),
            "reset combat_handler",
            caller=self.account,
        )
        self.assertIn("Unknown service", result)

    def test_force_keyword_bypasses_prompt(self):
        """``services reset all force`` triggers immediate reset."""
        with patch.object(CmdServices, "_do_reset_all") as mock_do:
            self.call(
                CmdServices(),
                "reset all force",
                caller=self.account,
            )
            mock_do.assert_called_once()

    def test_targeted_force_bypasses_prompt(self):
        """``services reset survival_service force`` triggers immediate reset."""
        with patch.object(CmdServices, "_do_reset_targeted") as mock_do:
            self.call(
                CmdServices(),
                "reset survival_service force",
                caller=self.account,
            )
            mock_do.assert_called_once()
            args, _ = mock_do.call_args
            self.assertEqual(args[0], "survival_service")
            self.assertFalse(args[1])

    def test_invalid_subcommand(self):
        """Non-reset subcommand shows usage."""
        result = self.call(
            CmdServices(),
            "bogus",
            caller=self.account,
        )
        self.assertIn("Usage", result)


@patch("commands.account_cmds.cmd_services.threads.deferToThread",
       lambda func, *a, **kw: MagicMock())
class TestServicesPipelineGrouping(EvenniaCommandTest):
    """
    Targeting any pipeline script must reset all three together
    so the staggered offsets are preserved.
    """

    def create_script(self):
        pass

    def test_targeting_telemetry_marks_pipeline(self):
        with patch.object(CmdServices, "_do_reset_targeted") as mock_do:
            self.call(
                CmdServices(),
                "reset telemetry_aggregator_service force",
                caller=self.account,
            )
            mock_do.assert_called_once()
            args, _ = mock_do.call_args
            self.assertEqual(args[0], "telemetry_aggregator_service")
            self.assertTrue(args[1])

    def test_targeting_saturation_marks_pipeline(self):
        with patch.object(CmdServices, "_do_reset_targeted") as mock_do:
            self.call(
                CmdServices(),
                "reset nft_saturation_service force",
                caller=self.account,
            )
            mock_do.assert_called_once()
            args, _ = mock_do.call_args
            self.assertTrue(args[1])

    def test_targeting_spawn_marks_pipeline(self):
        with patch.object(CmdServices, "_do_reset_targeted") as mock_do:
            self.call(
                CmdServices(),
                "reset unified_spawn_service force",
                caller=self.account,
            )
            mock_do.assert_called_once()
            args, _ = mock_do.call_args
            self.assertTrue(args[1])

    def test_pipeline_worker_calls_reset_pipeline(self):
        cmd = CmdServices()
        with patch(
            "commands.account_cmds.cmd_services._reset_pipeline"
        ) as mock_pipe:
            cmd._reset_targeted_worker("nft_saturation_service", True)
            mock_pipe.assert_called_once()

    def test_non_pipeline_worker_calls_reset_one(self):
        cmd = CmdServices()
        with patch(
            "commands.account_cmds.cmd_services._reset_one"
        ) as mock_one, patch(
            "commands.account_cmds.cmd_services._reset_pipeline"
        ) as mock_pipe:
            cmd._reset_targeted_worker("survival_service", False)
            mock_one.assert_called_once_with("survival_service")
            mock_pipe.assert_not_called()
