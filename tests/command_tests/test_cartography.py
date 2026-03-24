"""
Tests for the Cartography system.

Covers:
  - map_registry: register_map, get_map, get_all_maps, get_map_keys_for_room, render_map
  - DistrictMapNFTItem: surveyed_points, completion_pct, get_display_name
  - CmdSurvey: gate checks, full survey flow, multi-map, cancellation
  - CmdMap: list mode, render mode, matching, edge cases

evennia test --settings settings tests.command_tests.test_cartography
"""

from collections.abc import MutableSet
from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest, EvenniaCommandTest
from evennia.utils import create

from commands.general_skill_cmds.cmd_survey import CmdSurvey, _finish_survey
from commands.general_skill_cmds.cmd_map import CmdMap
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.cartography.map_registry import (
    MAP_REGISTRY,
    register_map,
    get_map,
    get_all_maps,
    get_map_keys_for_room,
    render_map,
)


# ── Test map fixtures ─────────────────────────────────────────────────────

FAKE_MAP_KEY = "_test_cartography_map"
FAKE_MAP_DEF = {
    "key": FAKE_MAP_KEY,
    "display_name": "Test Area",
    "template": "AB\nCD",
    "point_cells": {
        "room_a": [(0, 0)],
        "room_b": [(0, 1)],
        "room_c": [(1, 0)],
        "room_d": [(1, 1)],
    },
}

FAKE_MAP_KEY_2 = "_test_cartography_region"
FAKE_MAP_DEF_2 = {
    "key": FAKE_MAP_KEY_2,
    "display_name": "Test Region",
    "template": "XY",
    "point_cells": {
        "region_a": [(0, 0)],
        "region_b": [(0, 1)],
    },
}


# ── Windows OSError fix ───────────────────────────────────────────────────
#
# On Windows, datetime.fromtimestamp(0) raises OSError: [Errno 22] Invalid
# argument.  In tests the game timestamp is 0 (no DayNightService script
# running), which causes RoomBase.is_dark() → get_time_of_day() to explode
# during character creation inside EvenniaTest.setUp().  Applying this mixin
# BEFORE super().setUp() ensures the patch is already active when Evennia
# creates the test character and calls at_post_move → at_look → is_dark.

class _RoomBaseMixin:
    """Patch get_time_of_day before setUp so RoomBase.is_dark() doesn't blow
    up on Windows with game_timestamp=0."""

    def setUp(self):
        self._time_patcher = patch(
            "typeclasses.scripts.day_night_service.get_time_of_day",
            return_value=MagicMock(is_light=True),
        )
        self._time_patcher.start()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        self._time_patcher.stop()


# ── Helpers ───────────────────────────────────────────────────────────────

def _set_cart(char, level):
    """Set CARTOGRAPHY mastery level on a character."""
    levels = char.db.general_skill_mastery_levels or {}
    levels[skills.CARTOGRAPHY.value] = level.value
    char.db.general_skill_mastery_levels = levels


def _make_map_item(char, map_key, surveyed=None):
    """
    Place a DistrictMapNFTItem in char's inventory without triggering NFT hooks.
    Uses db_location bypass (same pattern as _make_nft_raw in base NFT tests).
    """
    item = create.create_object(
        "typeclasses.items.maps.district_map_nft_item.DistrictMapNFTItem",
        key=f"map-{map_key}",
        nohome=True,
    )
    item.map_key = map_key
    item.db.surveyed_points = set(surveyed) if surveyed else set()
    item.db_location = char
    item.save(update_fields=["db_location"])
    return item


# ══════════════════════════════════════════════════════════════════════════
#  1. Map Registry — register_map / get_map / get_all_maps
# ══════════════════════════════════════════════════════════════════════════

