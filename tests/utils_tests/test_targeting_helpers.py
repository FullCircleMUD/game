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
    bucket_contents,
    resolve_attack_target_in_combat,
    resolve_attack_target_out_of_combat,
    resolve_character_in_room,
    resolve_container,
    resolve_item_in_source,
    walk_contents,
)


def _make_actor(
    key="bob",
    hp=10,
    leader=None,
    combat_side=None,
    visible=True,
):
    """An actor-shaped mock for attack-target resolver tests.

    - ``hp`` controls p_living (pass hp=0 to simulate dead).
    - ``leader`` is returned by ``get_group_leader()``. A sentinel
      object shared between actors marks them as same-group. None
      means solo / no group.
    - ``combat_side`` builds a ``scripts.get("combat_handler")`` list
      holding one stub handler with ``.combat_side``. None means no
      combat handler attached (bystander).
    - ``visible`` controls ``is_hidden_visible_to``.
    """
    actor = MagicMock()
    actor.key = key
    actor.hp = hp
    actor.get_group_leader = MagicMock(return_value=leader)
    actor.is_hidden_visible_to = MagicMock(return_value=visible)
    scripts = MagicMock()
    if combat_side is None:
        scripts.get = MagicMock(return_value=[])
    else:
        handler = SimpleNamespace(combat_side=combat_side)
        scripts.get = MagicMock(return_value=[handler])
    actor.scripts = scripts
    return actor


def _search_returns_first(name=None, candidates=None, **_kwargs):
    """Side-effect for caller.search: return the first candidate matching ``name``.

    Mimics Evennia's ``caller.search(quiet=True, candidates=[...])``
    closely enough for priority-bucket tests. Does a simple
    case-insensitive substring match against each candidate's ``.key``
    so "no match in this bucket" falls through to the next tier.
    """
    if not candidates or not name:
        return None
    needle = name.lower()
    for obj in candidates:
        key = getattr(obj, "key", None)
        if isinstance(key, str) and needle in key.lower():
            return obj
    return None


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


