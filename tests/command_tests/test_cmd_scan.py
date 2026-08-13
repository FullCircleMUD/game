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

    def _goblin_beyond(self):
        create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin",
            location=self.north_room,
            nohome=True,
        )

    # Open and closed are covered above. Lock state is not a visibility
    # mechanic, and open-and-locked is a data anomaly lock() cannot produce,
    # so the only combination left worth pinning is the real one.

    def test_closed_and_locked_door_is_not_scannable(self):
        """Blocked because it is shut. Locking adds nothing to the sight line.

        A lock governs passage, not sight — the closed state is doing all the
        work here, and this exists to say so.
        """
        self.door.is_open = False
        self.door.is_locked = True
        self._goblin_beyond()
        self.assertIn("no one nearby", self.call(CmdScan(), ""))

    def test_hidden_door_blocks_scan(self):
        """An undiscovered door does not leak what lies beyond it.

        Scanning past a door the character cannot perceive would report who
        is through a passage they do not know exists.
        """
        self.door.is_open = True
        self.door.is_hidden = True
        create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin",
            location=self.north_room,
            nohome=True,
        )
        result = self.call(CmdScan(), "")
        self.assertIn("no one nearby", result)

    def test_discovered_hidden_door_allows_scan(self):
        """Once found, it is an ordinary open doorway."""
        self.door.is_open = True
        self.door.is_hidden = True
        self.door.discover(self.char1)
        create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin",
            location=self.north_room,
            nohome=True,
        )
        result = self.call(CmdScan(), "")
        self.assertIn("North", result)

    def test_traverse_locked_exit_is_still_scannable(self):
        """A sight line is not a route.

        You can see down a corridor you are not permitted to walk into, so a
        traverse lock must not block scanning — only something that actually
        obstructs sight does.
        """
        self.door.is_open = True
        self.door.locks.add("traverse:false()")
        create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin",
            location=self.north_room,
            nohome=True,
        )
        result = self.call(CmdScan(), "")
        self.assertIn("North", result)


class TestCmdScanDoorsAtDepth(EvenniaCommandTest):
    """Gating applies at every step outward, not just the first.

    The check inside the distance loop is a separate call site from the one
    that admits the first exit, and it decides whether a scan stops partway
    down a corridor. Rooms nearer than the obstruction must still report.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
        for ex in self.room1.contents_get(content_type="exit"):
            ex.delete()

        # room1 --north--> near --north(door)--> far
        self.near = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Near Room", nohome=True,
        )
        self.near.always_lit = True
        self.far = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Far Room", nohome=True,
        )
        self.far.always_lit = True

        first = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north", location=self.room1, destination=self.near, nohome=True,
        )
        first.set_direction("north")

        self.far_door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="north", location=self.near, destination=self.far, nohome=True,
        )
        self.far_door.set_direction("north")

        create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin", location=self.near, nohome=True,
        )
        create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a troll", location=self.far, nohome=True,
        )

    def test_open_door_at_depth_two_scans_both_rooms(self):
        self.far_door.is_open = True
        result = self.call(CmdScan(), "")
        self.assertIn("goblin", result)
        self.assertIn("troll", result)

    def test_closed_door_at_depth_two_stops_the_chain(self):
        """The near room still reports; only what is past the door is lost."""
        self.far_door.is_open = False
        result = self.call(CmdScan(), "")
        self.assertIn("goblin", result)
        self.assertNotIn("troll", result)

    def test_hidden_door_at_depth_two_stops_the_chain(self):
        """Judged from the caller's discovery state, not from the near room.

        The caller is not standing next to this door, so an undiscovered one
        two rooms out conceals what lies beyond it just as it would up close.
        """
        self.far_door.is_open = True
        self.far_door.is_hidden = True
        result = self.call(CmdScan(), "")
        self.assertIn("goblin", result)
        self.assertNotIn("troll", result)

    def test_discovered_door_at_depth_two_scans_through(self):
        self.far_door.is_open = True
        self.far_door.is_hidden = True
        self.far_door.discover(self.char1)
        result = self.call(CmdScan(), "")
        self.assertIn("troll", result)

    def test_corridor_that_bends_stops_the_scan(self):
        """Onward exits are matched on direction, so a turn ends the chain."""
        self.far_door.delete()
        turn = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="east", location=self.near, destination=self.far, nohome=True,
        )
        turn.set_direction("east")
        result = self.call(CmdScan(), "")
        self.assertIn("goblin", result)
        self.assertNotIn("troll", result)


class TestCmdScanSightless(EvenniaCommandTest):
    """
    Scanning is pure sight. Being in an unlit room without darkvision
    and being blinded are the same state, so both refuse it outright.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
        for ex in self.room1.contents_get(content_type="exit"):
            ex.delete()

        self.north_room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="North Room",
            nohome=True,
        )
        self.north_room.always_lit = True
        exit_north = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.north_room,
            nohome=True,
        )
        exit_north.set_direction("north")
        self.mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin",
            location=self.north_room,
            nohome=True,
        )

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False

    def test_a_blinded_character_cannot_scan(self):
        from enums.condition import Condition

        self.char1.add_condition(Condition.BLINDED)
        result = self.call(CmdScan(), "")
        self.assertIn("can't see a thing", result.lower())

    def test_an_unlit_room_stops_the_scan(self):
        """Darkness and blindness are one rule — a lit room next door
        does not rescue a scanner who cannot see."""
        self._darken()
        result = self.call(CmdScan(), "")
        self.assertIn("can't see a thing", result.lower())

    def test_nobody_is_reported_when_refused(self):
        self._darken()
        result = self.call(CmdScan(), "")
        self.assertNotIn("goblin", result)
        self.assertNotIn("North", result)

    def test_darkvision_scans_normally(self):
        from enums.condition import Condition

        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        result = self.call(CmdScan(), "")
        self.assertIn("North", result)

    def test_a_sighted_scanner_is_unaffected(self):
        result = self.call(CmdScan(), "")
        self.assertIn("North", result)
