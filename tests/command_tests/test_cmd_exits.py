"""
Tests for the exits command.

evennia test --settings settings tests.command_tests.test_cmd_exits
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_exits import CmdExits


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdExits(EvenniaCommandTest):
    """Test the exits command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
        self.room2 = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Town Square",
            nohome=True,
        )
        self.room2.always_lit = True

    # ── No exits ──────────────────────────────────────────────────────

    def test_no_exits(self):
        """Room with no exits shows appropriate message."""
        # Remove default exits from test setup
        for ex in self.room1.contents_get(content_type="exit"):
            ex.delete()
        result = self.call(CmdExits(), "")
        self.assertIn("no obvious exits", result)

    # ── Basic exit display ────────────────────────────────────────────

    def test_basic_exit_display(self):
        """Exit with direction shows direction and destination."""
        ex = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        ex.set_direction("north")
        result = self.call(CmdExits(), "")
        self.assertIn("Obvious exits", result)
        self.assertIn("North", result)
        self.assertIn("Town Square", result)

    # ── Door states ───────────────────────────────────────────────────

    def test_closed_door_shown(self):
        """Closed doors appear in exits list with (closed) tag."""
        door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="a heavy oak door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        door.set_direction("south")
        door.is_open = False
        result = self.call(CmdExits(), "")
        self.assertIn("closed", result)

    def test_locked_door_shown(self):
        """Locked doors appear in exits list with (locked) tag."""
        door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="a heavy oak door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        door.set_direction("south")
        door.is_open = False
        door.is_locked = True
        result = self.call(CmdExits(), "")
        self.assertIn("locked", result)

    def test_open_door_shows_open_tag(self):
        """Open doors show (open) state tag."""
        door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="a heavy oak door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        door.set_direction("south")
        door.is_open = True
        result = self.call(CmdExits(), "")
        self.assertIn("open", result)
        self.assertNotIn("closed", result)
        self.assertNotIn("locked", result)

    # ── Description display ───────────────────────────────────────────

    def test_door_description_shown(self):
        """Door exit shows its description alongside the state tag."""
        door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="a wooden door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        door.set_direction("north")
        door.db.desc = "A well-worn door leads north."
        door.is_open = True
        result = self.call(CmdExits(), "")
        self.assertIn("well-worn door", result)

    def test_non_door_exit_shows_destination_not_desc(self):
        """Non-door exits show destination name, not description."""
        ex = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        ex.set_direction("north")
        ex.db.desc = "A well-worn path leads north."
        result = self.call(CmdExits(), "")
        self.assertIn("Town Square", result)
        self.assertNotIn("well-worn path", result)

    def test_default_exit_desc_hidden(self):
        """The default 'This is an exit.' should not appear."""
        ex = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        ex.set_direction("north")
        result = self.call(CmdExits(), "")
        self.assertNotIn("This is an exit", result)

    # ── Alias ─────────────────────────────────────────────────────────

    def test_ex_alias(self):
        """'ex' alias should work."""
        ex = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        ex.set_direction("north")
        result = self.call(CmdExits(), "", cmdstring="ex")
        self.assertIn("Obvious exits", result)

    # ── Direction sort order ──────────────────────────────────────────

    # ── Exit return_appearance (look <exit>) ────────────────────────

    def test_look_exit_no_desc_shows_destination(self):
        """Looking at an exit with no db.desc shows destination name."""
        ex = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        ex.set_direction("north")
        result = ex.return_appearance(self.char1)
        self.assertIn("Town Square", result)
        self.assertNotIn("This is an exit", result)

    def test_look_exit_no_desc_shows_room_preview(self):
        """Looking at an exit with no db.desc shows first sentence of dest room."""
        self.room2.db.desc = "A bustling market square. Vendors hawk their wares."
        ex = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        ex.set_direction("north")
        result = ex.return_appearance(self.char1)
        self.assertIn("A bustling market square.", result)
        self.assertNotIn("Vendors", result)

    def test_look_exit_custom_desc_used(self):
        """Looking at an exit with custom db.desc uses Evennia's normal rendering."""
        ex = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        ex.set_direction("north")
        ex.db.desc = "A well-worn path leads north."
        result = ex.return_appearance(self.char1)
        self.assertIn("well-worn path", result)

    # ── Direction sort order ──────────────────────────────────────

    def test_direction_sort_order(self):
        """Exits should be sorted by canonical direction order."""
        room3 = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Market",
            nohome=True,
        )
        ex_s = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="south",
            location=self.room1,
            destination=room3,
            nohome=True,
        )
        ex_s.set_direction("south")
        ex_n = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        ex_n.set_direction("north")
        result = self.call(CmdExits(), "")
        north_idx = result.index("North")
        south_idx = result.index("South")
        self.assertLess(north_idx, south_idx)


class TestCmdExitsSightAndSize(EvenniaCommandTest):
    """Reading the exits needs eyes; the list only offers ways you fit."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
        self.dest = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Town Square",
            nohome=True,
        )
        for ex in self.room1.contents_get(content_type="exit"):
            ex.delete()
        self.gate = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.dest,
            nohome=True,
        )
        self.gate.direction = "north"

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False

    # ── Sight ────────────────────────────────────────────────────

    def test_a_dark_room_shows_no_exits(self):
        self._darken()
        self.call(CmdExits(), "", "It's too dark to see any exits.")

    def test_a_blinded_reader_is_refused_in_a_lit_room(self):
        """is_dark alone never asked this — a blind character read the list."""
        from enums.condition import Condition

        self.char1.add_condition(Condition.BLINDED)
        self.call(CmdExits(), "", "It's too dark to see any exits.")

    def test_darkvision_reads_the_exits_in_the_dark(self):
        from enums.condition import Condition

        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        result = self.call(CmdExits(), "")
        self.assertNotIn("too dark", result)

    def test_a_blinded_reader_is_refused_even_with_darkvision(self):
        from enums.condition import Condition

        self.char1.add_condition(Condition.DARKVISION)
        self.char1.add_condition(Condition.BLINDED)
        self.call(CmdExits(), "", "It's too dark to see any exits.")

    # ── Size ─────────────────────────────────────────────────────

    def test_an_exit_you_fit_through_is_listed(self):
        from enums.size import Size

        self.gate.max_size = Size.LARGE.value
        self.char1.size = Size.MEDIUM.value
        result = self.call(CmdExits(), "")
        self.assertIn("North", result)

    def test_an_exit_too_small_is_listed_and_labelled(self):
        """Labelled, not hidden — the same way a locked door is."""
        from enums.size import Size

        self.gate.max_size = Size.SMALL.value
        self.char1.size = Size.HUGE.value
        result = self.call(CmdExits(), "")
        self.assertIn("North", result)
        self.assertIn("too small", result)

    def test_an_exit_you_fit_through_carries_no_label(self):
        from enums.size import Size

        self.gate.max_size = Size.LARGE.value
        self.char1.size = Size.MEDIUM.value
        result = self.call(CmdExits(), "")
        self.assertNotIn("too small", result)

    def test_an_exit_with_no_size_limit_admits_anyone(self):
        from enums.size import Size

        self.char1.size = Size.GARGANTUAN.value
        result = self.call(CmdExits(), "")
        self.assertIn("North", result)
