# FullCircleMUD/tests/utils_tests/test_targeting_helpers.py

# TO RUN THIS TEST:
# IN FullCircleMUD/src/game:
#   evennia test --settings settings.py tests.utils_tests.test_targeting_helpers

from types import SimpleNamespace
from unittest.mock import MagicMock

from evennia.objects.objects import DefaultCharacter, DefaultExit
from evennia.utils.test_resources import EvenniaTest

from utils.targeting.helpers import (
    BASE_ITEM_PREDICATES,
    resolve_character_in_room,
    resolve_container,
    resolve_item_in_source,
    walk_contents,
)


def _make_item(key="sword"):
    """A plain item with no mixins — passes all predicates."""
    return SimpleNamespace(key=key)


def _make_character():
    """A mock that passes isinstance(x, DefaultCharacter)."""
    return MagicMock(spec=DefaultCharacter)


def _make_exit():
    """A mock that passes isinstance(x, DefaultExit)."""
    return MagicMock(spec=DefaultExit)


def _make_hidden_item(visible):
    """An item with HiddenObjectMixin-style visibility."""
    return SimpleNamespace(is_hidden_visible_to=lambda caller: visible)


def _make_caller(search_return=None):
    """A caller mock with a stubbed .search() method."""
    caller = MagicMock()
    caller.search.return_value = search_return
    return caller


def _make_container(key="pack", is_open=None):
    """A container-like object (is_container=True).

    If ``is_open`` is not None, the attribute is set explicitly —
    used by tests that verify resolve_container doesn't filter by
    open/closed state.
    """
    kwargs = {"key": key, "is_container": True}
    if is_open is not None:
        kwargs["is_open"] = is_open
    return SimpleNamespace(**kwargs)


def _make_player_character():
    """A mock that passes isinstance(x, FCMCharacter).

    Used by resolve_character_in_room tests to verify the helper
    matches player characters specifically, not generic DefaultCharacter
    subclasses like NPCs or mobs.
    """
    from typeclasses.actors.character import FCMCharacter
    return MagicMock(spec=FCMCharacter)