class TestMapRegistry(EvenniaTest):
    """Unit tests for the MAP_REGISTRY management functions."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        MAP_REGISTRY[FAKE_MAP_KEY] = dict(FAKE_MAP_DEF)

    def tearDown(self):
        MAP_REGISTRY.pop(FAKE_MAP_KEY, None)
        MAP_REGISTRY.pop("_test_reg_new", None)
        super().tearDown()

    def test_register_map_adds_to_registry(self):
        new_def = {"key": "_test_reg_new", "display_name": "New", "template": "", "point_cells": {}}
        register_map(new_def)
        self.assertIn("_test_reg_new", MAP_REGISTRY)

    def test_register_map_stores_correct_def(self):
        new_def = {"key": "_test_reg_new", "display_name": "New", "template": "X", "point_cells": {}}
        register_map(new_def)
        self.assertEqual(MAP_REGISTRY["_test_reg_new"]["display_name"], "New")

    def test_register_map_overwrites_existing(self):
        MAP_REGISTRY[FAKE_MAP_KEY] = {"key": FAKE_MAP_KEY, "display_name": "Old", "template": "", "point_cells": {}}
        register_map({"key": FAKE_MAP_KEY, "display_name": "Replaced", "template": "", "point_cells": {}})
        self.assertEqual(MAP_REGISTRY[FAKE_MAP_KEY]["display_name"], "Replaced")

    def test_get_map_returns_registered(self):
        result = get_map(FAKE_MAP_KEY)
        self.assertIsNotNone(result)
        self.assertEqual(result["display_name"], "Test Area")

    def test_get_map_unknown_key_returns_none(self):
        self.assertIsNone(get_map("totally_unknown_map_key_xyz"))

    def test_get_map_returns_dict(self):
        self.assertIsInstance(get_map(FAKE_MAP_KEY), dict)

    def test_get_all_maps_contains_registered(self):
        all_maps = get_all_maps()
        self.assertIn(FAKE_MAP_KEY, all_maps)

    def test_get_all_maps_returns_copy(self):
        """Mutating the returned dict must not affect MAP_REGISTRY."""
        all_maps = get_all_maps()
        all_maps["_mutation_test"] = True
        self.assertNotIn("_mutation_test", MAP_REGISTRY)


# ══════════════════════════════════════════════════════════════════════════
#  2. render_map
# ══════════════════════════════════════════════════════════════════════════

class TestRenderMap(EvenniaTest):
    """Unit tests for render_map() ASCII masking logic."""

    def create_script(self):
        pass

    def test_all_unsurveyed_shows_blank(self):
        ascii_out, legend = render_map(FAKE_MAP_DEF, set())
        self.assertEqual(ascii_out, "  \n  ")
        self.assertEqual(legend, "")

    def test_all_surveyed_shows_symbols(self):
        """All cells visible — legacy format uses 'unknown' POI → '?' symbol."""
        all_keys = set(FAKE_MAP_DEF["point_cells"].keys())
        ascii_out, legend = render_map(FAKE_MAP_DEF, all_keys)
        # Legacy format cells get 'unknown' POI type
        from world.cartography.poi_symbols import POI_SYMBOLS
        sym = POI_SYMBOLS.get("unknown", "?")
        self.assertTrue(all(c == sym for c in ascii_out if c not in ("\n", " ")))

    def test_partial_survey_first_point(self):
        ascii_out, _ = render_map(FAKE_MAP_DEF, {"room_a"})
        lines = ascii_out.split("\n")
        self.assertNotEqual(lines[0][0], " ")  # room_a surveyed → symbol shown
        self.assertEqual(lines[0][1], " ")     # room_b not surveyed → blank
        self.assertEqual(lines[1][0], " ")     # room_c not surveyed
        self.assertEqual(lines[1][1], " ")     # room_d not surveyed

    def test_partial_survey_diagonal(self):
        ascii_out, _ = render_map(FAKE_MAP_DEF, {"room_a", "room_d"})
        lines = ascii_out.split("\n")
        self.assertNotEqual(lines[0][0], " ")  # room_a visible
        self.assertEqual(lines[0][1], " ")     # room_b hidden
        self.assertEqual(lines[1][0], " ")     # room_c hidden
        self.assertNotEqual(lines[1][1], " ")  # room_d visible

    def test_structural_dashes_hidden_when_no_visible_neighbors(self):
        map_def = {
            "key": "_struct_test",
            "display_name": "Struct",
            "template": "-A-\n-B-",
            "point_cells": {
                "pt_a": [(0, 1)],
                "pt_b": [(1, 1)],
            },
        }
        ascii_out, _ = render_map(map_def, set())
        lines = ascii_out.split("\n")
        # No visible point cells → structural dashes hidden
        self.assertEqual(lines[0], "   ")
        self.assertEqual(lines[1], "   ")

    def test_structural_chars_shown_when_surveyed(self):
        map_def = {
            "key": "_struct_test2",
            "display_name": "Struct2",
            "template": "-A-",
            "point_cells": {"pt_a": [(0, 1)]},
        }
        ascii_out, _ = render_map(map_def, {"pt_a"})
        lines = ascii_out.split("\n")
        # Dashes adjacent to visible cell should show
        self.assertEqual(lines[0][1], ascii_out[1])  # cell is visible
        self.assertNotEqual(lines[0][0], " ")  # left dash visible

    def test_unknown_surveyed_key_does_not_raise(self):
        try:
            render_map(FAKE_MAP_DEF, {"nonexistent_point_xyz"})
        except Exception as exc:
            self.fail(f"render_map raised unexpectedly: {exc}")

    def test_empty_template_returns_empty(self):
        map_def = {"key": "_empty", "display_name": "E", "template": "", "point_cells": {}}
        ascii_out, legend = render_map(map_def, set())
        self.assertEqual(ascii_out, "")

    def test_multiline_template_preserves_lines(self):
        all_keys = set(FAKE_MAP_DEF["point_cells"].keys())
        ascii_out, _ = render_map(FAKE_MAP_DEF, all_keys)
        self.assertEqual(len(ascii_out.split("\n")), 2)

    def test_point_with_multiple_positions_all_masked(self):
        map_def = {
            "key": "_multi_pos",
            "display_name": "MultiPos",
            "template": "AB",
            "point_cells": {"big_room": [(0, 0), (0, 1)]},
        }
        ascii_out, _ = render_map(map_def, set())
        self.assertEqual(ascii_out, "  ")

    def test_point_with_multiple_positions_all_shown(self):
        map_def = {
            "key": "_multi_pos2",
            "display_name": "MultiPos2",
            "template": "AB",
            "point_cells": {"big_room": [(0, 0), (0, 1)]},
        }
        ascii_out, _ = render_map(map_def, {"big_room"})
        # Both positions shown (legacy format → unknown symbol)
        self.assertNotEqual(ascii_out[0], " ")
        self.assertNotEqual(ascii_out[1], " ")

    def test_three_line_template(self):
        map_def = {
            "key": "_three",
            "display_name": "Three",
            "template": "A\nB\nC",
            "point_cells": {
                "r1": [(0, 0)],
                "r2": [(1, 0)],
                "r3": [(2, 0)],
            },
        }
        ascii_out, _ = render_map(map_def, {"r1", "r3"})
        lines = ascii_out.split("\n")
        self.assertNotEqual(lines[0], " ")  # r1 visible
        self.assertEqual(lines[1], " ")     # r2 hidden
        self.assertNotEqual(lines[2], " ")  # r3 visible

    def test_unsurveyed_cells_are_blank_not_block(self):
        """Unsurveyed cells should be blank spaces, not '░'."""
        ascii_out, _ = render_map(FAKE_MAP_DEF, set())
        self.assertNotIn("░", ascii_out)

    def test_new_format_uses_poi_symbols(self):
        """New point_cells format with POI types uses central symbol registry."""
        from world.cartography.poi_symbols import POI_SYMBOLS
        map_def = {
            "key": "_poi_test",
            "display_name": "POI Test",
            "template": "A-B",
            "point_cells": {
                "shop": {"pos": [(0, 0)], "poi": "smithy"},
                "road": {"pos": [(0, 2)], "poi": "road"},
            },
        }
        ascii_out, legend = render_map(map_def, {"shop", "road"})
        self.assertEqual(ascii_out[0], POI_SYMBOLS["smithy"])
        self.assertEqual(ascii_out[2], POI_SYMBOLS["road"])
        self.assertIn("Smithy", legend)
        self.assertIn("Road", legend)

    def test_legend_only_shows_visible_types(self):
        """Legend should only include POI types that are actually visible."""
        map_def = {
            "key": "_legend_test",
            "display_name": "Legend Test",
            "template": "AB",
            "point_cells": {
                "the_bank": {"pos": [(0, 0)], "poi": "bank"},
                "the_inn":  {"pos": [(0, 1)], "poi": "inn"},
            },
        }
        _, legend = render_map(map_def, {"the_bank"})
        self.assertIn("Bank", legend)
        self.assertNotIn("Inn", legend)


# ══════════════════════════════════════════════════════════════════════════
#  3. get_map_keys_for_room
# ══════════════════════════════════════════════════════════════════════════

class TestGetMapKeysForRoom(_RoomBaseMixin, EvenniaTest):
    """Tests for get_map_keys_for_room — room tag parsing."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_no_tags_returns_empty(self):
        self.assertEqual(get_map_keys_for_room(self.room1), [])

    def test_single_tag_parsed(self):
        self.room1.tags.add("millholm_town:sq_center", category="map_cell")
        result = get_map_keys_for_room(self.room1)
        self.assertEqual(len(result), 1)
        self.assertIn(("millholm_town", "sq_center"), result)

    def test_multiple_tags_all_returned(self):
        self.room1.tags.add("millholm_town:sq_center", category="map_cell")
        self.room1.tags.add("millholm_region:millholm_town", category="map_cell")
        result = get_map_keys_for_room(self.room1)
        self.assertEqual(len(result), 2)
        self.assertIn(("millholm_town", "sq_center"), result)
        self.assertIn(("millholm_region", "millholm_town"), result)

    def test_tag_without_colon_ignored(self):
        self.room1.tags.add("no_colon_here", category="map_cell")
        self.assertEqual(get_map_keys_for_room(self.room1), [])

    def test_wrong_category_ignored(self):
        self.room1.tags.add("millholm_town:sq_center", category="zone")
        self.assertEqual(get_map_keys_for_room(self.room1), [])

    def test_tag_with_extra_colon_splits_on_first(self):
        """'map:point:sub' should split to ('map', 'point:sub')."""
        self.room1.tags.add("map_key:point:extra", category="map_cell")
        result = get_map_keys_for_room(self.room1)
        self.assertIn(("map_key", "point:extra"), result)

    def test_returns_list_not_set(self):
        self.room1.tags.add("millholm_town:sq_center", category="map_cell")
        result = get_map_keys_for_room(self.room1)
        self.assertIsInstance(result, list)


