"""
Tests for CircleMUD-style room display: template layout, color coding,
brief mode, and auto-exit suppression.

evennia test --settings settings tests.typeclass_tests.test_room_display
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest, EvenniaCommandTest
from evennia.utils import create

from enums.time_of_day import TimeOfDay
from commands.all_char_cmds.cmd_override_look import CmdLook


# ---------------------------------------------------------------------------
#  Room display layout tests (unit-level, via return_appearance)
# ---------------------------------------------------------------------------

class TestRoomDisplayLayout(EvenniaTest):
    """Test the assembled room output from return_appearance."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.db.desc = "A grassy field."
        self.room1.always_lit = True

    # ── No section labels ──────────────────────────────────────────────

    def test_no_old_style_exits_label(self):
        """Room output should not contain old-style standalone 'Exits:' label."""
        result = self.room1.return_appearance(self.char1)
        # The compact "[ Exits: ... ]" format is fine; the old "|cExits:|n" header is not
        for line in result.split("\n"):
            stripped = line.strip()
            if stripped in ("|cExits:|n", "Exits:"):
                self.fail(f"Found old-style exits label: {stripped!r}")

    def test_no_characters_label(self):
        """Room output should not contain 'Characters:' section label."""
        result = self.room1.return_appearance(self.char1)
        self.assertNotIn("Characters:", result)

    def test_no_things_label(self):
        """Room output should not contain 'Things:' section label."""
        result = self.room1.return_appearance(self.char1)
        self.assertNotIn("Things:", result)

    # ── No "None" placeholders ─────────────────────────────────────────

    def test_no_none_in_output(self):
        """Empty sections should be suppressed, not show 'None'."""
        result = self.room1.return_appearance(self.char1)
        self.assertNotIn("None", result)

    # ── Color coding ───────────────────────────────────────────────────

    def test_room_name_is_cyan(self):
        """Room name should be wrapped in cyan color codes."""
        result = self.room1.return_appearance(self.char1)
        self.assertIn("|c", result)
        # Room name should appear after a cyan code
        cyan_idx = result.index("|c")
        name_idx = result.index(self.room1.key)
        self.assertLess(cyan_idx, name_idx)

    def test_things_are_green(self):
        """Objects in room should be in green."""
        create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="a rusty sword",
            location=self.room1,
            nohome=True,
        )
        result = self.room1.return_appearance(self.char1)
        green_idx = result.index("|g")
        sword_idx = result.index("rusty sword")
        self.assertLess(green_idx, sword_idx)

    def test_characters_are_yellow(self):
        """Characters in room should be in yellow."""
        result = self.room1.return_appearance(self.char1)
        # char2 should be visible and yellow
        if self.char2.key in result:
            yellow_idx = result.index("|y")
            char_idx = result.index(self.char2.key)
            self.assertLess(yellow_idx, char_idx)

    # ── Description present ────────────────────────────────────────────

    def test_description_shown(self):
        """Room description should appear in normal output."""
        result = self.room1.return_appearance(self.char1)
        self.assertIn("A grassy field.", result)


# ---------------------------------------------------------------------------
#  Brief mode tests
# ---------------------------------------------------------------------------