class TestBucketContents(EvenniaTest):
    """Unit tests for utils.targeting.helpers.bucket_contents.

    bucket_contents is the multi-way partitioning primitive that
    sits alongside walk_contents. It's specifically designed for
    combat-state bucketing (get_sides), AI threat tier classification,
    and multi-faction combat. These tests cover:

    - Source edge cases (None, missing .contents, empty contents)
    - Classifier behaviour (bucket name → bucket, None → skip)
    - Predicate composition (filters short-circuit before key_fn)
    - Multi-bucket partitioning (more than 2 buckets at once)
    - Ordered iteration via priority tuple (the AI threat pattern)
    - Preservation of extra classifier buckets not in order
    """

    def create_script(self):
        pass

    # ── Source edge cases ─────────────────────────────────────────

    def test_source_none_returns_empty_dict(self):
        result = bucket_contents(None, None, lambda o, c: "bucket")
        self.assertEqual(result, {})

    def test_source_without_contents_returns_empty_dict(self):
        source = SimpleNamespace()  # no .contents
        result = bucket_contents(None, source, lambda o, c: "bucket")
        self.assertEqual(result, {})

    def test_empty_contents_returns_empty_dict(self):
        source = SimpleNamespace(contents=[])
        result = bucket_contents(None, source, lambda o, c: "bucket")
        self.assertEqual(result, {})

    # ── Classifier behaviour ──────────────────────────────────────

    def test_single_bucket(self):
        a = _make_item("a")
        b = _make_item("b")
        source = SimpleNamespace(contents=[a, b])
        result = bucket_contents(None, source, lambda o, c: "all")
        self.assertEqual(result, {"all": [a, b]})

    def test_multiple_buckets(self):
        # Classifier bucketing by key attribute
        a = SimpleNamespace(key="red", kind="fruit")
        b = SimpleNamespace(key="blue", kind="veggie")
        c = SimpleNamespace(key="green", kind="veggie")
        source = SimpleNamespace(contents=[a, b, c])

        def classify(obj, _caller):
            return obj.kind

        result = bucket_contents(None, source, classify)
        self.assertEqual(result, {"fruit": [a], "veggie": [b, c]})

    def test_key_fn_returns_none_skips_object(self):
        a = SimpleNamespace(key="a", include=True)
        b = SimpleNamespace(key="b", include=False)
        c = SimpleNamespace(key="c", include=True)
        source = SimpleNamespace(contents=[a, b, c])

        def classify(obj, _caller):
            return "yes" if obj.include else None

        result = bucket_contents(None, source, classify)
        self.assertEqual(result, {"yes": [a, c]})

    # ── Predicate composition ────────────────────────────────────

    def test_predicates_filter_before_classifier(self):
        a = _make_item("a")
        exit_obj = _make_exit()
        source = SimpleNamespace(contents=[a, exit_obj])
        classifier_calls = []

        def classify(obj, _caller):
            classifier_calls.append(obj)
            return "bucket"

        from utils.targeting.predicates import p_not_exit
        result = bucket_contents(None, source, classify, p_not_exit)
        # exit_obj filtered out BEFORE classifier runs
        self.assertEqual(classifier_calls, [a])
        self.assertEqual(result, {"bucket": [a]})

    def test_predicate_short_circuit_before_classifier(self):
        # Cheap predicate False → classifier never called for that obj.
        calls = []

        def cheap_false(obj, caller):  # noqa: ARG001
            calls.append(("predicate", obj.key))
            return False

        def classify(obj, _caller):
            calls.append(("classifier", obj.key))
            return "bucket"

        source = SimpleNamespace(contents=[_make_item("a"), _make_item("b")])
        bucket_contents(None, source, classify, cheap_false)
        # Predicate called twice, classifier never called
        self.assertEqual([c[0] for c in calls], ["predicate", "predicate"])

    # ── Ordered iteration ────────────────────────────────────────

    def test_order_empty_buckets_preserved(self):
        # When order is passed, empty buckets for those names
        # appear in the result. Critical for fall-through priority
        # logic in AI threat selection.
        source = SimpleNamespace(contents=[])
        result = bucket_contents(
            None, source, lambda o, c: "unreachable",
            order=("caster", "healer", "ranged", "melee"),
        )
        self.assertEqual(
            result,
            {"caster": [], "healer": [], "ranged": [], "melee": []},
        )

    def test_order_preserves_priority_sequence(self):
        # Classifier returns buckets out of priority order; the
        # result dict's key order still matches the `order` tuple.
        a = SimpleNamespace(key="a", role="melee")
        b = SimpleNamespace(key="b", role="caster")
        c = SimpleNamespace(key="c", role="ranged")
        source = SimpleNamespace(contents=[a, b, c])

        def classify(obj, _caller):
            return obj.role

        result = bucket_contents(
            None, source, classify,
            order=("caster", "healer", "ranged", "melee"),
        )
        # Dict keys appear in the priority order, not classification order
        self.assertEqual(
            list(result.keys()),
            ["caster", "healer", "ranged", "melee"],
        )
        self.assertEqual(result["caster"], [b])
        self.assertEqual(result["healer"], [])
        self.assertEqual(result["ranged"], [c])
        self.assertEqual(result["melee"], [a])

    def test_order_extra_buckets_appended(self):
        # Classifier produces a bucket name not in `order`.
        # The extra bucket is kept (not dropped) and appears at
        # the end of the result dict.
        a = SimpleNamespace(key="a", role="caster")
        b = SimpleNamespace(key="b", role="beast")  # not in order tuple
        source = SimpleNamespace(contents=[a, b])

        def classify(obj, _caller):
            return obj.role

        result = bucket_contents(
            None, source, classify,
            order=("caster", "healer"),
        )
        # "caster" and "healer" first (in order), "beast" last
        self.assertEqual(list(result.keys()), ["caster", "healer", "beast"])
        self.assertEqual(result["caster"], [a])
        self.assertEqual(result["healer"], [])
        self.assertEqual(result["beast"], [b])

    def test_order_with_none_source_returns_empty_buckets(self):
        # Edge case: None source + order should still honour the
        # order contract so AI fall-through iteration doesn't crash.
        result = bucket_contents(
            None, None, lambda o, c: "unused",
            order=("caster", "healer"),
        )
        self.assertEqual(result, {"caster": [], "healer": []})


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

    def test_quiet_kwarg_forwarded(self):
        item = _make_item("sword")
        caller = _make_caller(search_return=[item])
        source = SimpleNamespace(contents=[item])
        resolve_item_in_source(caller, source, "sword", quiet=True)
        caller.search.assert_called_once()
        _, kwargs = caller.search.call_args
        self.assertTrue(kwargs.get("quiet"))

    def test_exclude_worn_kwarg_forwarded(self):
        item = _make_item("sword")
        caller = _make_caller(search_return=item)
        source = SimpleNamespace(contents=[item])
        resolve_item_in_source(
            caller, source, "sword", quiet=True, exclude_worn=True,
        )
        caller.search.assert_called_once()
        _, kwargs = caller.search.call_args
        self.assertTrue(kwargs.get("quiet"))
        self.assertTrue(kwargs.get("exclude_worn"))


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


