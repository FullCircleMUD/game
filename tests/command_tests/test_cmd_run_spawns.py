"""
Tests for CmdRunSpawns — role guard, the on-the-fly SpawnService
creation branch, the per-item budget-preview preamble, and the
dispatch success/error messages.

get_role() is imported locally inside func() (not at module level), so
the role guard is patched at its source, evennia_shards.get_role.
get_spawn_service/set_spawn_service/SpawnService, get_resource_type,
and the calculator classes are all imported locally inside the
command's nested _run() closure too — patched at their own source
modules for the same reason.

SpawnService.run_hourly_cycle() and the calculators' own math are
already covered by tests/spawn_tests/ — these tests mock that layer
and focus on what belongs to this command: dispatch, the "create a
service if missing" branch, and the preview loop's per-item-type
formatting/error-handling.

defer_to_db_thread is patched with a side effect that actually runs
the closure passed to it (catching exceptions into a fake Failure), so
the inline _run()/callback functions execute for real.

evennia test --settings settings tests.command_tests.test_cmd_run_spawns
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_run_spawns import CmdRunSpawns

GET_SPAWN_SERVICE = "blockchain.xrpl.services.spawn.service.get_spawn_service"
SET_SPAWN_SERVICE = "blockchain.xrpl.services.spawn.service.set_spawn_service"
SPAWN_SERVICE_CLASS = "blockchain.xrpl.services.spawn.service.SpawnService"
GET_RESOURCE_TYPE = "blockchain.xrpl.currency_cache.get_resource_type"
RESOURCE_AVG = "blockchain.xrpl.services.spawn.calculators.resource.ResourceCalculator._get_avg_consumption"
RESOURCE_PRICE = "blockchain.xrpl.services.spawn.calculators.resource.ResourceCalculator._get_latest_buy_price"
RESOURCE_MODIFIER = "blockchain.xrpl.services.spawn.calculators.resource.ResourceCalculator.price_modifier"
KNOWLEDGE_SNAPSHOT = "blockchain.xrpl.services.spawn.calculators.knowledge.KnowledgeCalculator._get_snapshot"
DEFER = "commands.account_cmds.cmd_run_spawns.defer_to_db_thread"


class _FakeDeferred:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error

    def addCallback(self, fn):
        if self._error is None:
            fn(self._result)
        return self

    def addErrback(self, fn):
        if self._error is not None:
            fn(self._error)
        return self


def _sync_defer(fn, *args, **kwargs):
    try:
        result = fn(*args, **kwargs)
    except Exception as exc:
        failure = MagicMock()
        failure.getErrorMessage.return_value = str(exc)
        return _FakeDeferred(error=failure)
    return _FakeDeferred(result=result)


def _make_service(config=None, calculators=None):
    service = MagicMock()
    service.config = config or {}
    service._calculators = calculators or {}
    return service


# ══════════════════════════════════════════════════════════════════════════
#  Role guard
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role")
class TestRunSpawnsRoleGuard(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_shard_blocked(self, mock_role):
        mock_role.return_value = "shard"
        result = self.call(CmdRunSpawns(), "", caller=self.account)
        self.assertIn("can only be run OOC on the router", result)

    @patch(DEFER, side_effect=_sync_defer)
    @patch(GET_SPAWN_SERVICE)
    def test_router_allowed(self, mock_get_service, _mock_defer, mock_role):
        mock_role.return_value = "router"
        mock_get_service.return_value = _make_service()
        result = self.call(CmdRunSpawns(), "", caller=self.account)
        self.assertIn("Running spawn cycle", result)

    @patch(DEFER, side_effect=_sync_defer)
    @patch(GET_SPAWN_SERVICE)
    def test_monolith_allowed(self, mock_get_service, _mock_defer, mock_role):
        mock_role.return_value = "monolith"
        mock_get_service.return_value = _make_service()
        result = self.call(CmdRunSpawns(), "", caller=self.account)
        self.assertIn("Running spawn cycle", result)


# ══════════════════════════════════════════════════════════════════════════
#  SpawnService creation-on-the-fly
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role", return_value="monolith")
@patch(DEFER, side_effect=_sync_defer)
class TestSpawnServiceCreatedOnTheFly(EvenniaCommandTest):

    def create_script(self):
        pass

    @patch(SPAWN_SERVICE_CLASS)
    @patch(SET_SPAWN_SERVICE)
    @patch(GET_SPAWN_SERVICE)
    def test_creates_service_when_missing(
        self, mock_get_service, mock_set_service, mock_cls, _mock_defer, _mock_role,
    ):
        mock_get_service.return_value = None
        instance = _make_service()
        mock_cls.return_value = instance

        result = self.call(CmdRunSpawns(), "", caller=self.account)

        self.assertIn("Created SpawnService on the fly", result)
        mock_set_service.assert_called_once_with(instance)
        instance.run_hourly_cycle.assert_called_once()

    @patch(GET_SPAWN_SERVICE)
    def test_does_not_recreate_when_present(self, mock_get_service, _mock_defer, _mock_role):
        existing = _make_service()
        mock_get_service.return_value = existing

        result = self.call(CmdRunSpawns(), "", caller=self.account)

        self.assertNotIn("Created SpawnService on the fly", result)
        existing.run_hourly_cycle.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════
#  Budget preview preamble
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role", return_value="monolith")
@patch(DEFER, side_effect=_sync_defer)
@patch(GET_SPAWN_SERVICE)
class TestBudgetPreview(EvenniaCommandTest):

    def create_script(self):
        pass

    @patch(RESOURCE_MODIFIER, return_value=1.0)
    @patch(RESOURCE_PRICE, return_value=Decimal("5"))
    @patch(RESOURCE_AVG, return_value=Decimal("2"))
    @patch(GET_RESOURCE_TYPE, return_value={"name": "Wheat"})
    def test_resource_item_shows_name_and_budget(
        self, _mock_rt, _mock_avg, _mock_price, _mock_mod, mock_get_service, _mock_defer, _mock_role,
    ):
        calc = MagicMock()
        calc.calculate.return_value = 7
        service = _make_service(
            config={("resource", 1): {
                "calculator": "resource_calc", "default_spawn_rate": 5,
                "target_price_low": 1, "target_price_high": 10,
            }},
            calculators={"resource_calc": calc},
        )
        mock_get_service.return_value = service

        result = self.call(CmdRunSpawns(), "", caller=self.account)

        self.assertIn("Wheat", result)
        self.assertIn("budget=7", result)

    @patch(KNOWLEDGE_SNAPSHOT)
    def test_knowledge_item_shows_display_name_and_budget(
        self, mock_snapshot, mock_get_service, _mock_defer, _mock_role,
    ):
        snapshot = MagicMock()
        snapshot.eligible_players = 10
        snapshot.known_by = 4
        snapshot.unlearned_copies = 1
        snapshot.saturation = 0.4
        mock_snapshot.return_value = snapshot

        calc = MagicMock()
        calc.calculate.return_value = 3
        service = _make_service(
            config={("knowledge", "scroll_fireball"): {
                "calculator": "knowledge_calc", "tier": "basic",
            }},
            calculators={"knowledge_calc": calc},
        )
        mock_get_service.return_value = service

        result = self.call(CmdRunSpawns(), "", caller=self.account)

        self.assertIn("Fireball", result)
        self.assertIn("budget=3", result)

    def test_other_item_type_with_positive_budget_shown(
        self, mock_get_service, _mock_defer, _mock_role,
    ):
        calc = MagicMock()
        calc.calculate.return_value = 4
        service = _make_service(
            config={("gold", "gold"): {"calculator": "gold_calc"}},
            calculators={"gold_calc": calc},
        )
        mock_get_service.return_value = service

        result = self.call(CmdRunSpawns(), "", caller=self.account)

        self.assertIn("gold/gold", result)
        self.assertIn("budget=4", result)

    def test_other_item_type_with_zero_budget_not_shown(
        self, mock_get_service, _mock_defer, _mock_role,
    ):
        calc = MagicMock()
        calc.calculate.return_value = 0
        service = _make_service(
            config={("gold", "gold"): {"calculator": "gold_calc"}},
            calculators={"gold_calc": calc},
        )
        mock_get_service.return_value = service

        result = self.call(CmdRunSpawns(), "", caller=self.account)

        self.assertNotIn("gold/gold", result)

    def test_calculator_exception_shows_error_and_continues(
        self, mock_get_service, _mock_defer, _mock_role,
    ):
        calc = MagicMock()
        calc.calculate.side_effect = ValueError("bad calc")
        service = _make_service(
            config={("gold", "gold"): {"calculator": "gold_calc"}},
            calculators={"gold_calc": calc},
        )
        mock_get_service.return_value = service

        result = self.call(CmdRunSpawns(), "", caller=self.account)

        self.assertIn("ERROR", result)
        self.assertIn("bad calc", result)
        self.assertIn("Spawn cycle complete", result)
        service.run_hourly_cycle.assert_called_once()

    def test_entry_without_calculator_name_skipped(
        self, mock_get_service, _mock_defer, _mock_role,
    ):
        service = _make_service(config={("gold", "gold"): {}})
        mock_get_service.return_value = service

        try:
            result = self.call(CmdRunSpawns(), "", caller=self.account)
        except Exception as exc:
            self.fail(f"raised on missing calculator key: {exc}")
        self.assertIn("Spawn cycle complete", result)

    def test_entry_with_unknown_calculator_name_skipped(
        self, mock_get_service, _mock_defer, _mock_role,
    ):
        service = _make_service(
            config={("gold", "gold"): {"calculator": "does_not_exist"}},
            calculators={},
        )
        mock_get_service.return_value = service

        try:
            result = self.call(CmdRunSpawns(), "", caller=self.account)
        except Exception as exc:
            self.fail(f"raised on unknown calculator name: {exc}")
        self.assertIn("Spawn cycle complete", result)


# ══════════════════════════════════════════════════════════════════════════
#  Dispatch outcomes
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role", return_value="monolith")
@patch(DEFER, side_effect=_sync_defer)
@patch(GET_SPAWN_SERVICE)
class TestRunSpawnsOutcomes(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_success_shows_complete_message(self, mock_get_service, _mock_defer, _mock_role):
        mock_get_service.return_value = _make_service()
        result = self.call(CmdRunSpawns(), "", caller=self.account)
        self.assertIn("Spawn cycle complete", result)

    def test_cycle_failure_shows_error_message(self, mock_get_service, _mock_defer, _mock_role):
        service = _make_service()
        service.run_hourly_cycle.side_effect = RuntimeError("cycle boom")
        mock_get_service.return_value = service

        result = self.call(CmdRunSpawns(), "", caller=self.account)

        self.assertIn("Spawn cycle failed", result)
        self.assertIn("cycle boom", result)
