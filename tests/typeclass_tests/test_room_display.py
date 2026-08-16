"""
Tests for CircleMUD-style room display: template layout, color coding,
brief mode, and auto-exit suppression.

evennia test --settings settings tests.typeclass_tests.test_room_display
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest, EvenniaCommandTest
from evennia.utils import create

from enums.condition import Condition
from enums.named_effect import NamedEffect
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


class TestDisplayCharactersUnsighted(EvenniaTest):
    """
    A looker who cannot see still perceives that bodies are present. They
    get an anonymised line and none of the detail that would identify who
    is standing there.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.char2.location = self.room1

    def _darken(self):
        # has_natural_light is a read-only property derived from this.
        self.room1.always_lit = False
        self.room1.natural_light = False

    def _section(self):
        return self.room1.get_display_characters(self.char1)

    # ── The room is not empty ──────────────────────────────────────────

    def test_a_dark_room_still_reports_someone(self):
        """The premise: bodies present, identity withheld — not an empty room."""
        self._darken()
        self.assertIn("Someone is in the room.", self._section())

    def test_a_blind_looker_still_reports_someone(self):
        self.char1.add_condition(Condition.BLINDED)
        self.assertIn("Someone is in the room.", self._section())

    def test_the_real_name_is_withheld(self):
        self._darken()
        self.assertNotIn(self.char2.key, self._section())

    def test_an_empty_dark_room_reports_nothing(self):
        self.char2.location = self.room2
        self._darken()
        self.assertEqual(self._section(), "")

    def test_one_line_per_body(self):
        char3 = create.create_object(
            "typeclasses.actors.character.FCMCharacter",
            key="Gandalf",
            location=self.room1,
            nohome=True,
        )
        self._darken()
        self.assertEqual(self._section().count("is in the room."), 2)

    # ── The word is content ────────────────────────────────────────────

    def test_the_placeholder_is_settable(self):
        """unseen_name is an AttributeProperty, so content can reword it."""
        self.char2.unseen_name = "A mysterious presence"
        self._darken()
        self.assertIn("A mysterious presence is in the room.", self._section())

    # ── Identifying detail is withheld with the name ───────────────────

    def test_the_room_description_is_withheld(self):
        self.char2.room_description = "leans against the bar, whistling."
        self._darken()
        self.assertNotIn("whistling", self._section())

    def test_the_room_description_is_shown_when_sighted(self):
        self.char2.room_description = "leans against the bar, whistling."
        self.assertIn("whistling", self._section())

    def test_height_tags_are_withheld(self):
        self.char2.room_vertical_position = 2
        self._darken()
        self.assertNotIn("(Flying)", self._section())

    def test_height_tags_are_shown_when_sighted(self):
        self.char2.room_vertical_position = 2
        self.assertIn("(Flying)", self._section())

    def test_concealment_tags_are_withheld(self):
        """Only a looker who can see is told how they are seeing them."""
        self.char2.add_condition(Condition.INVISIBLE)
        self.char1.add_condition(Condition.DETECT_INVIS)
        self._darken()
        self.assertNotIn("(invisible)", self._section())

    def test_concealment_tags_are_shown_when_sighted(self):
        self.char2.add_condition(Condition.INVISIBLE)
        self.char1.add_condition(Condition.DETECT_INVIS)
        self.assertIn("(invisible)", self._section())

    def test_the_alignment_aura_is_withheld(self):
        self.char2.alignment_score = -500
        self.char1.apply_named_effect(NamedEffect.DETECT_ALIGNMENT, duration=300)
        self._darken()
        self.assertNotIn("(Evil)", self._section())

    # ── Darkvision is not blindness ────────────────────────────────────

    def test_darkvision_gets_the_full_rendering(self):
        self.char2.room_description = "leans against the bar, whistling."
        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        section = self._section()
        self.assertIn("whistling", section)
        self.assertNotIn("is in the room.", section)