# ══════════════════════════════════════════════════════════════════════════
#  4. DistrictMapNFTItem
# ══════════════════════════════════════════════════════════════════════════

class TestDistrictMapNFTItem(_RoomBaseMixin, EvenniaTest):
    """Tests for DistrictMapNFTItem typeclass."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        MAP_REGISTRY[FAKE_MAP_KEY] = dict(FAKE_MAP_DEF)

    def tearDown(self):
        MAP_REGISTRY.pop(FAKE_MAP_KEY, None)
        MAP_REGISTRY.pop("_test_empty_pts", None)
        MAP_REGISTRY.pop("_test_3pt", None)
        super().tearDown()

    def _make(self, map_key=FAKE_MAP_KEY, surveyed=None):
        item = create.create_object(
            "typeclasses.items.maps.district_map_nft_item.DistrictMapNFTItem",
            key="test-map",
            nohome=True,
        )
        item.map_key = map_key
        item.db.surveyed_points = set(surveyed) if surveyed else set()
        return item

    # ── at_object_creation ────────────────────────────────────────────────

    def test_creation_initializes_surveyed_points_as_set(self):
        item = self._make()
        self.assertIsInstance(item.db.surveyed_points, MutableSet)

    def test_creation_surveyed_points_empty(self):
        item = self._make()
        self.assertEqual(len(item.db.surveyed_points), 0)

    def test_creation_adds_district_map_item_type_tag(self):
        item = self._make()
        self.assertTrue(item.tags.has("district_map", category="item_type"))

    # ── surveyed_points property ──────────────────────────────────────────

    def test_surveyed_points_returns_set(self):
        item = self._make()
        self.assertIsInstance(item.surveyed_points, MutableSet)

    def test_surveyed_points_lazy_init_when_none(self):
        item = self._make()
        item.db.surveyed_points = None
        pts = item.surveyed_points
        self.assertIsInstance(pts, MutableSet)
        self.assertEqual(len(pts), 0)

    def test_surveyed_points_reflects_stored_values(self):
        item = self._make(surveyed={"room_a", "room_b"})
        self.assertIn("room_a", item.surveyed_points)
        self.assertIn("room_b", item.surveyed_points)

    def test_surveyed_points_is_mutable(self):
        item = self._make()
        item.surveyed_points.add("room_a")
        self.assertIn("room_a", item.surveyed_points)

    # ── completion_pct ────────────────────────────────────────────────────

    def test_completion_pct_zero_when_nothing_surveyed(self):
        item = self._make()
        self.assertEqual(item.completion_pct, 0)

    def test_completion_pct_100_when_all_surveyed(self):
        all_keys = set(FAKE_MAP_DEF["point_cells"].keys())
        item = self._make(surveyed=all_keys)
        self.assertEqual(item.completion_pct, 100)

    def test_completion_pct_50_when_half_surveyed(self):
        item = self._make(surveyed={"room_a", "room_b"})  # 2 of 4
        self.assertEqual(item.completion_pct, 50)

    def test_completion_pct_25_when_one_surveyed(self):
        item = self._make(surveyed={"room_a"})  # 1 of 4
        self.assertEqual(item.completion_pct, 25)

    def test_completion_pct_75_when_three_surveyed(self):
        item = self._make(surveyed={"room_a", "room_b", "room_c"})  # 3 of 4
        self.assertEqual(item.completion_pct, 75)

    def test_completion_pct_unknown_map_key_returns_zero(self):
        item = self._make(map_key="nonexistent_map_key_xyz")
        self.assertEqual(item.completion_pct, 0)

    def test_completion_pct_empty_point_cells_returns_zero(self):
        MAP_REGISTRY["_test_empty_pts"] = {
            "key": "_test_empty_pts", "display_name": "Empty",
            "template": "", "point_cells": {},
        }
        item = self._make(map_key="_test_empty_pts")
        self.assertEqual(item.completion_pct, 0)

    def test_completion_pct_rounds_correctly(self):
        """1 of 3 = 33.33% → rounds to 33."""
        MAP_REGISTRY["_test_3pt"] = {
            "key": "_test_3pt", "display_name": "Three Point",
            "template": "ABC",
            "point_cells": {"pt_a": [(0, 0)], "pt_b": [(0, 1)], "pt_c": [(0, 2)]},
        }
        item = self._make(map_key="_test_3pt", surveyed={"pt_a"})
        self.assertEqual(item.completion_pct, 33)

    def test_completion_pct_is_integer(self):
        item = self._make(surveyed={"room_a"})
        self.assertIsInstance(item.completion_pct, int)

    # ── get_display_name ──────────────────────────────────────────────────

    def test_display_name_zero_pct(self):
        item = self._make()
        result = item.get_display_name(looker=None)
        self.assertEqual(result, "Map: Test Area 0%")

    def test_display_name_partial_pct(self):
        item = self._make(surveyed={"room_a", "room_b"})
        result = item.get_display_name(looker=None)
        self.assertEqual(result, "Map: Test Area 50%")

    def test_display_name_full_pct(self):
        all_keys = set(FAKE_MAP_DEF["point_cells"].keys())
        item = self._make(surveyed=all_keys)
        result = item.get_display_name(looker=None)
        self.assertEqual(result, "Map: Test Area 100%")

    def test_display_name_unknown_map_key_falls_back_to_key(self):
        item = self._make(map_key="unknown_area_key")
        result = item.get_display_name(looker=self.char1)
        self.assertIn("unknown_area_key", result)

    def test_display_name_empty_map_key_shows_unknown_area(self):
        item = self._make(map_key="")
        result = item.get_display_name(looker=self.char1)
        self.assertIn("Unknown Area", result)

    def test_display_name_starts_with_map_prefix(self):
        item = self._make()
        result = item.get_display_name(looker=self.char1)
        self.assertTrue(result.startswith("Map:"))

    def test_display_name_no_looker_does_not_raise(self):
        item = self._make()
        try:
            result = item.get_display_name(looker=None)
            self.assertIn("Map:", result)
        except Exception as exc:
            self.fail(f"get_display_name raised with no looker: {exc}")

    def test_display_name_builder_shows_token_id(self):
        item = self._make()
        item.token_id = 42
        self.char1.permissions.add("Builder")
        try:
            result = item.get_display_name(looker=self.char1)
            self.assertIn("[NFT #42]", result)
        finally:
            self.char1.permissions.remove("Builder")

    def test_display_name_non_builder_no_token_id(self):
        item = self._make()
        item.token_id = 42
        with patch.object(item.locks, "check_lockstring", return_value=False):
            result = item.get_display_name(looker=self.char1)
        self.assertNotIn("NFT #", result)

    def test_display_name_includes_pct_sign(self):
        item = self._make()
        result = item.get_display_name(looker=self.char1)
        self.assertIn("%", result)


# ══════════════════════════════════════════════════════════════════════════
#  5. CmdSurvey — Gate Checks
# ══════════════════════════════════════════════════════════════════════════

class TestCmdSurveyGates(_RoomBaseMixin, EvenniaCommandTest):
    """Tests for CmdSurvey gate conditions."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        MAP_REGISTRY[FAKE_MAP_KEY] = dict(FAKE_MAP_DEF)

    def tearDown(self):
        MAP_REGISTRY.pop(FAKE_MAP_KEY, None)
        super().tearDown()

    def test_unskilled_blocked(self):
        _set_cart(self.char1, MasteryLevel.UNSKILLED)
        result = self.call(CmdSurvey(), "")
        self.assertIn("no training in cartography", result)

    def test_no_mastery_dict_blocked(self):
        """Character with no mastery dict at all should be blocked."""
        self.char1.db.general_skill_mastery_levels = None
        result = self.call(CmdSurvey(), "")
        self.assertIn("no training in cartography", result)

    def test_basic_mastery_passes_gate(self):
        """BASIC mastery should not produce the 'no training' message."""
        _set_cart(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdSurvey(), "")
        self.assertNotIn("no training in cartography", result)

    def test_skilled_mastery_passes_gate(self):
        _set_cart(self.char1, MasteryLevel.SKILLED)
        result = self.call(CmdSurvey(), "")
        self.assertNotIn("no training in cartography", result)

    def test_combat_blocked(self):
        _set_cart(self.char1, MasteryLevel.BASIC)
        with patch.object(self.char1.scripts, "get", return_value=[MagicMock()]):
            result = self.call(CmdSurvey(), "")
        self.assertIn("can't survey while fighting", result)

    def test_room_no_map_cell_tags(self):
        _set_cart(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdSurvey(), "")
        self.assertIn("nothing notable to map here", result)

    def test_tagged_room_but_no_map_in_inventory(self):
        """Room tagged but player has no matching map → no targets."""
        _set_cart(self.char1, MasteryLevel.BASIC)
        self.room1.tags.add(f"{FAKE_MAP_KEY}:room_a", category="map_cell")
        result = self.call(CmdSurvey(), "")
        self.assertIn("already mapped everything", result)

    def test_all_points_already_surveyed(self):
        _set_cart(self.char1, MasteryLevel.BASIC)
        self.room1.tags.add(f"{FAKE_MAP_KEY}:room_a", category="map_cell")
        _make_map_item(self.char1, FAKE_MAP_KEY, surveyed={"room_a"})
        result = self.call(CmdSurvey(), "")
        self.assertIn("already mapped everything", result)

    def test_room_tagged_to_unknown_map_no_targets(self):
        """Room tagged to a map the player doesn't have → no targets."""
        _set_cart(self.char1, MasteryLevel.BASIC)
        self.room1.tags.add("unregistered_map:some_point", category="map_cell")
        result = self.call(CmdSurvey(), "")
        self.assertIn("already mapped everything", result)