class TestWalkContents(EvenniaTest):
    """Unit tests for utils.targeting.helpers.walk_contents.

    walk_contents is the core primitive of the library — every
    resolver delegates to it. These tests exercise the primitive
    directly rather than through a specific resolver, so regressions
    in short-circuit eval, None-handling, or predicate composition
    are caught at the right level.
    """

    def create_script(self):
        pass

    # ── Source edge cases ─────────────────────────────────────────

    def test_source_is_none_returns_empty_list(self):
        result = walk_contents(None, None, *BASE_ITEM_PREDICATES)
        self.assertEqual(result, [])

    def test_source_without_contents_returns_empty_list(self):
        source = SimpleNamespace()  # no .contents attribute
        result = walk_contents(None, source, *BASE_ITEM_PREDICATES)
        self.assertEqual(result, [])

    def test_source_with_empty_contents_returns_empty_list(self):
        source = SimpleNamespace(contents=[])
        result = walk_contents(None, source, *BASE_ITEM_PREDICATES)
        self.assertEqual(result, [])

    # ── Predicate composition ─────────────────────────────────────

    def test_no_predicates_returns_all_contents(self):
        # A walk with zero predicates is effectively "give me
        # everything in source.contents". Python's all() over an
        # empty iterable is True, so every object passes.
        a = _make_item("a")
        b = _make_item("b")
        c = _make_item("c")
        source = SimpleNamespace(contents=[a, b, c])
        result = walk_contents(None, source)
        self.assertEqual(result, [a, b, c])

    def test_all_predicates_pass_returns_all_items(self):
        a = _make_item("a")
        b = _make_item("b")
        source = SimpleNamespace(contents=[a, b])
        # BASE_ITEM_PREDICATES filters out actors/exits/hidden — plain
        # SimpleNamespace items pass all three.
        result = walk_contents(None, source, *BASE_ITEM_PREDICATES)
        self.assertEqual(result, [a, b])

    def test_first_predicate_filters_out_object(self):
        item = _make_item("sword")
        character = _make_character()
        source = SimpleNamespace(contents=[item, character])
        result = walk_contents(None, source, *BASE_ITEM_PREDICATES)
        # Character filtered by p_not_actor (first in BASE stack)
        self.assertEqual(result, [item])

    def test_later_predicate_filters_out_object(self):
        visible = _make_item("sword")
        hidden = _make_hidden_item(visible=False)
        source = SimpleNamespace(contents=[visible, hidden])
        result = walk_contents(None, source, *BASE_ITEM_PREDICATES)
        # Hidden item filtered by p_visible_to (last in BASE stack)
        self.assertEqual(result, [visible])

    # ── Short-circuit eval ───────────────────────────────────────

    def test_short_circuit_stops_at_first_false(self):
        # Verifies that walk_contents uses all() with short-circuit
        # evaluation — if the first predicate returns False, later
        # predicates are never called for that object. Matters for
        # efficiency: expensive predicates should never run against
        # objects that fail cheap ones.
        call_log = []

        def cheap_false(obj, caller):  # noqa: ARG001
            call_log.append(("cheap", obj.key))
            return False

        def expensive(obj, caller):  # noqa: ARG001
            call_log.append(("expensive", obj.key))
            return True

        source = SimpleNamespace(contents=[_make_item("a"), _make_item("b")])
        walk_contents(None, source, cheap_false, expensive)

        # Cheap called twice (once per object), expensive never called
        self.assertEqual(
            [entry[0] for entry in call_log],
            ["cheap", "cheap"],
        )

    # ── Custom predicates ─────────────────────────────────────────

    def test_custom_predicate_composable(self):
        # Walk with a one-off custom predicate — verifies the
        # primitive doesn't assume BASE_ITEM_PREDICATES.
        a = SimpleNamespace(key="a", weight=5)
        b = SimpleNamespace(key="b", weight=15)
        c = SimpleNamespace(key="c", weight=10)
        source = SimpleNamespace(contents=[a, b, c])

        def p_lighter_than_10(obj, caller):  # noqa: ARG001
            return obj.weight < 10

        result = walk_contents(None, source, p_lighter_than_10)
        self.assertEqual(result, [a])


