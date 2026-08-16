"""
Tests for CmdSnapshotHistory — role guard, type resolution, the summary
view, and all three detail views.

get_role() is imported locally inside func() (not at module level), so
the role guard is patched at its source, evennia_shards.get_role.

evennia test --settings settings tests.command_tests.test_cmd_snapshot_history
"""

from datetime import timedelta
from unittest import TestCase as PlainTestCase
from unittest.mock import patch

from django.utils import timezone
from evennia.utils.test_resources import EvenniaCommandTest

from blockchain.xrpl.models import EconomySnapshot, ResourceSnapshot, SaturationSnapshot
from commands.account_cmds.cmd_snapshot_history import CmdSnapshotHistory, _resolve_type

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


def _saturation(hour=None, item_key="fireball", category="spell", **overrides):
    defaults = dict(
        hour=hour or NOW, item_key=item_key, category=category,
        active_players_7d=15, eligible_players=15, known_by=5,
        unlearned_copies=2, in_circulation=0, saturation=0.33,
        spawn_budget=10, spawn_quest_debt=0, spawn_placed=5, spawn_dropped=0,
    )
    defaults.update(overrides)
    return SaturationSnapshot.objects.create(**defaults)


def _resource(hour=None, currency_code="FCMWheat", **overrides):
    defaults = dict(
        hour=hour or NOW, currency_code=currency_code,
        in_character=100, in_account=50, in_spawned=10, in_reserve=200,
        in_sink=5, produced_1h=20, consumed_1h=15, traded_1h=5,
    )
    defaults.update(overrides)
    return ResourceSnapshot.objects.create(**defaults)


# ══════════════════════════════════════════════════════════════════════════
#  _resolve_type — pure function
# ══════════════════════════════════════════════════════════════════════════

class TestResolveType(PlainTestCase):

    def test_exact_match(self):
        self.assertEqual(_resolve_type("economy"), "economy")

    def test_partial_prefix_match(self):
        self.assertEqual(_resolve_type("eco"), "economy")
        self.assertEqual(_resolve_type("sat"), "saturation")
        self.assertEqual(_resolve_type("res"), "resources")

    def test_unknown_returns_none(self):
        self.assertIsNone(_resolve_type("definitely_not_a_type"))

    def test_case_insensitive(self):
        self.assertEqual(_resolve_type("ECONOMY"), "economy")


# ══════════════════════════════════════════════════════════════════════════
#  Role guard
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role")
class TestSnapshotHistoryRoleGuard(EvenniaCommandTest):
    databases = {"default", "xrpl"}

    def create_script(self):
        pass

    def test_shard_blocked(self, mock_role):
        mock_role.return_value = "shard"
        result = self.call(CmdSnapshotHistory(), "", caller=self.account)
        self.assertIn("can only be run OOC on the router", result)

    def test_router_allowed(self, mock_role):
        mock_role.return_value = "router"
        result = self.call(CmdSnapshotHistory(), "", caller=self.account)
        self.assertIn("Snapshot History", result)

    def test_monolith_allowed(self, mock_role):
        mock_role.return_value = "monolith"
        result = self.call(CmdSnapshotHistory(), "", caller=self.account)
        self.assertIn("Snapshot History", result)


# ══════════════════════════════════════════════════════════════════════════
#  Summary view
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role", return_value="monolith")
class TestSnapshotHistorySummary(EvenniaCommandTest):
    databases = {"default", "xrpl"}

    def create_script(self):
        pass

    def test_no_snapshots_shows_none_yet(self, _mock_role):
        result = self.call(CmdSnapshotHistory(), "", caller=self.account)
        self.assertIn("Economy Snapshots", result)
        self.assertIn("None yet", result)
        self.assertIn("Saturation Snapshots", result)
        self.assertIn("Resource Snapshots", result)

    def test_economy_summary_shows_recent(self, _mock_role):
        _economy(players_online=42)
        result = self.call(CmdSnapshotHistory(), "", caller=self.account)
        self.assertIn("42 online", result)

    def test_saturation_summary_groups_by_category(self, _mock_role):
        _saturation(item_key="fireball", category="spell")
        _saturation(item_key="ironsword_recipe", category="recipe")
        _saturation(item_key="rare_gem", category="item")
        result = self.call(CmdSnapshotHistory(), "", caller=self.account)
        self.assertIn("1 spells", result)
        self.assertIn("1 recipes", result)
        self.assertIn("1 items", result)

    def test_resource_summary_shows_count_and_latest_hour(self, _mock_role):
        _resource(currency_code="FCMWheat")
        _resource(currency_code="FCMIron")
        result = self.call(CmdSnapshotHistory(), "", caller=self.account)
        self.assertIn("2 resources tracked", result)


