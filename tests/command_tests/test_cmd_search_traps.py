"""
Tests for CmdSearch — trap detection extension.

Tests that the search command finds undetected traps on objects,
exits, and rooms (pressure plates).

evennia test --settings settings tests.command_tests.test_cmd_search_traps
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_search import CmdSearch


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

_ROOM = "typeclasses.terrain.rooms.room_base.RoomBase"
_CHAR = "typeclasses.actors.character.FCMCharacter"


class TestCmdSearchTraps(EvenniaCommandTest):

    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    # ── Trap detection on objects ──

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
           return_value=20)
    def test_search_finds_trapped_chest(self, mock_roll):
        """Search detects a trap on a chest."""
        chest = create.create_object(
            "typeclasses.world_objects.trap_chest.TrapChest",
            key="ornate chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_trapped = True
        chest.trap_armed = True
        chest.trap_detected = False
        chest.trap_find_dc = 5
        chest.trap_description = "a poison dart trap"

        # detect_trap sends room msg first via msg_contents
        self.call(CmdSearch(), "", "You notice a poison dart trap")
        self.assertTrue(chest.trap_detected)

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
           return_value=1)
    def test_search_misses_high_dc_trap(self, mock_roll):
        """Low roll misses a high-DC trap."""
        chest = create.create_object(
            "typeclasses.world_objects.trap_chest.TrapChest",
            key="chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_trapped = True
        chest.trap_armed = True
        chest.trap_detected = False
        chest.trap_find_dc = 30

        self.call(CmdSearch(), "", "You search but find nothing unusual.")
        self.assertFalse(chest.trap_detected)

    def test_search_skips_already_detected_trap(self):
        """Already-detected traps aren't searched again."""
        chest = create.create_object(
            "typeclasses.world_objects.trap_chest.TrapChest",
            key="chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_trapped = True
        chest.trap_armed = True
        chest.trap_detected = True

        self.call(CmdSearch(), "", "You search but find nothing unusual.")

    def test_search_skips_disarmed_trap(self):
        """Disarmed traps aren't searched for."""
        chest = create.create_object(
            "typeclasses.world_objects.trap_chest.TrapChest",
            key="chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_trapped = True
        chest.trap_armed = False
        chest.trap_detected = False

        self.call(CmdSearch(), "", "You search but find nothing unusual.")

    # ── Trap detection on exits ──

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
           return_value=20)
    def test_search_finds_trapped_exit(self, mock_roll):
        """Search detects a tripwire on an exit."""
        tripwire = create.create_object(
            "typeclasses.terrain.exits.exit_tripwire.TripwireExit",
            key="north",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        tripwire.is_trapped = True
        tripwire.trap_armed = True
        tripwire.trap_detected = False
        tripwire.trap_find_dc = 5
        tripwire.trap_description = "a tripwire"

        self.call(CmdSearch(), "", "You notice a tripwire")
        self.assertTrue(tripwire.trap_detected)

    # ── Trap detection on rooms (pressure plates) ──

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
           return_value=20)
    def test_search_finds_pressure_plate(self, mock_roll):
        """Search detects a pressure plate in the room."""
        plate_room = create.create_object(
            "typeclasses.terrain.rooms.room_pressure_plate.PressurePlateRoom",
            key="narrow passage",
            nohome=True,
        )
        plate_room.is_trapped = True
        plate_room.trap_armed = True
        plate_room.trap_detected = False
        plate_room.trap_find_dc = 15  # Above passive (10) but below search roll (20)
        plate_room.trap_description = "a pressure plate"

        self.char1.move_to(plate_room, quiet=True)

        self.call(CmdSearch(), "", "You notice a pressure plate")
        self.assertTrue(plate_room.trap_detected)


class TestPassiveTrapDetection(EvenniaCommandTest):
    """Tests for passive perception detecting traps on room entry."""

    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_passive_detects_low_dc_trap(self):
        """Passive perception (10 + bonus) detects traps on entry."""
        plate_room = create.create_object(
            "typeclasses.terrain.rooms.room_pressure_plate.PressurePlateRoom",
            key="passage",
            nohome=True,
        )
        plate_room.is_trapped = True
        plate_room.trap_armed = True
        plate_room.trap_detected = False
        plate_room.trap_find_dc = 5  # Very easy — passive 10 beats it

        self.char1.move_to(plate_room, quiet=True)
        self.assertTrue(plate_room.trap_detected)

    def test_passive_misses_high_dc_trap(self):
        """Passive perception can't detect high-DC traps."""
        plate_room = create.create_object(
            "typeclasses.terrain.rooms.room_pressure_plate.PressurePlateRoom",
            key="passage",
            nohome=True,
        )
        plate_room.is_trapped = True
        plate_room.trap_armed = True
        plate_room.trap_detected = False
        plate_room.trap_find_dc = 25  # Too hard for passive

        self.char1.move_to(plate_room, quiet=True)
        self.assertFalse(plate_room.trap_detected)

    def test_passive_detects_trap_on_exit(self):
        """Passive perception detects a tripwire exit in the destination room."""
        dest_room = create.create_object(
            _ROOM, key="dest room", nohome=True,
        )
        tripwire = create.create_object(
            "typeclasses.terrain.exits.exit_tripwire.TripwireExit",
            key="north",
            location=dest_room,
            destination=self.room1,
            nohome=True,
        )
        tripwire.is_trapped = True
        tripwire.trap_armed = True
        tripwire.trap_detected = False
        tripwire.trap_find_dc = 5

        self.char1.move_to(dest_room, quiet=True)
        self.assertTrue(tripwire.trap_detected)