class TestResolveItemInSource(EvenniaTest):
    """Unit tests for utils.targeting.helpers.resolve_item_in_source."""

    def create_script(self):
        # Skip EvenniaTest's default script creation — FCM has no
        # typeclasses.scripts.Script at that path and these tests
        # don't need any script fixture.
        pass

    # ── Source edge cases ─────────────────────────────────────────
    #
    # All three edge cases (None source, source without .contents,
    # source with empty .contents) produce an empty candidate list
    # from walk_contents. The helper forwards the empty list to
    # caller.search unconditionally — caller.search handles empty
    # candidates correctly, firing any nofound_string kwarg or the
    # default "not found" error, then returning None. An earlier
    # version of the helper short-circuited on empty candidates
    # and silently suppressed the error messaging; these tests
    # lock in the fix by asserting caller.search IS called (with
    # candidates=[]) in all three cases.

    def test_source_is_none_delegates_with_empty_candidates(self):
        caller = _make_caller()
        result = resolve_item_in_source(caller, None, "sword")
        self.assertIsNone(result)
        caller.search.assert_called_once()
        _, kwargs = caller.search.call_args
        self.assertEqual(kwargs["candidates"], [])

    def test_source_without_contents_delegates_with_empty_candidates(self):
        caller = _make_caller()
        source = SimpleNamespace()  # no .contents attribute
        result = resolve_item_in_source(caller, source, "sword")
        self.assertIsNone(result)
        caller.search.assert_called_once()
        _, kwargs = caller.search.call_args
        self.assertEqual(kwargs["candidates"], [])

    def test_source_with_empty_contents_delegates_with_empty_candidates(self):
        caller = _make_caller()
        source = SimpleNamespace(contents=[])
        result = resolve_item_in_source(caller, source, "sword")
        self.assertIsNone(result)
        caller.search.assert_called_once()
        _, kwargs = caller.search.call_args
        self.assertEqual(kwargs["candidates"], [])

    def test_nofound_string_forwarded_on_empty_candidates(self):
        # Regression test for the silent-return bug: when source
        # yields no candidates, nofound_string must still reach
        # caller.search so Evennia's error messaging fires. Before
        # the fix, the helper short-circuited before caller.search
        # was called, silently dropping nofound_string and showing
        # no error to the player. This test locks the fix in place.
        caller = _make_caller()
        source = SimpleNamespace(contents=[])
        resolve_item_in_source(
            caller, source, "sword",
            nofound_string="You aren't carrying sword.",
        )
        caller.search.assert_called_once()
        _, kwargs = caller.search.call_args
        self.assertEqual(
            kwargs.get("nofound_string"),
            "You aren't carrying sword.",
        )

    # ── Happy path ────────────────────────────────────────────────

    def test_matching_item_returned(self):
        sword = _make_item("sword")
        caller = _make_caller(search_return=sword)
        source = SimpleNamespace(contents=[sword])
        result = resolve_item_in_source(caller, source, "sword")
        self.assertIs(result, sword)

    # ── Filter exclusions ─────────────────────────────────────────
    #
    # These three tests assert that the base item predicates
    # (p_not_actor, p_not_exit, p_visible_to) filter the named
    # object OUT of the candidate list. After filtering, candidates
    # is empty and the helper delegates to caller.search with
    # candidates=[] (which fires any nofound_string or default
    # error and returns None).

    def test_character_excluded_from_candidates(self):
        character = _make_character()
        caller = _make_caller()
        source = SimpleNamespace(contents=[character])
        result = resolve_item_in_source(caller, source, "anything")
        self.assertIsNone(result)
        caller.search.assert_called_once()
        _, kwargs = caller.search.call_args
        self.assertNotIn(character, kwargs["candidates"])

    def test_exit_excluded_from_candidates(self):
        exit_obj = _make_exit()
        caller = _make_caller()
        source = SimpleNamespace(contents=[exit_obj])
        result = resolve_item_in_source(caller, source, "anything")
        self.assertIsNone(result)
        caller.search.assert_called_once()
        _, kwargs = caller.search.call_args
        self.assertNotIn(exit_obj, kwargs["candidates"])

    def test_hidden_item_excluded_when_mixin_returns_false(self):
        hidden = _make_hidden_item(visible=False)
        caller = _make_caller()
        source = SimpleNamespace(contents=[hidden])
        result = resolve_item_in_source(caller, source, "anything")
        self.assertIsNone(result)
        caller.search.assert_called_once()
        _, kwargs = caller.search.call_args
        self.assertNotIn(hidden, kwargs["candidates"])

    def test_hidden_item_included_when_mixin_returns_true(self):
        visible_hidden = _make_hidden_item(visible=True)
        caller = _make_caller(search_return=visible_hidden)
        source = SimpleNamespace(contents=[visible_hidden])
        resolve_item_in_source(caller, source, "anything")
        caller.search.assert_called_once()
        _, kwargs = caller.search.call_args
        self.assertIn(visible_hidden, kwargs["candidates"])

    def test_plain_visible_item_included(self):
        item = _make_item("sword")
        caller = _make_caller(search_return=item)
        source = SimpleNamespace(contents=[item])
        resolve_item_in_source(caller, source, "sword")
        caller.search.assert_called_once()
        _, kwargs = caller.search.call_args
        self.assertIn(item, kwargs["candidates"])

    # ── No match ──────────────────────────────────────────────────

    def test_no_match_returns_none(self):
        item = _make_item("sword")
        caller = _make_caller(search_return=None)
        source = SimpleNamespace(contents=[item])
        result = resolve_item_in_source(caller, source, "hammer")
        self.assertIsNone(result)

    # ── Source variations ────────────────────────────────────────

    def test_container_as_source(self):
        potion = _make_item("potion")
        caller = _make_caller(search_return=potion)
        chest = SimpleNamespace(contents=[potion])
        result = resolve_item_in_source(caller, chest, "potion")
        self.assertIs(result, potion)

    def test_caller_as_source_for_inventory_lookup(self):
        scroll = _make_item("scroll")
        caller = MagicMock()
        caller.contents = [scroll]
        caller.search = MagicMock(return_value=scroll)
        result = resolve_item_in_source(caller, caller, "scroll")
        self.assertIs(result, scroll)

    # ── Kwarg forwarding ─────────────────────────────────────────

    def test_stacked_kwarg_forwarded(self):
        coin = _make_item("coin")
        caller = _make_caller(search_return=[coin, coin, coin])
        source = SimpleNamespace(contents=[coin])
        resolve_item_in_source(caller, source, "coin", stacked=3)
        caller.search.assert_called_once()
        _, kwargs = caller.search.call_args
        self.assertEqual(kwargs.get("stacked"), 3)