# ══════════════════════════════════════════════════════════════════════════
#  6. CmdSurvey — Full Flow
# ══════════════════════════════════════════════════════════════════════════

class TestCmdSurveyFlow(_RoomBaseMixin, EvenniaCommandTest):
    """Tests for CmdSurvey survey execution and _finish_survey callback."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        MAP_REGISTRY[FAKE_MAP_KEY] = dict(FAKE_MAP_DEF)
        _set_cart(self.char1, MasteryLevel.BASIC)
        self.room1.tags.add(f"{FAKE_MAP_KEY}:room_a", category="map_cell")
        self.map_item = _make_map_item(self.char1, FAKE_MAP_KEY)

    def tearDown(self):
        MAP_REGISTRY.pop(FAKE_MAP_KEY, None)
        super().tearDown()

    @patch("commands.general_skill_cmds.cmd_survey.delay")
    def test_survey_shows_start_message(self, mock_delay):
        mock_delay.side_effect = lambda t, fn, *a, **kw: None
        result = self.call(CmdSurvey(), "")
        self.assertIn("unfurling your map", result)

    @patch("commands.general_skill_cmds.cmd_survey.delay")
    def test_survey_schedules_delay_of_3_seconds(self, mock_delay):
        self.call(CmdSurvey(), "")
        mock_delay.assert_called_once()
        self.assertEqual(mock_delay.call_args[0][0], 3)

    @patch("commands.general_skill_cmds.cmd_survey.delay")
    def test_finish_survey_adds_point_to_surveyed_set(self, mock_delay):
        mock_delay.side_effect = lambda t, fn, *a, **kw: fn(*a, **kw)
        self.call(CmdSurvey(), "")
        self.assertIn("room_a", self.map_item.surveyed_points)

    @patch("commands.general_skill_cmds.cmd_survey.delay")
    def test_finish_survey_persists_to_db(self, mock_delay):
        mock_delay.side_effect = lambda t, fn, *a, **kw: fn(*a, **kw)
        self.call(CmdSurvey(), "")
        self.assertIn("room_a", self.map_item.db.surveyed_points)

    @patch("commands.general_skill_cmds.cmd_survey.delay")
    def test_finish_survey_shows_completion_message(self, mock_delay):
        mock_delay.side_effect = lambda t, fn, *a, **kw: fn(*a, **kw)
        result = self.call(CmdSurvey(), "")
        self.assertIn("Room added to your map", result)

    @patch("commands.general_skill_cmds.cmd_survey.delay")
    def test_finish_survey_shows_pct_in_message(self, mock_delay):
        mock_delay.side_effect = lambda t, fn, *a, **kw: fn(*a, **kw)
        result = self.call(CmdSurvey(), "")
        self.assertIn("%", result)

    @patch("commands.general_skill_cmds.cmd_survey.delay")
    def test_finish_survey_shows_map_name_in_message(self, mock_delay):
        mock_delay.side_effect = lambda t, fn, *a, **kw: fn(*a, **kw)
        result = self.call(CmdSurvey(), "")
        self.assertIn("Test Area", result)

    def test_finish_survey_cancelled_if_room_id_wrong(self):
        """Directly call _finish_survey with wrong room_id — no point added."""
        wrong_id = self.room1.id + 9999
        _finish_survey(self.char1, [(self.map_item, "room_a")], wrong_id)
        self.assertNotIn("room_a", self.map_item.surveyed_points)

    def test_finish_survey_none_caller_does_not_raise(self):
        try:
            _finish_survey(None, [(self.map_item, "room_a")], self.room1.id)
        except Exception as exc:
            self.fail(f"_finish_survey raised with None caller: {exc}")

    def test_finish_survey_caller_no_location_does_not_raise(self):
        mock_caller = MagicMock()
        mock_caller.location = None
        try:
            _finish_survey(mock_caller, [(self.map_item, "room_a")], self.room1.id)
        except Exception as exc:
            self.fail(f"_finish_survey raised with no location: {exc}")

    def test_finish_survey_caller_no_location_does_not_add_point(self):
        mock_caller = MagicMock()
        mock_caller.location = None
        _finish_survey(mock_caller, [(self.map_item, "room_a")], self.room1.id)
        self.assertNotIn("room_a", self.map_item.surveyed_points)

    def test_finish_survey_direct_call_correct_room(self):
        """Directly calling _finish_survey with correct room adds the point."""
        _finish_survey(self.char1, [(self.map_item, "room_a")], self.room1.id)
        self.assertIn("room_a", self.map_item.surveyed_points)

    @patch("commands.general_skill_cmds.cmd_survey.delay")
    def test_survey_completion_pct_increases(self, mock_delay):
        """After survey, completion_pct should be > 0."""
        mock_delay.side_effect = lambda t, fn, *a, **kw: fn(*a, **kw)
        self.assertEqual(self.map_item.completion_pct, 0)
        self.call(CmdSurvey(), "")
        self.assertGreater(self.map_item.completion_pct, 0)

    @patch("commands.general_skill_cmds.cmd_survey.delay")
    def test_second_survey_same_room_shows_already_mapped(self, mock_delay):
        """Re-surveying an already-surveyed room shows 'already mapped'."""
        mock_delay.side_effect = lambda t, fn, *a, **kw: fn(*a, **kw)
        # First survey
        self.call(CmdSurvey(), "")
        # Second survey on same room
        result = self.call(CmdSurvey(), "")
        self.assertIn("already mapped everything", result)


# ══════════════════════════════════════════════════════════════════════════
#  7. CmdSurvey — Multi-Map
# ══════════════════════════════════════════════════════════════════════════

class TestCmdSurveyMultiMap(_RoomBaseMixin, EvenniaCommandTest):
    """Tests for CmdSurvey when room appears on multiple maps."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        MAP_REGISTRY[FAKE_MAP_KEY] = dict(FAKE_MAP_DEF)
        MAP_REGISTRY[FAKE_MAP_KEY_2] = dict(FAKE_MAP_DEF_2)
        _set_cart(self.char1, MasteryLevel.BASIC)
        self.room1.tags.add(f"{FAKE_MAP_KEY}:room_a", category="map_cell")
        self.room1.tags.add(f"{FAKE_MAP_KEY_2}:region_a", category="map_cell")
        self.map1 = _make_map_item(self.char1, FAKE_MAP_KEY)
        self.map2 = _make_map_item(self.char1, FAKE_MAP_KEY_2)

    def tearDown(self):
        MAP_REGISTRY.pop(FAKE_MAP_KEY, None)
        MAP_REGISTRY.pop(FAKE_MAP_KEY_2, None)
        super().tearDown()

    @patch("commands.general_skill_cmds.cmd_survey.delay")
    def test_both_maps_updated_simultaneously(self, mock_delay):
        mock_delay.side_effect = lambda t, fn, *a, **kw: fn(*a, **kw)
        self.call(CmdSurvey(), "")
        self.assertIn("room_a", self.map1.surveyed_points)
        self.assertIn("region_a", self.map2.surveyed_points)

    @patch("commands.general_skill_cmds.cmd_survey.delay")
    def test_missing_map_in_inventory_skipped_gracefully(self, mock_delay):
        """Tag for a map the player doesn't have is skipped — no crash."""
        mock_delay.side_effect = lambda t, fn, *a, **kw: fn(*a, **kw)
        self.room1.tags.add("_unowned_map:some_point", category="map_cell")
        try:
            self.call(CmdSurvey(), "")
        except Exception as exc:
            self.fail(f"Survey raised with unowned map tag: {exc}")
        # Owned maps still updated
        self.assertIn("room_a", self.map1.surveyed_points)

    @patch("commands.general_skill_cmds.cmd_survey.delay")
    def test_already_surveyed_on_one_map_other_still_updates(self, mock_delay):
        """Pre-surveyed point on map1 doesn't block map2 from updating."""
        mock_delay.side_effect = lambda t, fn, *a, **kw: fn(*a, **kw)
        self.map1.db.surveyed_points = {"room_a"}
        self.call(CmdSurvey(), "")
        self.assertIn("region_a", self.map2.surveyed_points)

    @patch("commands.general_skill_cmds.cmd_survey.delay")
    def test_finish_message_lists_all_updated_maps(self, mock_delay):
        """Completion message should mention both map names."""
        mock_delay.side_effect = lambda t, fn, *a, **kw: fn(*a, **kw)
        result = self.call(CmdSurvey(), "")
        self.assertIn("Test Area", result)
        self.assertIn("Test Region", result)