class TestResolveAttackTargetOutOfCombat(EvenniaTest):
    """Unit tests for resolve_attack_target_out_of_combat.

    Covers the group-priority classifier: strangers win over
    groupmates even when both match the keyword. Pet and mount are
    treated as groupmates (priority fallback, never preferred).
    """

    def create_script(self):
        pass

    def _caller(self, leader=None, pet=None, mount=None):
        """Build a caller with group/pet/mount state and room."""
        caller = _make_actor(key="me", leader=leader)
        caller.active_pet = pet
        caller.active_mount = mount
        caller.search = MagicMock(side_effect=_search_returns_first)
        return caller

    # ── Source edge cases ─────────────────────────────────────────

    def test_no_location_returns_none(self):
        caller = self._caller()
        caller.location = None
        self.assertIsNone(resolve_attack_target_out_of_combat(caller, "goblin"))

    def test_caller_alone_in_room_returns_none(self):
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[caller])
        self.assertIsNone(resolve_attack_target_out_of_combat(caller, "goblin"))

    # ── Single-bucket matches ────────────────────────────────────

    def test_single_stranger_matches(self):
        caller = self._caller()
        goblin = _make_actor(key="goblin")
        caller.location = SimpleNamespace(contents=[caller, goblin])
        result = resolve_attack_target_out_of_combat(caller, "goblin")
        self.assertIs(result, goblin)

    def test_only_groupmate_still_matches_as_fallback(self):
        # Pet-named "goblin" and nothing else — the groupmate bucket
        # is last priority but still matches when no stranger is
        # available. Player chose to attack their pet explicitly.
        leader = object()
        caller = self._caller(leader=leader)
        groupmate = _make_actor(key="goblin", leader=leader)
        caller.location = SimpleNamespace(contents=[caller, groupmate])
        result = resolve_attack_target_out_of_combat(caller, "goblin")
        self.assertIs(result, groupmate)

    # ── Priority: stranger wins over groupmate ───────────────────

    def test_stranger_wins_over_groupmate_same_name(self):
        leader = object()
        caller = self._caller(leader=leader)
        stranger_goblin = _make_actor(key="goblin")  # no leader = solo
        group_goblin = _make_actor(key="goblin", leader=leader)
        caller.location = SimpleNamespace(
            contents=[caller, group_goblin, stranger_goblin]
        )
        result = resolve_attack_target_out_of_combat(caller, "goblin")
        self.assertIs(result, stranger_goblin)

    def test_pet_goes_to_groupmate_bucket(self):
        pet = _make_actor(key="goblin")  # pet has no leader, caught via active_pet
        caller = self._caller(pet=pet)
        stranger_goblin = _make_actor(key="goblin")
        caller.location = SimpleNamespace(contents=[caller, pet, stranger_goblin])
        # Stranger goblin wins; pet would only match if no stranger.
        result = resolve_attack_target_out_of_combat(caller, "goblin")
        self.assertIs(result, stranger_goblin)

    def test_pet_only_still_matches(self):
        pet = _make_actor(key="goblin")
        caller = self._caller(pet=pet)
        caller.location = SimpleNamespace(contents=[caller, pet])
        result = resolve_attack_target_out_of_combat(caller, "goblin")
        self.assertIs(result, pet)

    def test_mount_goes_to_groupmate_bucket(self):
        mount = _make_actor(key="horse")
        caller = self._caller(mount=mount)
        stranger_horse = _make_actor(key="horse")
        caller.location = SimpleNamespace(contents=[caller, mount, stranger_horse])
        result = resolve_attack_target_out_of_combat(caller, "horse")
        self.assertIs(result, stranger_horse)

    # ── Caller lands in 'self' bucket, last priority ─────────────

    def test_caller_alone_in_room_with_matching_name_returns_self(self):
        # Caller lands in the 'self' bucket. With no stranger or
        # groupmate to match, self is the fallback and the resolver
        # returns the caller. Command layer then emits the friendly
        # self-error.
        caller = self._caller()
        caller.key = "goblin"
        caller.location = SimpleNamespace(contents=[caller])
        result = resolve_attack_target_out_of_combat(caller, "goblin")
        self.assertIs(result, caller)

    def test_stranger_wins_over_self_same_name(self):
        # Self bucket is last priority. Any other match wins. Typing
        # your own name when another actor in the room also matches
        # resolves to that actor, not yourself — the honest UX.
        caller = self._caller()
        caller.key = "goblin"
        stranger_goblin = _make_actor(key="goblin")
        caller.location = SimpleNamespace(contents=[caller, stranger_goblin])
        result = resolve_attack_target_out_of_combat(caller, "goblin")
        self.assertIs(result, stranger_goblin)

    # ── p_living / p_visible_to filter correctly ─────────────────

    def test_dead_stranger_is_filtered(self):
        caller = self._caller()
        dead = _make_actor(key="goblin", hp=0)
        caller.location = SimpleNamespace(contents=[caller, dead])
        self.assertIsNone(resolve_attack_target_out_of_combat(caller, "goblin"))

    def test_hidden_stranger_is_filtered(self):
        caller = self._caller()
        hidden = _make_actor(key="goblin", visible=False)
        caller.location = SimpleNamespace(contents=[caller, hidden])
        self.assertIsNone(resolve_attack_target_out_of_combat(caller, "goblin"))