class TestResolveContainer(EvenniaTest):
    """Unit tests for utils.targeting.helpers.resolve_container."""

    def create_script(self):
        pass

    # ── Happy paths ──────────────────────────────────────────────

    def test_container_in_inventory_returned(self):
        pack = _make_container("pack")
        caller = MagicMock()
        caller.contents = [pack]
        caller.location = SimpleNamespace(contents=[])
        caller.search = MagicMock(return_value=pack)
        result = resolve_container(caller, "pack")
        self.assertIs(result, pack)

    def test_container_in_room_returned_when_inventory_empty(self):
        chest = _make_container("chest")
        caller = MagicMock()
        caller.contents = []
        caller.location = SimpleNamespace(contents=[chest])
        # Inventory is empty so the helper skips that scope entirely
        # (no candidates → no search call). Only the room scope runs.
        caller.search = MagicMock(return_value=chest)
        result = resolve_container(caller, "chest")
        self.assertIs(result, chest)
        self.assertEqual(caller.search.call_count, 1)

    def test_inventory_wins_over_room_when_both_match(self):
        inv_pack = _make_container("pack")
        room_pack = _make_container("pack")
        caller = MagicMock()
        caller.contents = [inv_pack]
        caller.location = SimpleNamespace(contents=[room_pack])
        caller.search = MagicMock(return_value=inv_pack)
        result = resolve_container(caller, "pack")
        self.assertIs(result, inv_pack)
        # Only one call — fell out on inventory success, never looked at room
        self.assertEqual(caller.search.call_count, 1)

    # ── Fallback through to room ─────────────────────────────────

    def test_inventory_has_non_matching_container_falls_through_to_room(self):
        inv_pack = _make_container("pack")
        room_chest = _make_container("chest")
        caller = MagicMock()
        caller.contents = [inv_pack]
        caller.location = SimpleNamespace(contents=[room_chest])
        # Inventory call returns None (pack doesn't match "chest"),
        # room call returns the chest.
        caller.search = MagicMock(side_effect=[None, room_chest])
        result = resolve_container(caller, "chest")
        self.assertIs(result, room_chest)

    # ── None cases ───────────────────────────────────────────────

    def test_no_container_anywhere_returns_none(self):
        caller = MagicMock()
        caller.contents = []
        caller.location = SimpleNamespace(contents=[])
        caller.search = MagicMock(return_value=None)
        result = resolve_container(caller, "pack")
        self.assertIsNone(result)

    def test_caller_with_no_location_searches_inventory_only(self):
        pack = _make_container("pack")
        caller = MagicMock()
        caller.contents = [pack]
        caller.location = None
        caller.search = MagicMock(return_value=pack)
        result = resolve_container(caller, "pack")
        self.assertIs(result, pack)
        # Only one call — no room to fall back to
        self.assertEqual(caller.search.call_count, 1)

    # ── Filter: non-containers excluded ──────────────────────────

    def test_non_container_with_matching_name_excluded(self):
        sword = _make_item("pack")  # item named "pack" but is_container absent
        caller = MagicMock()
        caller.contents = [sword]
        caller.location = SimpleNamespace(contents=[])
        # resolve_container filters sword out before calling search;
        # candidates list is empty, so search is never called.
        caller.search = MagicMock(return_value=None)
        result = resolve_container(caller, "pack")
        self.assertIsNone(result)
        caller.search.assert_not_called()

    # ── Filter: hidden containers excluded ───────────────────────

    def test_hidden_container_excluded_by_base_filter(self):
        hidden_chest = SimpleNamespace(
            key="chest",
            is_container=True,
            is_hidden_visible_to=lambda caller: False,
        )
        caller = MagicMock()
        caller.contents = []
        caller.location = SimpleNamespace(contents=[hidden_chest])
        caller.search = MagicMock(return_value=None)
        result = resolve_container(caller, "chest")
        self.assertIsNone(result)
        # Both scopes have empty candidates after filtering — no search call
        caller.search.assert_not_called()

    # ── Non-gating: closed containers ARE returned ───────────────

    def test_closed_container_still_returned(self):
        # Explicitly tests that resolve_container does NOT filter by
        # is_open. A closed chest must still be found so picklock /
        # smash / etc. can operate on it.
        closed_chest = _make_container("chest", is_open=False)
        caller = MagicMock()
        caller.contents = [closed_chest]
        caller.location = SimpleNamespace(contents=[])
        caller.search = MagicMock(return_value=closed_chest)
        result = resolve_container(caller, "chest")
        self.assertIs(result, closed_chest)


