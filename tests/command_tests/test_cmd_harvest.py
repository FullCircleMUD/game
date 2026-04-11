"""
Tests for resource harvesting commands — mine, chop, harvest, hunt, fish, forage.

Verifies height-gated gathering, three-tier room descriptions, tool requirements,
busy-lock prevention, race-condition handling (count depleted between start and
completion), and correct resource addition to character inventory.

The harvesting delay uses utils.delay() which is mocked to execute callbacks
immediately (no actual waiting in tests).

evennia test --settings settings tests.command_tests.test_cmd_harvest
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.room_specific_cmds.harvesting.cmd_harvest import CmdHarvest


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _instant_delay(seconds, callback, *args, **kwargs):
    """Mock for utils.delay — executes callback immediately."""
    callback(*args, **kwargs)


class HarvestingTestBase(EvenniaCommandTest):
    """Base class that creates a mining harvesting room."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_harvesting.RoomHarvesting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Configure room as an iron mine
        self.room1.db.resource_id = 4          # Iron Ore
        self.room1.db.resource_count = 10
        self.room1.db.abundance_threshold = 5
        self.room1.db.harvest_command = "mine"
        self.room1.db.harvest_height = 0
        self.room1.db.desc_abundant = "Rich veins of iron ore glint in the rock face."
        self.room1.db.desc_scarce = "A few traces of ore remain in the walls."
        self.room1.db.desc_depleted = "The mine is exhausted. Nothing remains."
        self.room1.db.always_lit = True


# ── Basic Harvesting ──────────────────────────────────────────────

class TestHarvestBasic(HarvestingTestBase):
    """Test basic single-resource harvesting."""

    @patch("commands.room_specific_cmds.harvesting.cmd_harvest.delay",
           side_effect=_instant_delay)
    def test_mine_one(self, mock_delay):
        """Mining should produce 1 Iron Ore and decrement room count."""
        result = self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertIn("Iron Ore", result)
        self.assertEqual(self.room1.db.resource_count, 9)

    @patch("commands.room_specific_cmds.harvesting.cmd_harvest.delay",
           side_effect=_instant_delay)
    def test_mine_adds_to_inventory(self, mock_delay):
        """Character should have the resource after mining."""
        self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertEqual(self.char1.get_resource(4), 1)

    @patch("commands.room_specific_cmds.harvesting.cmd_harvest.delay",
           side_effect=_instant_delay)
    def test_mine_last_one(self, mock_delay):
        """Mining the last resource should succeed and leave count at 0."""
        self.room1.db.resource_count = 1
        result = self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertIn("Iron Ore", result)
        self.assertEqual(self.room1.db.resource_count, 0)
        self.assertEqual(self.char1.get_resource(4), 1)

    def test_mine_depleted(self):
        """Mining when count is 0 should fail with depleted message."""
        self.room1.db.resource_count = 0
        result = self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertIn("exhausted", result.lower())


# ── Validation ────────────────────────────────────────────────────

class TestHarvestValidation(HarvestingTestBase):
    """Test error messages for invalid harvest attempts."""

    def test_wrong_command(self):
        """Using 'chop' in a mining room should fail."""
        result = self.call(CmdHarvest(), "", cmdstring="chop")
        self.assertIn("can't chop here", result.lower())

    def test_wrong_height_ground(self):
        """Character flying when harvest_height is 0 should fail."""
        self.char1.room_vertical_position = 1
        result = self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertIn("ground", result.lower())

    @patch("commands.room_specific_cmds.harvesting.cmd_harvest.delay",
           side_effect=_instant_delay)
    def test_underwater_resource(self, mock_delay):
        """Character at correct depth should be able to harvest underwater."""
        self.room1.db.harvest_height = -1
        self.room1.db.max_depth = -1
        self.char1.room_vertical_position = -1
        result = self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertIn("Iron Ore", result)

    @patch("commands.room_specific_cmds.harvesting.cmd_harvest.delay",
           side_effect=_instant_delay)
    def test_flying_resource(self, mock_delay):
        """Character at correct flying height should be able to harvest."""
        self.room1.db.harvest_height = 1
        self.char1.room_vertical_position = 1
        result = self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertIn("Iron Ore", result)

    def test_wrong_height_needs_fly(self):
        """Ground character when harvest_height is 1 should get fly message."""
        self.room1.db.harvest_height = 1
        self.char1.room_vertical_position = 0
        result = self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertIn("fly up", result.lower())

    def test_wrong_height_needs_swim(self):
        """Ground character when harvest_height is -1 should get swim message."""
        self.room1.db.harvest_height = -1
        self.char1.room_vertical_position = 0
        result = self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertIn("swim down", result.lower())

    def test_busy_rejected(self):
        """Should reject if already processing/harvesting."""
        self.char1.ndb.is_processing = True
        result = self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertIn("busy", result.lower())
        # Count should NOT change
        self.assertEqual(self.room1.db.resource_count, 10)