# ══════════════════════════════════════════════════════════════════════════
#  Type resolution / index parsing at the command level
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role", return_value="monolith")
class TestSnapshotHistoryArgParsing(EvenniaCommandTest):
    databases = {"default", "xrpl"}

    def create_script(self):
        pass

    def test_unknown_type_shows_error(self, _mock_role):
        result = self.call(CmdSnapshotHistory(), "bogus", caller=self.account)
        self.assertIn("Unknown snapshot type", result)
        self.assertIn("Types: economy, saturation, resources", result)

    def test_invalid_index_shows_error(self, _mock_role):
        result = self.call(CmdSnapshotHistory(), "economy notanumber", caller=self.account)
        self.assertIn("Invalid index", result)

    def test_negative_index_clamped_to_one(self, _mock_role):
        _economy(players_online=7)
        result = self.call(CmdSnapshotHistory(), "economy -5", caller=self.account)
        self.assertIn("Economy Snapshot #1", result)


# ══════════════════════════════════════════════════════════════════════════
#  Economy detail
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role", return_value="monolith")
class TestEconomyDetail(EvenniaCommandTest):
    databases = {"default", "xrpl"}

    def create_script(self):
        pass

    def test_no_snapshots_shows_message(self, _mock_role):
        result = self.call(CmdSnapshotHistory(), "economy", caller=self.account)
        self.assertIn("No economy snapshots found", result)

    def test_index_beyond_available_shows_message(self, _mock_role):
        _economy()
        result = self.call(CmdSnapshotHistory(), "economy 5", caller=self.account)
        self.assertIn("Only 1 economy snapshot(s) available", result)

    def test_shows_full_detail(self, _mock_role):
        _economy(players_online=9, gold_circulation=12345)
        result = self.call(CmdSnapshotHistory(), "economy", caller=self.account)
        self.assertIn("Players Online:", result)
        self.assertIn("9", result)
        self.assertIn("12,345", result)

    def test_partial_name_resolves(self, _mock_role):
        _economy(players_online=3)
        result = self.call(CmdSnapshotHistory(), "eco", caller=self.account)
        self.assertIn("Economy Snapshot #1", result)


# ══════════════════════════════════════════════════════════════════════════
#  Saturation detail
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role", return_value="monolith")
class TestSaturationDetail(EvenniaCommandTest):
    databases = {"default", "xrpl"}

    def create_script(self):
        pass

    def test_no_snapshots_shows_message(self, _mock_role):
        result = self.call(CmdSnapshotHistory(), "saturation", caller=self.account)
        self.assertIn("No saturation snapshots found", result)

    def test_index_beyond_available_shows_message(self, _mock_role):
        _saturation()
        result = self.call(CmdSnapshotHistory(), "saturation 5", caller=self.account)
        self.assertIn("Only 1 saturation hour(s) available", result)

    def test_spell_row_shows_known_and_unlearned(self, _mock_role):
        _saturation(item_key="fireball", category="spell",
                     known_by=4, unlearned_copies=2)
        result = self.call(CmdSnapshotHistory(), "saturation", caller=self.account)
        self.assertIn("fireball", result)
        self.assertIn("known=4", result)
        self.assertIn("unlearned=2", result)

    def test_item_row_shows_circulation(self, _mock_role):
        _saturation(item_key="rare_gem", category="item", in_circulation=7)
        result = self.call(CmdSnapshotHistory(), "saturation", caller=self.account)
        self.assertIn("rare_gem", result)
        self.assertIn("circ=7", result)

    def test_category_header_shown(self, _mock_role):
        _saturation(item_key="fireball", category="spell")
        result = self.call(CmdSnapshotHistory(), "saturation", caller=self.account)
        self.assertIn("Spells", result)


# ══════════════════════════════════════════════════════════════════════════
#  Resource detail
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role", return_value="monolith")
class TestResourceDetail(EvenniaCommandTest):
    databases = {"default", "xrpl"}

    def create_script(self):
        pass

    def test_no_snapshots_shows_message(self, _mock_role):
        result = self.call(CmdSnapshotHistory(), "resources", caller=self.account)
        self.assertIn("No resource snapshots found", result)

    def test_index_beyond_available_shows_message(self, _mock_role):
        _resource()
        result = self.call(CmdSnapshotHistory(), "resources 5", caller=self.account)
        self.assertIn("Only 1 resource hour(s) available", result)

    def test_shows_currency_and_circulation(self, _mock_role):
        _resource(currency_code="FCMWheat", in_character=111)
        result = self.call(CmdSnapshotHistory(), "resources", caller=self.account)
        self.assertIn("FCMWheat", result)
        self.assertIn("char=111", result)

    def test_amm_price_shows_na_when_null(self, _mock_role):
        _resource(currency_code="FCMWheat", amm_buy_price=None, amm_sell_price=None)
        result = self.call(CmdSnapshotHistory(), "resources", caller=self.account)
        self.assertIn("buy=n/a", result)
        self.assertIn("sell=n/a", result)

    def test_amm_price_shown_when_present(self, _mock_role):
        _resource(currency_code="FCMWheat", amm_buy_price=2.5, amm_sell_price=2.0)
        result = self.call(CmdSnapshotHistory(), "resources", caller=self.account)
        self.assertIn("buy=2.5g", result)
        self.assertIn("sell=2.0g", result)