class TestResolveCharacterInRoom(EvenniaTest):
    """Unit tests for utils.targeting.helpers.resolve_character_in_room."""

    def create_script(self):
        pass

    # ── Happy path ────────────────────────────────────────────────

    def test_player_character_in_room_returned(self):
        pc = _make_player_character()
        caller = MagicMock()
        caller.location = SimpleNamespace(contents=[pc])
        caller.search = MagicMock(return_value=pc)
        result = resolve_character_in_room(caller, "bob")
        self.assertIs(result, pc)

    # ── Filter: non-characters excluded ───────────────────────────

    def test_generic_default_character_excluded(self):
        # An NPC / mob / pet is a DefaultCharacter but NOT an
        # FCMCharacter — p_is_character should filter it out.
        npc = MagicMock(spec=DefaultCharacter)
        caller = MagicMock()
        caller.location = SimpleNamespace(contents=[npc])
        caller.search = MagicMock(return_value=None)
        result = resolve_character_in_room(caller, "bob")
        self.assertIsNone(result)
        # Empty candidates after filtering — search never called
        caller.search.assert_not_called()

    def test_plain_object_excluded(self):
        item = _make_item("bob")
        caller = MagicMock()
        caller.location = SimpleNamespace(contents=[item])
        caller.search = MagicMock(return_value=None)
        result = resolve_character_in_room(caller, "bob")
        self.assertIsNone(result)
        caller.search.assert_not_called()

    # ── Edge cases ────────────────────────────────────────────────

    def test_no_location_returns_none(self):
        caller = MagicMock()
        caller.location = None
        caller.search = MagicMock()
        result = resolve_character_in_room(caller, "bob")
        self.assertIsNone(result)
        caller.search.assert_not_called()

    def test_empty_room_returns_none(self):
        caller = MagicMock()
        caller.location = SimpleNamespace(contents=[])
        caller.search = MagicMock(return_value=None)
        result = resolve_character_in_room(caller, "bob")
        self.assertIsNone(result)
        caller.search.assert_not_called()

    # ── Policy: caller is NOT excluded by the helper ─────────────

    def test_caller_is_returned_if_they_match(self):
        # resolve_character_in_room deliberately does NOT exclude the
        # caller. Commands that want "not self" apply that check in
        # the command layer so they can emit a specific error. This
        # test locks in that non-exclusion so future edits don't
        # silently break the contract.
        caller_pc = _make_player_character()
        caller_pc.location = SimpleNamespace(contents=[caller_pc])
        caller_pc.search = MagicMock(return_value=caller_pc)
        result = resolve_character_in_room(caller_pc, "bob")
        self.assertIs(result, caller_pc)
