"""
Tests for CmdClimb — climb up/down climbable fixtures.

evennia test --settings settings tests.command_tests.test_cmd_climb
"""

from unittest.mock import MagicMock, patch, PropertyMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_climb import CmdClimb
from enums.condition import Condition


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdClimbBasic(EvenniaCommandTest):
    """Basic climb up/down with a climbable fixture."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
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
        self.assertIn("dreams", result)

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
        self.room1.always_lit = True
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


class TestCmdClimbSightless(EvenniaCommandTest):
    """
    Climbing is done by touch, so darkness and blindness do not prevent
    it — they only change how it reads.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
        self.char1.room_vertical_position = 0
        self.fixture = self._fixture("a drainpipe")

    def _fixture(self, key):
        fixture = create.create_object(
            "typeclasses.world_objects.climbable_fixture.ClimbableFixture",
            key=key,
            location=self.room1,
        )
        fixture.climbable_heights = {0, 1}
        fixture.climb_dc = 0
        fixture.climb_up_msg = "You haul yourself up."
        return fixture

    def _darken(self):
        # has_natural_light is a read-only property derived from this.
        self.room1.always_lit = False
        self.room1.natural_light = False

    def test_a_dark_room_no_longer_blocks_the_climb(self):
        self._darken()
        self.call(CmdClimb(), "up")
        self.assertEqual(self.char1.room_vertical_position, 1)

    def test_a_blinded_climber_still_climbs(self):
        self.char1.add_condition(Condition.BLINDED)
        self.call(CmdClimb(), "up")
        self.assertEqual(self.char1.room_vertical_position, 1)

    def test_the_sole_climbable_is_found_by_touch(self):
        self._darken()
        result = self.call(CmdClimb(), "up")
        self.assertIn("grope about until you find", result)

    def test_a_sighted_climber_gets_no_groping_text(self):
        result = self.call(CmdClimb(), "up")
        self.assertNotIn("grope about", result)

    def test_several_climbables_cannot_be_told_apart(self):
        self._darken()
        self._fixture("a ladder")
        result = self.call(CmdClimb(), "up")
        self.assertIn("can't tell them apart", result)
        self.assertEqual(self.char1.room_vertical_position, 0)

    def test_the_sightless_prompt_does_not_list_what_is_there(self):
        """Naming them would hand over what the climber cannot see."""
        self._darken()
        self._fixture("a ladder")
        result = self.call(CmdClimb(), "up")
        self.assertNotIn("drainpipe", result)
        self.assertNotIn("ladder", result)

    def test_a_sighted_climber_is_still_offered_the_list(self):
        self._fixture("a ladder")
        result = self.call(CmdClimb(), "up")
        self.assertIn("drainpipe", result)
        self.assertIn("ladder", result)

    def test_naming_a_target_still_works_unseen(self):
        self._darken()
        self._fixture("a ladder")
        self.call(CmdClimb(), "up drainpipe")
        self.assertEqual(self.char1.room_vertical_position, 1)


class TestCmdClimbRoomMessages(EvenniaCommandTest):
    """What the rest of the room is told, and whose view it reflects."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
        self.char1.room_vertical_position = 0
        self.char2.location = self.room1
        self.char2.msg = MagicMock()
        self.fixture = create.create_object(
            "typeclasses.world_objects.climbable_fixture.ClimbableFixture",
            key="a drainpipe",
            location=self.room1,
        )
        self.fixture.climbable_heights = {0, 1}
        self.fixture.climb_dc = 0

    def _heard(self):
        said = []
        for args, kwargs in self.char2.msg.call_args_list:
            payload = kwargs.get("text", args[0] if args else None)
            if isinstance(payload, tuple):
                payload = payload[0]
            if payload:
                said.append(str(payload))
        return " ".join(said)

    def test_a_watcher_is_told_who_climbed_what(self):
        self.call(CmdClimb(), "up drainpipe")
        heard = self._heard()
        self.assertIn(self.char1.key, heard)
        self.assertIn("drainpipe", heard)

    def test_a_blind_watcher_gets_neither_name(self):
        """The message resolves per recipient, so it must redact."""
        self.char2.add_condition(Condition.BLINDED)
        self.call(CmdClimb(), "up drainpipe")
        heard = self._heard()
        self.assertNotIn(self.char1.key, heard)
        self.assertIn("Someone", heard)

    @patch("commands.all_char_cmds.cmd_climb.dice")
    def test_a_blind_watcher_gets_neither_name_on_failure(self, mock_dice):
        self.fixture.climb_dc = 15
        mock_dice.roll_with_advantage_or_disadvantage.return_value = 1
        self.char2.add_condition(Condition.BLINDED)
        self.call(CmdClimb(), "up drainpipe")
        heard = self._heard()
        self.assertNotIn(self.char1.key, heard)
        self.assertIn("Someone", heard)