# ══════════════════════════════════════════════════════════════════════════
#  7b. CmdSurvey — Scale-Aware Adjacent Revelation
# ══════════════════════════════════════════════════════════════════════════

SCALE_DISTRICT_MAP = {
    "key": "_test_scale_district",
    "display_name": "Scale District",
    "scale": "district",
    "template": ".-.",
    "point_cells": {
        "center": {"pos": [(0, 0)], "poi": "road"},
        "east":   {"pos": [(0, 2)], "poi": "road"},
    },
}

SCALE_REGION_MAP = {
    "key": "_test_scale_region",
    "display_name": "Scale Region",
    "scale": "region",
    "template": ". .",
    "point_cells": {
        "area_a": {"pos": [(0, 0)], "poi": "town"},
        "area_b": {"pos": [(0, 2)], "poi": "woods"},
    },
}


class TestCmdSurveyScale(_RoomBaseMixin, EvenniaCommandTest):
    """Tests for scale-aware survey — district reveals adjacents, region does not."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        MAP_REGISTRY[SCALE_DISTRICT_MAP["key"]] = dict(SCALE_DISTRICT_MAP)
        MAP_REGISTRY[SCALE_REGION_MAP["key"]] = dict(SCALE_REGION_MAP)
        _set_cart(self.char1, MasteryLevel.BASIC)

        # room1 tagged as "center" on district map and "area_a" on region map
        self.room1.tags.add(f"{SCALE_DISTRICT_MAP['key']}:center", category="map_cell")
        self.room1.tags.add(f"{SCALE_REGION_MAP['key']}:area_a", category="map_cell")

        # room2 is adjacent (east exit) — tagged as "east" on district and "area_b" on region
        self.room2.tags.add(f"{SCALE_DISTRICT_MAP['key']}:east", category="map_cell")
        self.room2.tags.add(f"{SCALE_REGION_MAP['key']}:area_b", category="map_cell")

        # Create exit from room1 → room2
        create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="east",
            location=self.room1,
            destination=self.room2,
        )

        self.district_map = _make_map_item(self.char1, SCALE_DISTRICT_MAP["key"])
        self.region_map = _make_map_item(self.char1, SCALE_REGION_MAP["key"])

    def tearDown(self):
        MAP_REGISTRY.pop(SCALE_DISTRICT_MAP["key"], None)
        MAP_REGISTRY.pop(SCALE_REGION_MAP["key"], None)
        super().tearDown()

    def test_district_survey_reveals_adjacent(self):
        """District-scale survey reveals the adjacent room's cell."""
        _finish_survey(
            self.char1,
            [(self.district_map, "center")],
            self.room1.id,
        )
        self.assertIn("center", self.district_map.surveyed_points)
        self.assertIn("east", self.district_map.surveyed_points)

    def test_region_survey_does_not_reveal_adjacent(self):
        """Region-scale survey reveals only the current cell, not adjacent."""
        _finish_survey(
            self.char1,
            [(self.region_map, "area_a")],
            self.room1.id,
        )
        self.assertIn("area_a", self.region_map.surveyed_points)
        self.assertNotIn("area_b", self.region_map.surveyed_points)

    def test_no_scale_field_defaults_to_district_behaviour(self):
        """Map without scale field defaults to district (reveals adjacents)."""
        no_scale_map = {
            "key": "_test_no_scale",
            "display_name": "No Scale",
            "template": ".-.",
            "point_cells": {
                "here": {"pos": [(0, 0)], "poi": "road"},
                "there": {"pos": [(0, 2)], "poi": "road"},
            },
        }
        MAP_REGISTRY[no_scale_map["key"]] = no_scale_map
        self.room1.tags.add(f"{no_scale_map['key']}:here", category="map_cell")
        self.room2.tags.add(f"{no_scale_map['key']}:there", category="map_cell")
        map_item = _make_map_item(self.char1, no_scale_map["key"])

        _finish_survey(self.char1, [(map_item, "here")], self.room1.id)
        self.assertIn("here", map_item.surveyed_points)
        self.assertIn("there", map_item.surveyed_points)

        MAP_REGISTRY.pop(no_scale_map["key"], None)

    def test_mixed_scale_survey_reveals_district_not_region(self):
        """Room on both maps: district adjacent revealed, region adjacent not."""
        _finish_survey(
            self.char1,
            [(self.district_map, "center"), (self.region_map, "area_a")],
            self.room1.id,
        )
        # District: both cells revealed
        self.assertIn("east", self.district_map.surveyed_points)
        # Region: only current cell
        self.assertNotIn("area_b", self.region_map.surveyed_points)


