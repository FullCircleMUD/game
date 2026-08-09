"""
Tests for CmdAMMCheck — role guard, plus _query_pools() and the report
rendering callbacks.

get_role() is imported locally inside func() (not at module level), so
the role guard is patched at its source, evennia_shards.get_role.

CurrencyType is pre-seeded by a data migration (36 resources + gold),
so _query_pools() always iterates real rows too. Tests use a synthetic
currency (is_gold=False, a currency_code get_amm_info won't recognise)
and a resource_filter/side_effect combo so every real currency is
skipped without needing to know or touch its data.

evennia test --settings settings tests.command_tests.test_cmd_amm_check
"""

from decimal import Decimal
from unittest import TestCase as PlainTestCase
from unittest.mock import MagicMock, patch

from django.test import TestCase
from evennia.utils.test_resources import EvenniaCommandTest

from blockchain.xrpl.models import CurrencyType
from commands.account_cmds.cmd_amm_check import (
    CmdAMMCheck,
    _on_pools_complete,
    _on_pools_error,
    _query_pools,
)

FAKE_CODE = "FCMFakeium"
FAKE_NAME = "Fakeium"
GOLD_CODE = "FCMGold"


def _fake_pool_info(gold_reserve=Decimal("1000"), resource_reserve=Decimal("500"),
                     trading_fee=5, gold_first=True):
    r_gold = {"currency": GOLD_CODE, "value": gold_reserve}
    r_resource = {"currency": FAKE_CODE, "value": resource_reserve}
    return {
        "reserve_1": r_gold if gold_first else r_resource,
        "reserve_2": r_resource if gold_first else r_gold,
        "trading_fee": trading_fee,
    }


def _amm_info_side_effect(pool_info):
    """Only responds for FAKE_CODE — every real seeded currency gets None."""
    def _inner(gold, resource_code):
        if resource_code != FAKE_CODE:
            return None
        return pool_info
    return _inner


