"""
Tests for posture commands (sit, rest, sleep, stand, wake).

evennia test --settings settings tests.command_tests.test_cmd_posture
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_posture import (
    CmdSit, CmdRest, CmdSleep, CmdStand, CmdWake,
)


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestPostureCommands(EvenniaCommandTest):
    """Test posture commands and position changes."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    # ── Basic position changes ────────────────────────────────────────

    def test_sit(self):
        """sit command sets position to sitting."""
        result = self.call(CmdSit(), "")
        self.assertIn("sit down", result)
        self.assertEqual(self.char1.position, "sitting")

    def test_rest(self):
        """rest command sets position to resting."""
        result = self.call(CmdRest(), "")
        self.assertIn("rest", result)
        self.assertEqual(self.char1.position, "resting")

    def test_sleep(self):
        """sleep command sets position to sleeping."""
        result = self.call(CmdSleep(), "")
        self.assertIn("sleep", result)
        self.assertEqual(self.char1.position, "sleeping")

    def test_stand(self):
        """stand command sets position to standing."""
        self.char1.position = "sitting"
        result = self.call(CmdStand(), "")
        self.assertIn("stand up", result)
        self.assertEqual(self.char1.position, "standing")

    def test_wake(self):
        """wake command sets position to standing from sleeping."""
        self.char1.position = "sleeping"
        result = self.call(CmdWake(), "")
        self.assertIn("wake up", result)
        self.assertEqual(self.char1.position, "standing")

    # ── Guards ────────────────────────────────────────────────────────

    def test_already_in_position(self):
        """Can't change to the same position."""
        self.char1.position = "sitting"
        result = self.call(CmdSit(), "")
        self.assertIn("already", result)

    def test_wake_when_not_sleeping(self):
        """wake when not sleeping shows error."""
        result = self.call(CmdWake(), "")
        self.assertIn("aren't asleep", result)

    def test_cant_sit_while_fighting(self):
        """Can't sit down while fighting."""
        self.char1.position = "fighting"
        result = self.call(CmdSit(), "")
        self.assertIn("fighting", result)

    def test_cant_rest_while_fighting(self):
        """Can't rest while fighting."""
        self.char1.position = "fighting"
        result = self.call(CmdRest(), "")
        self.assertIn("fighting", result)

    def test_cant_sleep_while_fighting(self):
        """Can't sleep while fighting."""
        self.char1.position = "fighting"
        result = self.call(CmdSleep(), "")
        self.assertIn("fighting", result)

    # ── Room description integration ──────────────────────────────────

    def test_room_desc_standing_default(self):
        """Default standing shows 'stands here'."""
        desc = self.char1.get_room_description()
        self.assertIn("stands here", desc)

    def test_room_desc_sitting(self):
        """Sitting shows 'is sitting here'."""
        self.char1.position = "sitting"
        desc = self.char1.get_room_description()
        self.assertIn("sitting here", desc)

    def test_room_desc_resting(self):
        """Resting shows 'is resting here'."""
        self.char1.position = "resting"
        desc = self.char1.get_room_description()
        self.assertIn("resting here", desc)

    def test_room_desc_sleeping(self):
        """Sleeping shows 'is sleeping here'."""
        self.char1.position = "sleeping"
        desc = self.char1.get_room_description()
        self.assertIn("sleeping here", desc)

    # ── Regen multipliers ─────────────────────────────────────────────

    def test_regen_multiplier_standing(self):
        """Standing has 1x regen."""
        self.assertEqual(self.char1.REGEN_MULTIPLIERS["standing"], 1)

    def test_regen_multiplier_resting(self):
        """Resting has 2x regen."""
        self.assertEqual(self.char1.REGEN_MULTIPLIERS["resting"], 2)

    def test_regen_multiplier_sleeping(self):
        """Sleeping has 3x regen."""
        self.assertEqual(self.char1.REGEN_MULTIPLIERS["sleeping"], 3)

    def test_regen_multiplier_fighting(self):
        """Fighting has 0x regen."""
        self.assertEqual(self.char1.REGEN_MULTIPLIERS["fighting"], 0)

    # ── Sleep policy ─────────────────────────────────────────────────

    def test_sleep_blocked_in_no_sleep_room(self):
        """Can't sleep in a room tagged sleep_policy: none."""
        self.room1.set_sleep_policy("none")
        result = self.call(CmdSleep(), "")
        self.assertIn("can't sleep here", result)
        self.assertEqual(self.char1.position, "standing")

    def test_sleep_allowed_in_super_room(self):
        """Can sleep in a room tagged sleep_policy: super."""
        self.room1.set_sleep_policy("super")
        result = self.call(CmdSleep(), "")
        self.assertIn("sleep", result)
        self.assertEqual(self.char1.position, "sleeping")
