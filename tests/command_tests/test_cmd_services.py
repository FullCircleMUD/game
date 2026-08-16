"""
Tests for CmdServices — role-scoped service script report + reset.

Key behaviours under test:
- Status report lists only scripts declared for get_role() on this process
- Report shows running/last_repeat/last_work per script
- The targeted form rejects unknown script keys with a clear error
- A script not valid for this role cannot be resolved as a reset target
- The ``force`` keyword bypasses the Y/N confirmation
- Per-actor scripts (combat handlers, dungeon instances, etc.) are
  unreachable because they are not in the registry
- Partial name matching resolves short aliases

evennia test --settings settings tests.command_tests.test_cmd_services
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_services import CmdServices, _resolve_name
from server.conf.at_server_startstop import _SCRIPTS, _select_scripts


class TestServicesRegistry(EvenniaCommandTest):
    """The registry is the safety mechanism — verify its shape."""

    def create_script(self):
        pass

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
        keys = {key for key, _path, _roles, _tags in _SCRIPTS}
        for name in forbidden:
            self.assertNotIn(name, keys, f"{name} must not be resettable")


class TestServicesNameResolution(EvenniaCommandTest):
    """Partial name matching and short aliases, scoped to a role."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.monolith_entries = _select_scripts(role="monolith")
        self.shard_entries = _select_scripts(role="shard")

    def test_exact_match(self):
        self.assertEqual(
            _resolve_name("survival_service", self.monolith_entries),
            "survival_service",
        )

    def test_short_alias_spawn(self):
        self.assertEqual(
            _resolve_name("spawn", self.monolith_entries),
            "unified_spawn_service",
        )

    def test_short_alias_regen(self):
        self.assertEqual(
            _resolve_name("regen", self.monolith_entries),
            "regeneration_service",
        )

    def test_partial_match(self):
        self.assertEqual(
            _resolve_name("telemetry", self.monolith_entries),
            "telemetry_aggregator_service",
        )

    def test_unknown_returns_none(self):
        self.assertIsNone(
            _resolve_name("definitely_not_a_real_script", self.monolith_entries)
        )

    def test_router_only_script_unresolvable_on_shard(self):
        """
        unified_spawn_service is router/monolith-only — a shard's entry
        list must not contain it, so it can never resolve as a target
        there. This is the structural fix for the double-ticker risk.
        """
        self.assertIsNone(
            _resolve_name("unified_spawn_service", self.shard_entries)
        )

    def test_game_role_script_unresolvable_on_router(self):
        """survival_service (GAME_ROLES) must not resolve on a router."""
        router_entries = _select_scripts(role="router")
        self.assertIsNone(_resolve_name("survival_service", router_entries))


@patch("commands.account_cmds.cmd_services.get_role", return_value="monolith")
@patch("commands.account_cmds.cmd_services.threads.deferToThread",
       lambda func, *a, **kw: MagicMock())
class TestServicesArgParsing(EvenniaCommandTest):
    """Test argument parsing — unknown keys, force, named target."""

    def create_script(self):
        pass

    def test_no_args_shows_report(self, _mock_role):
        """Bare ``services`` shows the status report."""
        result = self.call(
            CmdServices(),
            "",
            caller=self.account,
        )
        self.assertIn("Service Report", result)

    def test_report_lists_role_scoped_scripts(self, _mock_role):
        result = self.call(
            CmdServices(),
            "",
            caller=self.account,
        )
        self.assertIn("survival_service", result)
        self.assertIn("RUNNING", result)
        self.assertIn("LAST REPEAT", result)
        self.assertIn("LAST WORK", result)

    def test_unknown_script_rejected(self, _mock_role):
        """An unknown script key returns an error and lists registry."""
        result = self.call(
            CmdServices(),
            "reset definitely_not_a_real_script",
            caller=self.account,
        )
        self.assertIn("Unknown service", result)
        self.assertIn("regeneration_service", result)

    def test_combat_handler_rejected_as_unknown(self, _mock_role):
        result = self.call(
            CmdServices(),
            "reset combat_handler",
            caller=self.account,
        )
        self.assertIn("Unknown service", result)

    def test_force_keyword_bypasses_prompt(self, _mock_role):
        """``services reset <name> force`` triggers immediate reset."""
        with patch.object(CmdServices, "_do_reset_targeted") as mock_do:
            self.call(
                CmdServices(),
                "reset survival_service force",
                caller=self.account,
            )
            mock_do.assert_called_once()
            args, _ = mock_do.call_args
            self.assertEqual(args[0], "survival_service")

    def test_multiple_names_rejected(self, _mock_role):
        """Only a single target name is accepted — no 'reset all'."""
        result = self.call(
            CmdServices(),
            "reset survival_service regeneration_service",
            caller=self.account,
        )
        self.assertIn("Usage", result)

    def test_invalid_subcommand(self, _mock_role):
        """Non-reset subcommand shows usage."""
        result = self.call(
            CmdServices(),
            "bogus",
            caller=self.account,
        )
        self.assertIn("Usage", result)


@patch("commands.account_cmds.cmd_services.get_role", return_value="shard")
@patch("commands.account_cmds.cmd_services.threads.deferToThread",
       lambda func, *a, **kw: MagicMock())
class TestServicesRoleGating(EvenniaCommandTest):
    """A router-only script must be structurally unreachable from a shard."""

    def create_script(self):
        pass

    def test_router_only_script_rejected_on_shard(self, _mock_role):
        result = self.call(
            CmdServices(),
            "reset unified_spawn_service",
            caller=self.account,
        )
        self.assertIn("Unknown service", result)

    def test_report_omits_router_only_scripts_on_shard(self, _mock_role):
        result = self.call(
            CmdServices(),
            "",
            caller=self.account,
        )
        self.assertNotIn("unified_spawn_service", result)
        self.assertIn("survival_service", result)