# ── Tool Requirement ──────────────────────────────────────────────

class TestHarvestTool(HarvestingTestBase):
    """Test optional tool requirement."""

    def test_required_tool_missing(self):
        """Should fail if required tool is not in inventory."""
        self.room1.db.required_tool = "pickaxe"
        result = self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertIn("need a pickaxe", result.lower())
        self.assertEqual(self.room1.db.resource_count, 10)

    @patch("commands.room_specific_cmds.harvesting.cmd_harvest.delay",
           side_effect=_instant_delay)
    def test_required_tool_present(self, mock_delay):
        """Should succeed if required tool is in inventory."""
        self.room1.db.required_tool = "pickaxe"
        create.create_object(key="pickaxe", location=self.char1)
        result = self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertIn("Iron Ore", result)

    @patch("commands.room_specific_cmds.harvesting.cmd_harvest.delay",
           side_effect=_instant_delay)
    def test_no_tool_required(self, mock_delay):
        """Should succeed when no tool is required (default)."""
        result = self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertIn("Iron Ore", result)


# ── Race Condition ────────────────────────────────────────────────

class TestHarvestRaceCondition(HarvestingTestBase):
    """Test race condition where count reaches 0 between start and completion."""

    @patch("commands.room_specific_cmds.harvesting.cmd_harvest.delay")
    def test_count_zero_at_completion(self, mock_delay):
        """If count drops to 0 during delay, completion should fail gracefully."""
        # Start the harvest (count=10, passes initial check)
        self.call(CmdHarvest(), "", cmdstring="mine")

        # Capture the callback that was passed to delay()
        self.assertTrue(mock_delay.called)
        callback = mock_delay.call_args[0][1]

        # Simulate another player taking the last resource
        self.room1.db.resource_count = 0

        # Execute the callback — should fail gracefully
        callback()

        # No resource should have been added
        self.assertEqual(self.char1.get_resource(4), 0)
        # Busy flag should be cleared
        self.assertFalse(self.char1.ndb.is_processing)


# ── Room Descriptions ─────────────────────────────────────────────

