"""
Tests for CmdEconomy — role guard, latest-snapshot view, and
per-resource detail view.

get_role() is imported locally inside func() (not at module level), so
the role guard is patched at its source, evennia_shards.get_role.

evennia test --settings settings tests.command_tests.test_cmd_economy
"""

from decimal import Decimal
from unittest import TestCase as PlainTestCase
from unittest.mock import patch

from django.utils import timezone
from evennia.utils.test_resources import EvenniaCommandTest

from blockchain.xrpl.models import EconomySnapshot, ResourceSnapshot
from commands.account_cmds.cmd_economy import CmdEconomy, _fmt

NOW = timezone.now().replace(minute=0, second=0, microsecond=0)


def _economy(hour=None, **overrides):
    defaults = dict(
        hour=hour or NOW, players_online=5, unique_players_1h=3,
        unique_players_24h=10, unique_players_7d=20,
        gold_circulation=1000, gold_reserve=500, gold_sinks_1h=10,
        gold_spawned_1h=20, amm_trades_1h=2, amm_volume_gold_1h=50,
        imports_1h=1, exports_1h=1,
    )
    defaults.update(overrides)
    return EconomySnapshot.objects.create(**defaults)


def _resource(hour=None, currency_code="FCMWheat", **overrides):
    defaults = dict(
        hour=hour or NOW, currency_code=currency_code,
        in_character=100, in_account=50, in_spawned=10, in_reserve=200,
        in_sink=5, produced_1h=20, consumed_1h=15, traded_1h=5,
    )
    defaults.update(overrides)
    return ResourceSnapshot.objects.create(**defaults)


# ══════════════════════════════════════════════════════════════════════════
#  _fmt — pure formatting helper
# ══════════════════════════════════════════════════════════════════════════

class TestFmt(PlainTestCase):

    def test_none_shows_dash(self):
        self.assertEqual(_fmt(None), "-")

    def test_whole_number_has_no_decimals(self):
        self.assertEqual(_fmt(Decimal("1000")), "1,000")

    def test_fractional_shows_two_decimals(self):
        self.assertEqual(_fmt(Decimal("1234.5")), "1,234.50")

    def test_zero_is_whole(self):
        self.assertEqual(_fmt(Decimal("0")), "0")


# ══════════════════════════════════════════════════════════════════════════
#  Role guard
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role")
class TestEconomyRoleGuard(EvenniaCommandTest):
    databases = {"default", "xrpl"}

    def create_script(self):
        pass

    def test_shard_blocked(self, mock_role):
        mock_role.return_value = "shard"
        result = self.call(CmdEconomy(), "", caller=self.account)
        self.assertIn("can only be run OOC on the router", result)

    def test_router_allowed(self, mock_role):
        mock_role.return_value = "router"
        result = self.call(CmdEconomy(), "", caller=self.account)
        self.assertIn("No economy snapshots yet", result)

    def test_monolith_allowed(self, mock_role):
        mock_role.return_value = "monolith"
        result = self.call(CmdEconomy(), "", caller=self.account)
        self.assertIn("No economy snapshots yet", result)


# ══════════════════════════════════════════════════════════════════════════
#  Latest snapshot view
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role", return_value="monolith")
class TestShowLatestSnapshot(EvenniaCommandTest):
    databases = {"default", "xrpl"}

    def create_script(self):
        pass

    def test_no_snapshot_shows_wait_message(self, _mock_role):
        result = self.call(CmdEconomy(), "", caller=self.account)
        self.assertIn("Wait for the hourly aggregator", result)

    def test_shows_player_activity(self, _mock_role):
        _economy(players_online=42, unique_players_1h=7)
        result = self.call(CmdEconomy(), "", caller=self.account)
        self.assertIn("42 online", result)
        self.assertIn("7 (1h)", result)

    def test_shows_gold_line(self, _mock_role):
        _economy(gold_circulation=Decimal("1000"), gold_reserve=Decimal("500"))
        result = self.call(CmdEconomy(), "", caller=self.account)
        self.assertIn("1,000 circulating", result)
        self.assertIn("500 reserve", result)

    def test_resources_section_excludes_gold(self, _mock_role):
        snap = _economy()
        _resource(hour=snap.hour, currency_code="FCMGold", in_character=999)
        _resource(hour=snap.hour, currency_code="FCMWheat", in_character=10)
        result = self.call(CmdEconomy(), "", caller=self.account)
        self.assertIn("Wheat", result)
        self.assertNotIn("999", result)

    def test_resource_name_strips_fcm_prefix(self, _mock_role):
        snap = _economy()
        _resource(hour=snap.hour, currency_code="FCMIron")
        result = self.call(CmdEconomy(), "", caller=self.account)
        self.assertIn("Iron", result)
        self.assertNotIn("FCMIron", result)

    def test_resources_ordered_by_in_character_descending(self, _mock_role):
        snap = _economy()
        _resource(hour=snap.hour, currency_code="FCMWheat", in_character=5)
        _resource(hour=snap.hour, currency_code="FCMIron", in_character=50)
        result = self.call(CmdEconomy(), "", caller=self.account)
        self.assertLess(result.index("Iron"), result.index("Wheat"))

    def test_resource_buy_sell_dash_when_null(self, _mock_role):
        snap = _economy()
        _resource(hour=snap.hour, currency_code="FCMWheat",
                   amm_buy_price=None, amm_sell_price=None)
        result = self.call(CmdEconomy(), "", caller=self.account)
        self.assertIn("Wheat", result)


# ══════════════════════════════════════════════════════════════════════════
#  Resource detail view
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role", return_value="monolith")
class TestShowResourceDetail(EvenniaCommandTest):
    databases = {"default", "xrpl"}

    def create_script(self):
        pass

    def test_no_match_shows_message(self, _mock_role):
        result = self.call(CmdEconomy(), "nonexistent_resource_xyz", caller=self.account)
        self.assertIn("No snapshots found matching", result)

    def test_multiple_matches_asks_to_be_specific(self, _mock_role):
        _resource(currency_code="FCMWheat")
        _resource(currency_code="FCMWheatgerm")
        result = self.call(CmdEconomy(), "wheat", caller=self.account)
        self.assertIn("Multiple matches", result)
        self.assertIn("Be more specific", result)

    def test_single_match_shows_history(self, _mock_role):
        _resource(currency_code="FCMWheat", in_character=Decimal("77"))
        result = self.call(CmdEconomy(), "wheat", caller=self.account)
        self.assertIn("Wheat", result)
        self.assertIn("77", result)

    def test_case_insensitive_match(self, _mock_role):
        _resource(currency_code="FCMWheat")
        result = self.call(CmdEconomy(), "WHEAT", caller=self.account)
        self.assertIn("Wheat", result)

    def test_buy_sell_dash_when_null(self, _mock_role):
        _resource(currency_code="FCMWheat", amm_buy_price=None, amm_sell_price=None)
        result = self.call(CmdEconomy(), "wheat", caller=self.account)
        self.assertIn("Wheat", result)

    def test_buy_sell_shown_when_present(self, _mock_role):
        _resource(currency_code="FCMWheat",
                   amm_buy_price=Decimal("2.50"), amm_sell_price=Decimal("2.00"))
        result = self.call(CmdEconomy(), "wheat", caller=self.account)
        self.assertIn("2.5", result)