class TestResolveAttackTargetInCombat(EvenniaTest):
    """Unit tests for resolve_attack_target_in_combat.

    Covers the combat-side priority classifier: enemy > bystander >
    ally. Combat side is read via a stubbed
    ``scripts.get("combat_handler")`` list where each handler has a
    ``.combat_side`` attribute.
    """

    def create_script(self):
        pass

    def _caller(self, combat_side=1):
        """Build a caller currently on the given combat side."""
        caller = _make_actor(key="me", combat_side=combat_side)
        caller.search = MagicMock(side_effect=_search_returns_first)
        return caller

    # ── Source / state edge cases ────────────────────────────────

    def test_no_location_returns_none(self):
        caller = self._caller()
        caller.location = None
        self.assertIsNone(resolve_attack_target_in_combat(caller, "goblin"))

    def test_caller_not_in_combat_returns_none(self):
        caller = _make_actor(key="me", combat_side=None)
        caller.search = MagicMock(side_effect=_search_returns_first)
        goblin = _make_actor(key="goblin", combat_side=2)
        caller.location = SimpleNamespace(contents=[caller, goblin])
        self.assertIsNone(resolve_attack_target_in_combat(caller, "goblin"))

    def test_caller_alone_in_combat_returns_none(self):
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[caller])
        self.assertIsNone(resolve_attack_target_in_combat(caller, "goblin"))

    # ── Priority: enemy > bystander > ally ───────────────────────

    def test_enemy_wins_over_bystander_and_ally(self):
        caller = self._caller(combat_side=1)
        enemy_goblin = _make_actor(key="goblin", combat_side=2)
        bystander_goblin = _make_actor(key="goblin", combat_side=None)
        ally_goblin = _make_actor(key="goblin", combat_side=1)
        caller.location = SimpleNamespace(
            contents=[caller, ally_goblin, bystander_goblin, enemy_goblin]
        )
        result = resolve_attack_target_in_combat(caller, "goblin")
        self.assertIs(result, enemy_goblin)

    def test_bystander_wins_when_no_enemy(self):
        caller = self._caller(combat_side=1)
        bystander_goblin = _make_actor(key="goblin", combat_side=None)
        ally_goblin = _make_actor(key="goblin", combat_side=1)
        caller.location = SimpleNamespace(
            contents=[caller, ally_goblin, bystander_goblin]
        )
        result = resolve_attack_target_in_combat(caller, "goblin")
        self.assertIs(result, bystander_goblin)

    def test_side_zero_handler_classified_as_bystander(self):
        # A combatant with combat_side=0 is a degenerate state but
        # defined as "not on a side"; treated as a bystander.
        caller = self._caller(combat_side=1)
        zero = _make_actor(key="goblin", combat_side=0)
        ally = _make_actor(key="goblin", combat_side=1)
        caller.location = SimpleNamespace(contents=[caller, ally, zero])
        result = resolve_attack_target_in_combat(caller, "goblin")
        self.assertIs(result, zero)

    def test_ally_matches_when_nothing_else(self):
        caller = self._caller(combat_side=1)
        ally_goblin = _make_actor(key="goblin", combat_side=1)
        caller.location = SimpleNamespace(contents=[caller, ally_goblin])
        result = resolve_attack_target_in_combat(caller, "goblin")
        self.assertIs(result, ally_goblin)

    def test_no_match_returns_none(self):
        caller = self._caller(combat_side=1)
        rat = _make_actor(key="rat", combat_side=2)
        caller.location = SimpleNamespace(contents=[caller, rat])
        self.assertIsNone(resolve_attack_target_in_combat(caller, "goblin"))

    # ── Caller lands in 'self' bucket, last priority ─────────────

    def test_caller_alone_in_combat_with_matching_name_returns_self(self):
        # Self is the last-priority fallback. With no enemy,
        # bystander, or ally named "goblin", self wins and the
        # resolver returns caller so the command layer emits the
        # friendly self-error.
        caller = self._caller(combat_side=1)
        caller.key = "goblin"
        caller.location = SimpleNamespace(contents=[caller])
        result = resolve_attack_target_in_combat(caller, "goblin")
        self.assertIs(result, caller)

    def test_enemy_wins_over_self_same_name(self):
        # Enemy tier beats self tier — priority semantics hold for
        # self just like any other bucket.
        caller = self._caller(combat_side=1)
        caller.key = "goblin"
        enemy_goblin = _make_actor(key="goblin", combat_side=2)
        caller.location = SimpleNamespace(contents=[caller, enemy_goblin])
        result = resolve_attack_target_in_combat(caller, "goblin")
        self.assertIs(result, enemy_goblin)

    def test_dead_enemy_is_filtered(self):
        caller = self._caller(combat_side=1)
        dead_enemy = _make_actor(key="goblin", combat_side=2, hp=0)
        caller.location = SimpleNamespace(contents=[caller, dead_enemy])
        self.assertIsNone(resolve_attack_target_in_combat(caller, "goblin"))