# ══════════════════════════════════════════════════════════════════════════
#  Role guard
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role")
class TestAMMCheckRoleGuard(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_shard_blocked(self, mock_role):
        mock_role.return_value = "shard"
        result = self.call(CmdAMMCheck(), "", caller=self.account)
        self.assertIn("can only be run OOC on the router", result)

    def test_router_allowed(self, mock_role):
        mock_role.return_value = "router"
        with patch(
            "commands.account_cmds.cmd_amm_check.threads.deferToThread"
        ) as mock_defer:
            result = self.call(CmdAMMCheck(), "", caller=self.account)
        self.assertIn("Querying AMM pools", result)
        mock_defer.assert_called_once()

    def test_monolith_allowed(self, mock_role):
        mock_role.return_value = "monolith"
        with patch(
            "commands.account_cmds.cmd_amm_check.threads.deferToThread"
        ) as mock_defer:
            result = self.call(CmdAMMCheck(), "", caller=self.account)
        self.assertIn("Querying AMM pools", result)
        mock_defer.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════
#  _query_pools
# ══════════════════════════════════════════════════════════════════════════

class TestQueryPools(TestCase):
    databases = {"default", "xrpl"}

    def setUp(self):
        CurrencyType.objects.create(
            currency_code=FAKE_CODE, resource_id=999999, name=FAKE_NAME,
            unit="units", is_gold=False,
        )

    @patch("blockchain.xrpl.xrpl_amm.get_amm_info")
    def test_pool_found_and_returned(self, mock_amm):
        mock_amm.side_effect = _amm_info_side_effect(_fake_pool_info())

        pools = _query_pools(FAKE_NAME.lower())

        self.assertEqual(len(pools), 1)
        self.assertEqual(pools[0]["name"], FAKE_NAME)
        self.assertEqual(pools[0]["currency_code"], FAKE_CODE)

    @patch("blockchain.xrpl.xrpl_amm.get_amm_info")
    def test_reserve_orientation_when_gold_is_reserve_1(self, mock_amm):
        mock_amm.side_effect = _amm_info_side_effect(
            _fake_pool_info(gold_reserve=Decimal("1000"),
                             resource_reserve=Decimal("500"), gold_first=True)
        )

        pools = _query_pools(FAKE_NAME.lower())

        self.assertEqual(pools[0]["gold_reserve"], Decimal("1000"))
        self.assertEqual(pools[0]["resource_reserve"], Decimal("500"))

    @patch("blockchain.xrpl.xrpl_amm.get_amm_info")
    def test_reserve_orientation_when_gold_is_reserve_2(self, mock_amm):
        mock_amm.side_effect = _amm_info_side_effect(
            _fake_pool_info(gold_reserve=Decimal("1000"),
                             resource_reserve=Decimal("500"), gold_first=False)
        )

        pools = _query_pools(FAKE_NAME.lower())

        self.assertEqual(pools[0]["gold_reserve"], Decimal("1000"))
        self.assertEqual(pools[0]["resource_reserve"], Decimal("500"))

    @patch("blockchain.xrpl.xrpl_amm.get_amm_info")
    def test_fee_pct_divides_trading_fee_by_1000(self, mock_amm):
        mock_amm.side_effect = _amm_info_side_effect(
            _fake_pool_info(trading_fee=5)
        )

        pools = _query_pools(FAKE_NAME.lower())

        self.assertEqual(pools[0]["fee_pct"], Decimal("5") / Decimal("1000"))

    @patch("blockchain.xrpl.xrpl_amm.get_amm_info")
    def test_resource_filter_excludes_non_matching(self, mock_amm):
        mock_amm.side_effect = _amm_info_side_effect(_fake_pool_info())

        pools = _query_pools("some_other_resource_name")

        self.assertEqual(pools, [])
        mock_amm.assert_not_called()

    @patch("blockchain.xrpl.xrpl_amm.get_amm_info")
    def test_none_info_skipped(self, mock_amm):
        mock_amm.return_value = None

        pools = _query_pools(FAKE_NAME.lower())

        self.assertEqual(pools, [])

    @patch("blockchain.xrpl.xrpl_amm.get_amm_info")
    def test_exception_during_lookup_skipped_not_raised(self, mock_amm):
        mock_amm.side_effect = Exception("ledger boom")

        try:
            pools = _query_pools(FAKE_NAME.lower())
        except Exception as exc:
            self.fail(f"_query_pools propagated an exception: {exc}")

        self.assertEqual(pools, [])

    @patch("blockchain.xrpl.xrpl_amm.get_amm_info")
    def test_gold_currency_never_queried(self, mock_amm):
        """is_gold=False filter means the gold row itself is never a target."""
        mock_amm.side_effect = _amm_info_side_effect(_fake_pool_info())

        _query_pools(None)

        called_codes = {call.args[1] for call in mock_amm.call_args_list}
        self.assertNotIn(GOLD_CODE, called_codes)


# ══════════════════════════════════════════════════════════════════════════
#  Display callbacks — direct calls, no thread plumbing
# ══════════════════════════════════════════════════════════════════════════

def _pool(name="Fakeium", code=FAKE_CODE, resource_id=999999,
          gold_reserve=Decimal("1000"), resource_reserve=Decimal("500"),
          fee_pct=Decimal("0.005")):
    return {
        "name": name, "currency_code": code, "resource_id": resource_id,
        "gold_reserve": gold_reserve, "resource_reserve": resource_reserve,
        "fee_pct": fee_pct,
    }


class TestOnPoolsComplete(PlainTestCase):

    def test_no_pools_shows_none_detected(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_pools_complete(caller, [])
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("No AMM pools detected", msgs)

    def test_disconnected_caller_is_noop(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 0
        _on_pools_complete(caller, [_pool()])
        caller.msg.assert_not_called()

    def test_pool_shows_name_and_reserves(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_pools_complete(caller, [_pool(name="Fakeium")])
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("Fakeium", msgs)
        self.assertIn("1000", msgs)
        self.assertIn("500", msgs)


class TestOnPoolsError(PlainTestCase):

    def test_shows_error_message(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        failure = MagicMock()
        failure.getErrorMessage.return_value = "boom"
        _on_pools_error(caller, failure)
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("AMM Check Error", msgs)
        self.assertIn("boom", msgs)

    def test_disconnected_caller_is_noop(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 0
        failure = MagicMock()
        _on_pools_error(caller, failure)
        caller.msg.assert_not_called()