class TestBriefMode(EvenniaTest):
    """Test brief_mode preference suppresses description on movement."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.db.desc = "A detailed room description."
        self.room1.always_lit = True

    def test_brief_mode_hides_description(self):
        """With brief_mode ON, description is hidden (no ignore_brief)."""
        self.char1.brief_mode = True
        result = self.room1.return_appearance(self.char1)
        self.assertNotIn("A detailed room description.", result)

    def test_brief_mode_still_shows_name(self):
        """With brief_mode ON, room name is still shown."""
        self.char1.brief_mode = True
        result = self.room1.return_appearance(self.char1)
        self.assertIn(self.room1.key, result)

    def test_ignore_brief_shows_description(self):
        """With brief_mode ON but ignore_brief=True, description appears."""
        self.char1.brief_mode = True
        result = self.room1.return_appearance(self.char1, ignore_brief=True)
        self.assertIn("A detailed room description.", result)

    def test_brief_off_shows_description(self):
        """With brief_mode OFF, description appears normally."""
        self.char1.brief_mode = False
        result = self.room1.return_appearance(self.char1)
        self.assertIn("A detailed room description.", result)


# ---------------------------------------------------------------------------
#  Auto-exit suppression tests
# ---------------------------------------------------------------------------

class TestAutoExits(EvenniaTest):
    """Test auto_exits preference controls exit display."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        # Create an exit so there's something to show/hide
        self.room2 = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Room2",
            nohome=True,
        )
        self.room2.always_lit = True
        self.exit = create.create_object(
            "evennia.objects.objects.DefaultExit",
            key="north",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )

    def test_auto_exits_on_shows_exit(self):
        """With auto_exits ON, exit appears in compact format."""
        self.char1.auto_exits = True
        result = self.room1.return_appearance(self.char1)
        self.assertIn("Exits:", result)

    def test_auto_exits_off_hides_exit(self):
        """With auto_exits OFF, exit section is suppressed."""
        self.char1.auto_exits = False
        result = self.room1.return_appearance(self.char1)
        self.assertNotIn("Exits:", result)

    def test_compact_exit_format(self):
        """Exits should display as [ Exits: ... ] on one line."""
        self.char1.auto_exits = True
        exits_str = self.room1.get_display_exits(self.char1)
        self.assertTrue(exits_str.startswith("[ Exits:"))
        self.assertTrue(exits_str.endswith("]"))

    def test_directional_exit_abbreviation(self):
        """Directional exits should use abbreviations (n, s, e, w)."""
        # Replace the DefaultExit with a directional one
        self.exit.delete()
        ex = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        ex.set_direction("north")
        exits_str = self.room1.get_display_exits(self.char1)
        self.assertIn("n", exits_str)
        # Should NOT contain the full word "north" inside brackets
        inner = exits_str.replace("[ Exits: ", "").replace(" ]", "")
        self.assertNotIn("north", inner)

    def test_closed_door_hidden_from_auto_exits(self):
        """Closed doors should not appear in the compact auto-exit line."""
        self.exit.delete()
        # Remove all default exits so only the door remains
        for ex in self.room1.contents_get(content_type="exit"):
            ex.delete()
        door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="a heavy oak door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        door.set_direction("south")
        door.is_open = False
        exits_str = self.room1.get_display_exits(self.char1)
        # Closed door should be completely hidden — no exits at all
        self.assertEqual(exits_str, "")

    def test_open_door_shown_in_auto_exits(self):
        """Open doors should appear in the compact auto-exit line."""
        self.exit.delete()
        door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="a heavy oak door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        door.set_direction("south")
        door.is_open = True
        exits_str = self.room1.get_display_exits(self.char1)
        # Extract the exit abbreviations from inside the brackets
        inner = exits_str.replace("[ Exits: ", "").replace(" ]", "")
        self.assertIn("s", inner.split())


# ---------------------------------------------------------------------------
#  Look command brief bypass tests
# ---------------------------------------------------------------------------

class TestLookCommandBriefBypass(EvenniaCommandTest):
    """Test that explicit 'look' bypasses brief mode."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.db.desc = "A detailed room description."
        self.room1.always_lit = True
        self.account.attributes.add(
            "wallet_address", "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )

    def test_look_command_shows_desc_when_brief(self):
        """Explicit 'look' shows description even with brief_mode ON."""
        self.char1.brief_mode = True
        result = self.call(CmdLook(), "")
        self.assertIn("A detailed room description.", result)


# ---------------------------------------------------------------------------
#  Room description (character display in rooms) tests
# ---------------------------------------------------------------------------

class TestRoomDescription(EvenniaTest):
    """Test room_description display in character list."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True

    def test_default_room_description(self):
        """Characters with no custom room_description show default sentence."""
        result = self.room1.return_appearance(self.char1)
        self.assertIn("unremarkable", result)
        self.assertIn(self.char2.key, result)

    def test_custom_room_description(self):
        """Characters with custom room_description show it instead."""
        self.char2.room_description = "A grizzled warrior leans against the wall."
        result = self.room1.return_appearance(self.char1)
        self.assertIn("grizzled warrior", result)

    def test_room_description_name_placeholder(self):
        """The {name} placeholder is replaced with character name."""
        self.char2.room_description = "{name} the brave stands watch here."
        result = self.room1.return_appearance(self.char1)
        self.assertIn(self.char2.key, result)
        self.assertNotIn("{name}", result)

    def test_one_character_per_line(self):
        """Each character should be on its own line, not comma-separated."""
        # Create a third character so we have 2 visible (char2, char3)
        char3 = create.create_object(
            "typeclasses.actors.character.FCMCharacter",
            key="Gandalf",
            location=self.room1,
            nohome=True,
        )
        result = self.room1.return_appearance(self.char1)
        chars_section = self.room1.get_display_characters(self.char1)
        # Should have newlines between characters, not commas
        self.assertIn("\n", chars_section)
        self.assertNotIn(", and", chars_section)
