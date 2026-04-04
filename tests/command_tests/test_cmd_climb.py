"""
Tests for CmdClimb — climb up/down climbable fixtures.

evennia test --settings settings tests.command_tests.test_cmd_climb
"""

from unittest.mock import patch, PropertyMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_climb import CmdClimb


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdClimbBasic(EvenniaCommandTest):
    """Basic climb up/down with a climbable fixture."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.room_vertical_position = 0
        self.fixture = create.create_object(
            "typeclasses.world_objects.climbable_fixture.ClimbableFixture",
            key="a drainpipe",
            location=self.room1,
        )
        self.fixture.climbable_heights = {0, 1}
        self.fixture.climb_dc = 0
        self.fixture.climb_up_msg = "You haul yourself up the drainpipe."
        self.fixture.climb_down_msg = "You shinny down the drainpipe."

    def test_climb_up(self):
        """climb up drainpipe should move to height 1."""
        result = self.call(CmdClimb(), "up drainpipe")
        self.assertIn("haul yourself up", result)
        self.assertEqual(self.char1.room_vertical_position, 1)

    def test_climb_down(self):
        """climb down drainpipe from height 1 should move to 0."""
        self.char1.room_vertical_position = 1
        result = self.call(CmdClimb(), "down drainpipe")
        self.assertIn("shinny down", result)
        self.assertEqual(self.char1.room_vertical_position, 0)

    def test_climb_up_at_max(self):
        """climb up at max supported height should error."""
        self.char1.room_vertical_position = 1
        result = self.call(CmdClimb(), "up drainpipe")
        self.assertIn("can't climb any higher", result)
        self.assertEqual(self.char1.room_vertical_position, 1)

    def test_climb_down_at_ground(self):
        """climb down at height 0 should error."""
        result = self.call(CmdClimb(), "down drainpipe")
        self.assertIn("can't climb any lower", result)
        self.assertEqual(self.char1.room_vertical_position, 0)

    def test_auto_target_single_fixture(self):
        """climb up with no target and one fixture should auto-target."""
        result = self.call(CmdClimb(), "up")
        self.assertIn("haul yourself up", result)
        self.assertEqual(self.char1.room_vertical_position, 1)

    def test_no_direction(self):
        """climb with no direction should show usage."""
        result = self.call(CmdClimb(), "")
        self.assertIn("Usage", result)

    def test_nothing_climbable(self):
        """climb in room with no climbable fixture should error."""
        self.fixture.delete()
        result = self.call(CmdClimb(), "up")
        self.assertIn("nothing climbable", result)

    def test_climb_non_climbable_object(self):
        """climb up on a non-climbable object should error."""
        result = self.call(CmdClimb(), "up Char")
        self.assertIn("can't climb", result)

    def test_climb_nonexistent(self):
        """climb up nonexistent target should error."""
        result = self.call(CmdClimb(), "up banana")
        self.assertIn("don't see", result)


class TestCmdClimbGuards(EvenniaCommandTest):
    """Climb should be blocked by position and encumbrance."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.room_vertical_position = 0
        self.fixture = create.create_object(
            "typeclasses.world_objects.climbable_fixture.ClimbableFixture",
            key="a ladder",
            location=self.room1,
        )
        self.fixture.climbable_heights = {0, 1}
        self.fixture.climb_dc = 0

    def test_climb_while_sleeping(self):
        """Sleeping characters can't climb."""
        self.char1.position = "sleeping"
        result = self.call(CmdClimb(), "up ladder")
        self.assertIn("asleep", result)

    def test_climb_while_encumbered(self):
        """Encumbered characters can't climb."""
        with patch.object(
            type(self.char1), "is_encumbered", new_callable=PropertyMock, return_value=True,
        ):
            result = self.call(CmdClimb(), "up ladder")
            self.assertIn("too much", result)


class TestCmdClimbSkillCheck(EvenniaCommandTest):
    """Climb with climb_dc > 0 should require a DEX check."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.room_vertical_position = 0
        self.char1.dexterity = 10  # +0 modifier
        self.fixture = create.create_object(
            "typeclasses.world_objects.climbable_fixture.ClimbableFixture",
            key="a rope",
            location=self.room1,
        )
        self.fixture.climbable_heights = {0, 1}
        self.fixture.climb_dc = 15
        self.fixture.climb_fail_msg = "The rope slips through your hands!"

    @patch("commands.all_char_cmds.cmd_climb.dice")
    def test_climb_check_pass(self, mock_dice):
        """Passing the DC should succeed."""
        mock_dice.roll_with_advantage_or_disadvantage.return_value = 16
        self.call(CmdClimb(), "up rope")
        self.assertEqual(self.char1.room_vertical_position, 1)

    @patch("commands.all_char_cmds.cmd_climb.dice")
    def test_climb_check_fail(self, mock_dice):
        """Failing the DC should stay at ground level."""
        mock_dice.roll_with_advantage_or_disadvantage.return_value = 5
        result = self.call(CmdClimb(), "up rope")
        self.assertIn("rope slips", result)
        self.assertEqual(self.char1.room_vertical_position, 0)