# ══════════════════════════════════════════════════════════════════════════
#  8. CmdMap
# ══════════════════════════════════════════════════════════════════════════

class TestCmdMap(_RoomBaseMixin, EvenniaCommandTest):
    """Tests for CmdMap — listing and rendering district maps."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        MAP_REGISTRY[FAKE_MAP_KEY] = dict(FAKE_MAP_DEF)
        MAP_REGISTRY[FAKE_MAP_KEY_2] = dict(FAKE_MAP_DEF_2)

    def tearDown(self):
        MAP_REGISTRY.pop(FAKE_MAP_KEY, None)
        MAP_REGISTRY.pop(FAKE_MAP_KEY_2, None)
        super().tearDown()

    # ── No maps ───────────────────────────────────────────────────────────

    def test_no_maps_in_inventory(self):
        result = self.call(CmdMap(), "")
        self.assertIn("don't have any maps", result)

    # ── List mode (no argument) ───────────────────────────────────────────

    def test_list_mode_shows_header(self):
        _make_map_item(self.char1, FAKE_MAP_KEY)
        result = self.call(CmdMap(), "")
        self.assertIn("Maps in your inventory", result)

    def test_list_mode_shows_map_display_name(self):
        _make_map_item(self.char1, FAKE_MAP_KEY)
        result = self.call(CmdMap(), "")
        self.assertIn("Test Area", result)

    def test_list_mode_shows_pct(self):
        _make_map_item(self.char1, FAKE_MAP_KEY)
        result = self.call(CmdMap(), "")
        self.assertIn("0%", result)

    def test_list_mode_shows_all_maps(self):
        _make_map_item(self.char1, FAKE_MAP_KEY)
        _make_map_item(self.char1, FAKE_MAP_KEY_2)
        result = self.call(CmdMap(), "")
        self.assertIn("Test Area", result)
        self.assertIn("Test Region", result)

    def test_list_mode_shows_nonzero_pct(self):
        _make_map_item(self.char1, FAKE_MAP_KEY, surveyed={"room_a", "room_b"})
        result = self.call(CmdMap(), "")
        self.assertIn("50%", result)

    def test_maps_alias_shows_list(self):
        _make_map_item(self.char1, FAKE_MAP_KEY)
        result = self.call(CmdMap(), "", cmdstring="maps")
        self.assertIn("Maps in your inventory", result)

    # ── Render mode (with argument) ───────────────────────────────────────

    def test_render_mode_match_by_key_substring(self):
        _make_map_item(self.char1, FAKE_MAP_KEY)
        result = self.call(CmdMap(), "_test_cartography")
        self.assertIn("Test Area", result)

    def test_render_mode_match_by_display_name_substring(self):
        _make_map_item(self.char1, FAKE_MAP_KEY)
        result = self.call(CmdMap(), "test area")
        self.assertIn("Test Area", result)

    def test_render_mode_partial_name_match(self):
        _make_map_item(self.char1, FAKE_MAP_KEY)
        result = self.call(CmdMap(), "test")
        self.assertIn("Test Area", result)

    def test_render_mode_case_insensitive(self):
        _make_map_item(self.char1, FAKE_MAP_KEY)
        result = self.call(CmdMap(), "TEST AREA")
        self.assertIn("Test Area", result)

    def test_render_mode_unsurveyed_is_blank(self):
        _make_map_item(self.char1, FAKE_MAP_KEY)  # 0% surveyed
        result = self.call(CmdMap(), "test area")
        self.assertNotIn("░", result)  # no block chars for unsurveyed

    def test_render_mode_surveyed_point_shows_symbol(self):
        _make_map_item(self.char1, FAKE_MAP_KEY, surveyed={"room_a"})
        result = self.call(CmdMap(), "test area")
        # Legacy format uses 'unknown' POI → '?' symbol
        from world.cartography.poi_symbols import POI_SYMBOLS
        self.assertIn(POI_SYMBOLS.get("unknown", "?"), result)

    def test_render_mode_fully_surveyed_no_mask(self):
        all_keys = set(FAKE_MAP_DEF["point_cells"].keys())
        _make_map_item(self.char1, FAKE_MAP_KEY, surveyed=all_keys)
        result = self.call(CmdMap(), "test area")
        self.assertNotIn("░", result)

    def test_render_mode_no_match(self):
        _make_map_item(self.char1, FAKE_MAP_KEY)
        result = self.call(CmdMap(), "completely_nonexistent_area_xyz")
        self.assertIn("don't have a map matching", result)

    def test_render_mode_no_map_def(self):
        """Map item whose key is no longer in registry → 'no template data'."""
        _make_map_item(self.char1, "orphaned_key_xyz")
        result = self.call(CmdMap(), "orphaned_key")
        self.assertIn("no template data", result)

    def test_render_mode_shows_map_name_in_header(self):
        _make_map_item(self.char1, FAKE_MAP_KEY)
        result = self.call(CmdMap(), "test area")
        self.assertIn("Test Area", result)

    def test_render_mode_with_no_maps_shows_no_maps(self):
        result = self.call(CmdMap(), "test area")
        self.assertIn("don't have any maps", result)

    def test_render_mode_first_match_used(self):
        """When multiple maps could match, first match is rendered."""
        _make_map_item(self.char1, FAKE_MAP_KEY)
        _make_map_item(self.char1, FAKE_MAP_KEY_2)
        # Both contain "test" — command renders the first match, no crash
        try:
            result = self.call(CmdMap(), "test")
            self.assertIsNotNone(result)
        except Exception as exc:
            self.fail(f"CmdMap raised with ambiguous match: {exc}")

    # ── Edge cases ────────────────────────────────────────────────────────

    def test_map_with_empty_surveyed_points_renders(self):
        """Map with empty surveyed set should render without errors."""
        _make_map_item(self.char1, FAKE_MAP_KEY, surveyed=set())
        try:
            result = self.call(CmdMap(), "test area")
            self.assertNotIn("░", result)  # blank spaces, not block chars
        except Exception as exc:
            self.fail(f"CmdMap raised with empty surveyed_points: {exc}")

    def test_map_list_one_map(self):
        _make_map_item(self.char1, FAKE_MAP_KEY)
        result = self.call(CmdMap(), "")
        # Should have exactly one map entry
        self.assertEqual(result.count("Map:"), 1)

    def test_map_list_two_maps(self):
        _make_map_item(self.char1, FAKE_MAP_KEY)
        _make_map_item(self.char1, FAKE_MAP_KEY_2)
        result = self.call(CmdMap(), "")
        self.assertEqual(result.count("Map:"), 2)