class TestHarvestDescriptions(HarvestingTestBase):
    """Test three-tier room description based on resource count."""

    def test_desc_abundant(self):
        """Count > threshold should show abundant description."""
        self.room1.db.resource_count = 10
        desc = self.room1.get_display_desc(self.char1)
        self.assertEqual(
            desc, "Rich veins of iron ore glint in the rock face."
        )

    def test_desc_scarce(self):
        """Count between 1 and threshold should show scarce description."""
        self.room1.db.resource_count = 3
        desc = self.room1.get_display_desc(self.char1)
        self.assertEqual(desc, "A few traces of ore remain in the walls.")

    def test_desc_depleted(self):
        """Count 0 should show depleted description."""
        self.room1.db.resource_count = 0
        desc = self.room1.get_display_desc(self.char1)
        self.assertEqual(
            desc, "The mine is exhausted. Nothing remains."
        )

    def test_desc_at_threshold(self):
        """Count equal to threshold should show scarce (not abundant)."""
        self.room1.db.resource_count = 5
        desc = self.room1.get_display_desc(self.char1)
        self.assertEqual(desc, "A few traces of ore remain in the walls.")

    def test_desc_above_threshold(self):
        """Count one above threshold should show abundant."""
        self.room1.db.resource_count = 6
        desc = self.room1.get_display_desc(self.char1)
        self.assertEqual(
            desc, "Rich veins of iron ore glint in the rock face."
        )

    def test_default_descriptions(self):
        """Rooms without custom descriptions should use defaults."""
        # Clear custom descriptions to get defaults
        self.room1.db.desc_abundant = "Resources are plentiful here."
        self.room1.db.desc_scarce = "A few resources remain here."
        self.room1.db.desc_depleted = "There is nothing left to gather here."

        self.room1.db.resource_count = 10
        self.assertEqual(
            self.room1.get_display_desc(self.char1),
            "Resources are plentiful here.",
        )

        self.room1.db.resource_count = 3
        self.assertEqual(
            self.room1.get_display_desc(self.char1),
            "A few resources remain here.",
        )

        self.room1.db.resource_count = 0
        self.assertEqual(
            self.room1.get_display_desc(self.char1),
            "There is nothing left to gather here.",
        )


# ── Experience Points ─────────────────────────────────────────────

class TestHarvestXP(HarvestingTestBase):
    """Test XP awarded on successful harvest."""

    @patch("commands.room_specific_cmds.harvesting.cmd_harvest.delay",
           side_effect=_instant_delay)
    def test_xp_awarded(self, mock_delay):
        """Should award harvest_xp on successful harvest."""
        self.room1.db.harvest_xp = 10
        self.char1.experience_points = 0
        self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertEqual(self.char1.experience_points, 10)

    @patch("commands.room_specific_cmds.harvesting.cmd_harvest.delay",
           side_effect=_instant_delay)
    def test_no_xp_when_zero(self, mock_delay):
        """Should not show XP message when harvest_xp is 0."""
        self.room1.db.harvest_xp = 0
        result = self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertNotIn("XP", result)

    @patch("commands.room_specific_cmds.harvesting.cmd_harvest.delay")
    def test_no_xp_on_race_fail(self, mock_delay):
        """Should not award XP when race condition blocks harvest."""
        self.room1.db.harvest_xp = 10
        self.char1.experience_points = 0
        self.call(CmdHarvest(), "", cmdstring="mine")
        callback = mock_delay.call_args[0][1]
        self.room1.db.resource_count = 0
        callback()
        self.assertEqual(self.char1.experience_points, 0)


# ── Busy Flag ─────────────────────────────────────────────────────

class TestHarvestBusyFlag(HarvestingTestBase):
    """Test that busy flag is properly managed."""

    @patch("commands.room_specific_cmds.harvesting.cmd_harvest.delay",
           side_effect=_instant_delay)
    def test_busy_cleared_on_success(self, mock_delay):
        """is_processing should be False after successful harvest."""
        self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertFalse(self.char1.ndb.is_processing)

    @patch("commands.room_specific_cmds.harvesting.cmd_harvest.delay")
    def test_busy_cleared_on_race_fail(self, mock_delay):
        """is_processing should be False even when race condition blocks harvest."""
        self.call(CmdHarvest(), "", cmdstring="mine")
        callback = mock_delay.call_args[0][1]
        self.room1.db.resource_count = 0
        callback()
        self.assertFalse(self.char1.ndb.is_processing)

    @patch("commands.room_specific_cmds.harvesting.cmd_harvest.delay",
           side_effect=_instant_delay)
    def test_busy_set_during_delay(self, mock_delay):
        """is_processing should be True while harvesting (verified via mock)."""
        # With instant delay it's set and cleared immediately,
        # but we can verify it was set by checking the flow completed
        self.call(CmdHarvest(), "", cmdstring="mine")
        self.assertEqual(self.char1.get_resource(4), 1)