class TestDisplayThingsUnsighted(EvenniaTest):
    """
    Items are shapes you can make out but not identify. Collapsed rather
    than one line each, since a room can hold many more things than
    people.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        # EvenniaTest seeds room1 with obj/obj2 — clear them so each test
        # controls exactly what is on the ground.
        self.obj1.location = self.room2
        self.obj2.location = self.room2

    def _darken(self):
        # has_natural_light is a read-only property derived from this.
        self.room1.always_lit = False
        self.room1.natural_light = False

    def _thing(self, key="a brass key"):
        return create.create_object(
            "typeclasses.world_objects.base_world_item.WorldItem",
            key=key,
            location=self.room1,
            nohome=True,
        )

    def _section(self):
        return self.room1.get_display_things(self.char1)

    # ── The room is not empty ──────────────────────────────────────────

    def test_one_thing_in_the_dark(self):
        self._thing()
        self._darken()
        self.assertEqual(self._section(), "Something is on the ground.")

    def test_several_things_collapse(self):
        self._thing("a brass key")
        self._thing("a rusty dagger")
        self._thing("a clay pot")
        self._darken()
        self.assertEqual(
            self._section(), "Several things are on the ground."
        )

    def test_a_blind_looker_gets_the_same(self):
        self._thing()
        self.char1.add_condition(Condition.BLINDED)
        self.assertEqual(self._section(), "Something is on the ground.")

    def test_an_empty_dark_room_reports_nothing(self):
        self._darken()
        self.assertEqual(self._section(), "")

    def test_the_real_name_is_withheld(self):
        self._thing()
        self._darken()
        self.assertNotIn("brass key", self._section())

    # ── The word is content ────────────────────────────────────────────

    def test_the_singular_keeps_the_items_own_word(self):
        thing = self._thing()
        thing.unseen_name = "A strange shape"
        self._darken()
        self.assertEqual(self._section(), "A strange shape is on the ground.")

    # ── Identifying detail is withheld ─────────────────────────────────

    def test_ground_descriptions_are_withheld(self):
        thing = self._thing()
        thing.ground_description = "A brass key glints among the rushes."
        self._darken()
        section = self._section()
        self.assertNotIn("glints", section)
        self.assertEqual(section, "Something is on the ground.")

    def test_ground_descriptions_are_shown_when_sighted(self):
        thing = self._thing()
        thing.ground_description = "A brass key glints among the rushes."
        self.assertIn("glints", self._section())

    # ── The sighted path is untouched ──────────────────────────────────

    def test_sighted_still_groups_and_lists(self):
        self._thing("brass key")
        self._thing("brass key")
        section = self._section()
        self.assertIn("two brass keys", section)

    def test_darkvision_gets_the_full_rendering(self):
        self._thing()
        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        section = self._section()
        self.assertIn("brass key", section)
        self.assertNotIn("on the ground.", section)


class TestReturnAppearanceUnsighted(EvenniaTest):
    """
    The assembled room, for a looker who cannot see. The premise this
    whole seam exists for: bodies and shapes you cannot identify, not an
    empty room.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.db.desc = "A grassy field under open sky."
        self.room1.always_lit = True
        self.obj1.location = self.room2
        self.obj2.location = self.room2
        self.char2.location = self.room1

    def _darken(self):
        # has_natural_light is a read-only property derived from this.
        self.room1.always_lit = False
        self.room1.natural_light = False

    def _thing(self, key="a brass key"):
        return create.create_object(
            "typeclasses.world_objects.base_world_item.WorldItem",
            key=key,
            location=self.room1,
            nohome=True,
        )

    def _look(self):
        return self.room1.return_appearance(self.char1, ignore_brief=True)

    # ── What a dark room shows ─────────────────────────────────────────

    def test_the_room_is_somewhere(self):
        self._darken()
        self.assertIn("Somewhere", self._look())

    def test_the_room_name_is_withheld(self):
        self._darken()
        self.assertNotIn(self.room1.key, self._look())

    def test_the_description_is_withheld(self):
        self._darken()
        self.assertNotIn("grassy field", self._look())

    def test_bodies_are_reported(self):
        """The premise — an occupied dark room does not read as empty."""
        self._darken()
        self.assertIn("Someone is in the room.", self._look())

    def test_things_are_reported(self):
        self._thing()
        self._darken()
        self.assertIn("Something is on the ground.", self._look())

    def test_no_names_leak_anywhere(self):
        self._thing()
        self._darken()
        result = self._look()
        self.assertNotIn(self.char2.key, result)
        self.assertNotIn("brass key", result)

    # ── A blind looker takes the same path in a lit room ───────────────

    def test_a_blind_looker_in_a_lit_room_is_treated_the_same(self):
        """Was the inconsistency: full room render, anonymised occupants."""
        self._thing()
        self.char1.add_condition(Condition.BLINDED)
        result = self._look()
        self.assertIn("Somewhere", result)
        self.assertNotIn("grassy field", result)
        self.assertIn("Someone is in the room.", result)
        self.assertIn("Something is on the ground.", result)

    # ── Sighted is untouched ───────────────────────────────────────────

    def test_a_lit_room_shows_everything(self):
        self._thing()
        result = self._look()
        self.assertIn(self.room1.key, result)
        self.assertIn("grassy field", result)
        self.assertIn(self.char2.key, result)
        self.assertIn("brass key", result)

    def test_darkvision_shows_everything(self):
        self._thing()
        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        result = self._look()
        self.assertIn("grassy field", result)
        self.assertIn(self.char2.key, result)
        self.assertIn("brass key", result)

    def test_darkvision_is_tagged_as_dark(self):
        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        self.assertIn("(Dark)", self._look())
