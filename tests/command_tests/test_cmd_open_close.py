"""
Tests for CmdOpen and CmdClose commands.

evennia test --settings settings tests.command_tests.test_cmd_open_close
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_open import CmdOpen
from commands.all_char_cmds.cmd_close import CmdClose


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class OpenCloseTestBase(EvenniaCommandTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.account.attributes.add("wallet_address", WALLET_A)

    def _make_chest(self, is_open=False, is_locked=False):
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="iron chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_open = is_open
        chest.is_locked = is_locked
        return chest


class TestCmdOpen(OpenCloseTestBase):

    def test_open_no_args(self):
        self.call(CmdOpen(), "", "Open what?")

    def test_open_closed_chest(self):
        self._make_chest(is_open=False)
        self.call(CmdOpen(), "iron chest", "You open iron chest.")

    def test_open_already_open(self):
        self._make_chest(is_open=True)
        self.call(CmdOpen(), "iron chest", "iron chest is already open.")

    def test_open_locked_chest(self):
        self._make_chest(is_open=False, is_locked=True)
        self.call(CmdOpen(), "iron chest", "iron chest is locked.")

    def test_open_nonexistent(self):
        self.call(CmdOpen(), "invisible box", "You don't see")


class TestCmdOpenDoor(OpenCloseTestBase):
    """Test opening ExitDoor by door_name alias."""

    def _make_door(self, door_name="door"):
        door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="heavy oak door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        return door

    def test_open_door_by_alias(self):
        """'open door' finds and opens an ExitDoor with door_name='door'."""
        self._make_door()
        self.call(CmdOpen(), "door", "You open heavy oak door.")

    def test_open_door_by_key(self):
        """'open heavy oak door' finds and opens the door by key."""
        self._make_door()
        self.call(CmdOpen(), "heavy oak door", "You open heavy oak door.")

    def test_close_door_by_alias(self):
        """'close door' closes an open ExitDoor."""
        door = self._make_door()
        door.is_open = True
        self.call(CmdClose(), "door", "You close heavy oak door.")


class TestCmdOpenDoorDirectional(OpenCloseTestBase):
    """Test opening/closing doors with directional qualifiers."""

    def setUp(self):
        super().setUp()
        # Two doors in the same room, different directions
        self.door_south = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="heavy oak door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        self.door_south.set_direction("south")

        room3 = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Room3",
            nohome=True,
        )
        self.door_east = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="iron gate",
            location=self.room1,
            destination=room3,
            nohome=True,
        )
        self.door_east.set_direction("east")

    def test_open_door_south(self):
        """'open door south' opens the south door."""
        self.call(CmdOpen(), "door south", "You open heavy oak door.")

    def test_open_door_s(self):
        """'open door s' opens the south door (abbreviation)."""
        self.call(CmdOpen(), "door s", "You open heavy oak door.")

    def test_close_door_south(self):
        """'close door south' closes the south door."""
        self.door_south.is_open = True
        self.call(CmdClose(), "door south", "You close heavy oak door.")

    def test_open_gate_east(self):
        """'open gate east' opens the east gate."""
        self.call(CmdOpen(), "gate east", "You open iron gate.")

    def test_open_gate_e(self):
        """'open gate e' opens the east gate (abbreviation)."""
        self.call(CmdOpen(), "gate e", "You open iron gate.")

    def test_open_south_door(self):
        """'open south door' (direction first) opens the south door."""
        self.call(CmdOpen(), "south door", "You open heavy oak door.")


class TestCmdClose(OpenCloseTestBase):

    def test_close_no_args(self):
        self.call(CmdClose(), "", "Close what?")

    def test_close_open_chest(self):
        self._make_chest(is_open=True)
        self.call(CmdClose(), "iron chest", "You close iron chest.")

    def test_close_already_closed(self):
        self._make_chest(is_open=False)
        self.call(CmdClose(), "iron chest", "iron chest is already closed.")
