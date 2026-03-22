"""
Tests for the scan command.

evennia test --settings settings tests.command_tests.test_cmd_scan
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_scan import CmdScan


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdScanNoExits(EvenniaCommandTest):
    """Test scan with no exits."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
        # Remove default exits
        for ex in self.room1.contents_get(content_type="exit"):
            ex.delete()

    def test_no_exits_shows_no_one(self):
        """Scan with no exits says no one nearby."""
        result = self.call(CmdScan(), "")
        self.assertIn("no one nearby", result)


class TestCmdScanBasic(EvenniaCommandTest):
    """Test basic scan functionality."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
        # Remove default exits
        for ex in self.room1.contents_get(content_type="exit"):
            ex.delete()

        # Create adjacent room to the north
        self.north_room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="North Room",
            nohome=True,
        )
        self.north_room.always_lit = True
        self.exit_north = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.north_room,
            nohome=True,
        )
        self.exit_north.set_direction("north")

    def test_empty_adjacent_room(self):
        """Scan shows no one if adjacent rooms are empty."""
        result = self.call(CmdScan(), "")
        self.assertIn("no one nearby", result)

    def test_character_in_adjacent_room(self):
        """Scan shows character in an adjacent room."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin",
            location=self.north_room,
            nohome=True,
        )
        result = self.call(CmdScan(), "")
        self.assertIn("North", result)
        self.assertIn("nearby", result)

    def test_shows_direction_label(self):
        """Scan output includes the direction heading."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a troll",
            location=self.north_room,
            nohome=True,
        )
        result = self.call(CmdScan(), "")
        self.assertIn("North:", result)


class TestCmdScanMultipleRooms(EvenniaCommandTest):
    """Test scanning multiple rooms deep."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
        # Remove default exits
        for ex in self.room1.contents_get(content_type="exit"):
            ex.delete()

        # Create chain: room1 -> north_room -> far_room -> distant_room
        self.north_room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="North Room",
            nohome=True,
        )
        self.north_room.always_lit = True

        self.far_room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Far Room",
            nohome=True,
        )
        self.far_room.always_lit = True

        self.distant_room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Distant Room",
            nohome=True,
        )
        self.distant_room.always_lit = True

        # room1 -> north_room
        ex1 = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.north_room,
            nohome=True,
        )
        ex1.set_direction("north")

        # north_room -> far_room
        ex2 = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.north_room,
            destination=self.far_room,
            nohome=True,
        )
        ex2.set_direction("north")

        # far_room -> distant_room
        ex3 = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.far_room,
            destination=self.distant_room,
            nohome=True,
        )
        ex3.set_direction("north")

    def test_nearby_distance(self):
        """Character 1 room away shows as 'nearby'."""
        create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin",
            location=self.north_room,
            nohome=True,
        )
        result = self.call(CmdScan(), "")
        self.assertIn("nearby", result)

    def test_not_far_off_distance(self):
        """Character 2 rooms away shows as 'not far off'."""
        create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a troll",
            location=self.far_room,
            nohome=True,
        )
        result = self.call(CmdScan(), "")
        self.assertIn("not far off", result)

    def test_far_off_distance(self):
        """Character 3 rooms away shows as 'far off'."""
        create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a dragon",
            location=self.distant_room,
            nohome=True,
        )
        result = self.call(CmdScan(), "")
        self.assertIn("far off", result)


class TestCmdScanVisibility(EvenniaCommandTest):
    """Test scan visibility filtering."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
        # Remove default exits
        for ex in self.room1.contents_get(content_type="exit"):
            ex.delete()

        self.north_room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="North Room",
            nohome=True,
        )
        self.north_room.always_lit = True

        ex = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.north_room,
            nohome=True,
        )
        ex.set_direction("north")

    def test_hidden_character_not_shown(self):
        """Hidden characters are not visible to scan."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a thief",
            location=self.north_room,
            nohome=True,
        )
        mob.add_condition("hidden")
        result = self.call(CmdScan(), "")
        self.assertIn("no one nearby", result)

    def test_dark_room_blocks_scan(self):
        """Dark rooms show 'Too dark' and stop scanning."""
        self.north_room.always_lit = False
        self.north_room.natural_light = False
        create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin",
            location=self.north_room,
            nohome=True,
        )
        result = self.call(CmdScan(), "")
        self.assertIn("Too dark", result)


class TestCmdScanDoors(EvenniaCommandTest):
    """Test that closed doors block scanning."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
        # Remove default exits
        for ex in self.room1.contents_get(content_type="exit"):
            ex.delete()

        self.north_room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="North Room",
            nohome=True,
        )
        self.north_room.always_lit = True

        self.door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="north",
            location=self.room1,
            destination=self.north_room,
            nohome=True,
        )
        self.door.set_direction("north")

    def test_closed_door_blocks_scan(self):
        """Closed doors prevent scanning through them."""
        self.door.is_open = False
        create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin",
            location=self.north_room,
            nohome=True,
        )
        result = self.call(CmdScan(), "")
        self.assertIn("no one nearby", result)

    def test_open_door_allows_scan(self):
        """Open doors allow scanning through them."""
        self.door.is_open = True
        create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin",
            location=self.north_room,
            nohome=True,
        )
        result = self.call(CmdScan(), "")
        self.assertIn("North", result)
