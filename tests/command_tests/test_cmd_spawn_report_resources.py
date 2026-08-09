"""
Tests for CmdSpawnReportResources — router-only, values()-only report.

Key behaviours under test:
- Role guard: only router/monolith may run it
- Empty registry produces a clear "no rooms" message, not a crash
- Per-district grouping, FULL/DEPLETED markers, grand total, by-resource
  roll-up all match what the old instantiated version produced
- The typeclass-path filter (HARVESTING_ROOM_TYPECLASSES) stands in for
  the old isinstance(obj, RoomHarvesting) check without materialising
  any room — verified by planting a same-tagged non-RoomHarvesting room
  and confirming it's excluded
- Rooms with no district tag fall back to "unknown"
- Unknown resource_id (no CurrencyType row) falls back to "Resource #<id>"

evennia test --settings settings tests.command_tests.test_cmd_spawn_report_resources
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_spawn_report_resources import CmdSpawnReportResources


def _make_room(key, resource_id, resource_count, resource_count_max, district=None):
    """Create a RoomHarvesting with explicit resource state.

    Overrides the AttributeProperty defaults set at creation, then
    re-derives spawn_resources_max the same idempotent way
    wb_at_post_build does (see room_harvesting.py's docstring on why a
    second at_object_post_creation() call is safe).
    """
    room = create.create_object(
        "typeclasses.terrain.rooms.room_harvesting.RoomHarvesting",
        key=key,
        nohome=True,
    )
    room.db.resource_id = resource_id
    room.db.resource_count = resource_count
    room.db.resource_count_max = resource_count_max
    room.at_object_post_creation()
    if district:
        room.set_district(district)
    return room


@patch("commands.account_cmds.cmd_spawn_report_resources.get_role")
class TestSpawnReportResourcesRoleGuard(EvenniaCommandTest):
    databases = "__all__"

    def create_script(self):
        pass

    def test_shard_blocked(self, mock_role):
        mock_role.return_value = "shard"
        result = self.call(CmdSpawnReportResources(), "", caller=self.account)
        self.assertIn("can only be run OOC on the router", result)

    def test_router_allowed(self, mock_role):
        mock_role.return_value = "router"
        result = self.call(CmdSpawnReportResources(), "", caller=self.account)
        self.assertIn("No harvesting rooms found", result)

    def test_monolith_allowed(self, mock_role):
        mock_role.return_value = "monolith"
        result = self.call(CmdSpawnReportResources(), "", caller=self.account)
        self.assertIn("No harvesting rooms found", result)


@patch("commands.account_cmds.cmd_spawn_report_resources.get_role", return_value="monolith")
class TestSpawnReportResourcesReport(EvenniaCommandTest):
    databases = "__all__"

    def create_script(self):
        pass

    def test_single_room_shows_district_and_counts(self, _mock_role):
        _make_room("Iron Mine", resource_id=1, resource_count=3,
                    resource_count_max=10, district="millholm_hills")
        result = self.call(CmdSpawnReportResources(), "", caller=self.account)
        self.assertIn("millholm_hills", result)
        self.assertIn("Iron Mine", result)
        self.assertIn("3 / 10", result)

    def test_unknown_resource_id_falls_back_to_number(self, _mock_role):
        _make_room("Odd Room", resource_id=999, resource_count=1,
                    resource_count_max=5, district="test_district")
        result = self.call(CmdSpawnReportResources(), "", caller=self.account)
        self.assertIn("Resource #999", result)

    def test_full_marker_shown_when_at_cap(self, _mock_role):
        _make_room("Full Mine", resource_id=1, resource_count=10,
                    resource_count_max=10, district="test_district")
        result = self.call(CmdSpawnReportResources(), "", caller=self.account)
        self.assertIn("[FULL]", result)

    def test_depleted_marker_shown_when_zero(self, _mock_role):
        _make_room("Empty Mine", resource_id=1, resource_count=0,
                    resource_count_max=10, district="test_district")
        result = self.call(CmdSpawnReportResources(), "", caller=self.account)
        self.assertIn("[DEPLETED]", result)

    def test_no_district_tag_falls_back_to_unknown(self, _mock_role):
        _make_room("Untagged Mine", resource_id=1, resource_count=2,
                    resource_count_max=10)
        result = self.call(CmdSpawnReportResources(), "", caller=self.account)
        self.assertIn("unknown", result)

    def test_grand_total_sums_across_districts(self, _mock_role):
        _make_room("Mine A", resource_id=1, resource_count=3,
                    resource_count_max=10, district="district_a")
        _make_room("Mine B", resource_id=1, resource_count=4,
                    resource_count_max=10, district="district_b")
        result = self.call(CmdSpawnReportResources(), "", caller=self.account)
        self.assertIn("7 / 20 units", result)
        self.assertIn("across 2 rooms", result)

    def test_by_resource_rollup_aggregates_same_resource(self, _mock_role):
        _make_room("Mine A", resource_id=1, resource_count=3,
                    resource_count_max=10, district="district_a")
        _make_room("Mine B", resource_id=1, resource_count=4,
                    resource_count_max=10, district="district_b")
        result = self.call(CmdSpawnReportResources(), "", caller=self.account)
        self.assertIn("By resource:", result)
        self.assertIn("7 / 20", result)

    def test_non_harvesting_room_with_same_tag_excluded(self, _mock_role):
        """
        A room manually carrying the same (key, category) tag but a
        different typeclass must not appear — this is what
        HARVESTING_ROOM_TYPECLASSES replaces isinstance() with.
        """
        decoy = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Decoy Room",
            nohome=True,
        )
        decoy.tags.add("spawn_resources", category="spawn_resources")
        decoy.db.resource_id = 1
        decoy.db.resource_count = 5
        decoy.db.spawn_resources_max = {1: 10}

        result = self.call(CmdSpawnReportResources(), "", caller=self.account)
        self.assertIn("No harvesting rooms found", result)
        self.assertNotIn("Decoy Room", result)
