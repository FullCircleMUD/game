# FullCircleMUD/tests/utils_tests/test_targeting_helpers.py

# TO RUN THIS TEST:
# IN FullCircleMUD/src/game:
#   evennia test --settings settings.py tests.utils_tests.test_targeting_helpers

from types import SimpleNamespace
from unittest.mock import MagicMock

from evennia.objects.objects import DefaultCharacter, DefaultExit
from evennia.utils.test_resources import EvenniaTest

from utils.targeting.helpers import (
    bucket_contents,
    resolve_attack_target_in_combat,
    resolve_attack_target_out_of_combat,
    resolve_character_in_room,
    resolve_container,
    resolve_friendly_target_in_combat,
    resolve_friendly_target_out_of_combat,
    resolve_item_in_source,
    resolve_target,
    walk_contents,
)
from utils.targeting.predicates import p_not_actor, p_not_exit, p_visible_to


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


def _make_gettable_item(key="sword"):
    """An item that passes the get lock (access("get") returns True)."""
    obj = SimpleNamespace(key=key)
    obj.access = lambda caller, access_type, **kw: access_type == "get"
    return obj


def _make_fixed_item(key="chest"):
    """An item that fails the get lock (access("get") returns False)."""
    obj = SimpleNamespace(key=key)
    obj.access = lambda caller, access_type, **kw: access_type != "get"
    return obj


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
        result = walk_contents(None, None, p_not_actor, p_not_exit, p_visible_to)
        self.assertEqual(result, [])

    def test_source_without_contents_returns_empty_list(self):
        source = SimpleNamespace()  # no .contents attribute
        result = walk_contents(None, source, p_not_actor, p_not_exit, p_visible_to)
        self.assertEqual(result, [])

    def test_source_with_empty_contents_returns_empty_list(self):
        source = SimpleNamespace(contents=[])
        result = walk_contents(None, source, p_not_actor, p_not_exit, p_visible_to)
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
        # p_not_actor, p_not_exit, p_visible_to filters out
        # actors/exits/hidden — plain SimpleNamespace items pass all three.
        result = walk_contents(None, source, p_not_actor, p_not_exit, p_visible_to)
        self.assertEqual(result, [a, b])

    def test_first_predicate_filters_out_object(self):
        item = _make_item("sword")
        character = _make_character()
        source = SimpleNamespace(contents=[item, character])
        result = walk_contents(None, source, p_not_actor, p_not_exit, p_visible_to)
        # Character filtered by p_not_actor (first predicate)
        self.assertEqual(result, [item])

    def test_later_predicate_filters_out_object(self):
        visible = _make_item("sword")
        hidden = _make_hidden_item(visible=False)
        source = SimpleNamespace(contents=[visible, hidden])
        result = walk_contents(None, source, p_not_actor, p_not_exit, p_visible_to)
        # Hidden item filtered by p_visible_to (last predicate)
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
        # primitive doesn't assume any default predicate stack.
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

    def _caller(self, leader=None):
        """Build a caller with group state and room."""
        caller = _make_actor(key="me", leader=leader)
        caller.search = MagicMock(side_effect=_search_returns_first)
        return caller

    def _make_pet(self, key="goblin", owner_key="me"):
        """Build a pet-shaped mock owned by the caller."""
        pet = _make_actor(key=key)
        pet.is_pet = True
        pet.owner_key = owner_key
        return pet

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
        caller = self._caller()
        pet = self._make_pet(key="goblin", owner_key=caller.key)
        stranger_goblin = _make_actor(key="goblin")
        caller.location = SimpleNamespace(contents=[caller, pet, stranger_goblin])
        # Stranger goblin wins; pet would only match if no stranger.
        result = resolve_attack_target_out_of_combat(caller, "goblin")
        self.assertIs(result, stranger_goblin)

    def test_pet_only_still_matches(self):
        caller = self._caller()
        pet = self._make_pet(key="goblin", owner_key=caller.key)
        caller.location = SimpleNamespace(contents=[caller, pet])
        result = resolve_attack_target_out_of_combat(caller, "goblin")
        self.assertIs(result, pet)

    def test_mount_goes_to_groupmate_bucket(self):
        """Mounts are pets (is_pet=True via BasePet) — same groupmate classification."""
        caller = self._caller()
        mount = self._make_pet(key="horse", owner_key=caller.key)
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


class TestActorCombatBuildingBlocks(EvenniaTest):
    """Tests for actors_in_combat and actors_not_in_combat building blocks."""

    def create_script(self):
        pass

    def _caller(self):
        caller = _make_actor(key="me")
        caller.search = MagicMock(side_effect=_search_returns_first)
        return caller

    def test_actors_in_combat_finds_combatant(self):
        caller = self._caller()
        goblin = _make_actor(key="goblin", combat_side=1)
        caller.location = SimpleNamespace(contents=[caller, goblin])
        target, _ = resolve_target(caller, "goblin", "actors_in_combat")
        self.assertIs(target, goblin)

    def test_actors_in_combat_skips_idle(self):
        caller = self._caller()
        goblin = _make_actor(key="goblin", combat_side=None)
        caller.location = SimpleNamespace(contents=[caller, goblin])
        target, _ = resolve_target(caller, "goblin", "actors_in_combat")
        self.assertIsNone(target)

    def test_actors_in_combat_skips_dead(self):
        caller = self._caller()
        goblin = _make_actor(key="goblin", hp=0, combat_side=1)
        caller.location = SimpleNamespace(contents=[caller, goblin])
        target, _ = resolve_target(caller, "goblin", "actors_in_combat")
        self.assertIsNone(target)

    def test_actors_not_in_combat_finds_idle(self):
        caller = self._caller()
        bob = _make_actor(key="bob", combat_side=None)
        caller.location = SimpleNamespace(contents=[caller, bob])
        target, _ = resolve_target(caller, "bob", "actors_not_in_combat")
        self.assertIs(target, bob)

    def test_actors_not_in_combat_skips_combatant(self):
        caller = self._caller()
        bob = _make_actor(key="bob", combat_side=1)
        caller.location = SimpleNamespace(contents=[caller, bob])
        target, _ = resolve_target(caller, "bob", "actors_not_in_combat")
        self.assertIsNone(target)

    def test_actors_in_combat_no_location(self):
        caller = self._caller()
        caller.location = None
        target, _ = resolve_target(caller, "goblin", "actors_in_combat")
        self.assertIsNone(target)

    def test_actors_not_in_combat_no_location(self):
        caller = self._caller()
        caller.location = None
        target, _ = resolve_target(caller, "bob", "actors_not_in_combat")
        self.assertIsNone(target)


class TestResolveFriendlyTargetInCombat(EvenniaTest):
    """Tests for resolve_friendly_target_in_combat.

    Reversed priority: self > ally > bystander > enemy.
    Verifies that friendly-intent targeting prefers allies over enemies.
    """

    def create_script(self):
        pass

    def _caller(self, combat_side=1):
        caller = _make_actor(key="me", combat_side=combat_side)
        caller.search = MagicMock(side_effect=_search_returns_first)
        return caller

    def test_ally_wins_over_enemy_same_name(self):
        caller = self._caller(combat_side=1)
        ally_goblin = _make_actor(key="goblin", combat_side=1)
        enemy_goblin = _make_actor(key="goblin", combat_side=2)
        caller.location = SimpleNamespace(
            contents=[caller, enemy_goblin, ally_goblin]
        )
        result = resolve_friendly_target_in_combat(caller, "goblin")
        self.assertIs(result, ally_goblin)

    def test_self_wins_over_ally(self):
        caller = self._caller(combat_side=1)
        caller.key = "goblin"
        ally_goblin = _make_actor(key="goblin", combat_side=1)
        caller.location = SimpleNamespace(contents=[caller, ally_goblin])
        result = resolve_friendly_target_in_combat(caller, "goblin")
        self.assertIs(result, caller)

    def test_bystander_wins_over_enemy(self):
        caller = self._caller(combat_side=1)
        bystander = _make_actor(key="goblin", combat_side=None)
        enemy = _make_actor(key="goblin", combat_side=2)
        caller.location = SimpleNamespace(contents=[caller, enemy, bystander])
        result = resolve_friendly_target_in_combat(caller, "goblin")
        self.assertIs(result, bystander)

    def test_enemy_still_matches_as_last_resort(self):
        caller = self._caller(combat_side=1)
        enemy = _make_actor(key="goblin", combat_side=2)
        caller.location = SimpleNamespace(contents=[caller, enemy])
        result = resolve_friendly_target_in_combat(caller, "goblin")
        self.assertIs(result, enemy)

    def test_no_match_returns_none(self):
        caller = self._caller(combat_side=1)
        rat = _make_actor(key="rat", combat_side=2)
        caller.location = SimpleNamespace(contents=[caller, rat])
        result = resolve_friendly_target_in_combat(caller, "goblin")
        self.assertIsNone(result)

    def test_caller_not_in_combat_returns_none(self):
        caller = _make_actor(key="me", combat_side=None)
        caller.search = MagicMock(side_effect=_search_returns_first)
        goblin = _make_actor(key="goblin", combat_side=1)
        caller.location = SimpleNamespace(contents=[caller, goblin])
        result = resolve_friendly_target_in_combat(caller, "goblin")
        self.assertIsNone(result)


class TestResolveFriendlyTargetOutOfCombat(EvenniaTest):
    """Tests for resolve_friendly_target_out_of_combat.

    Reversed priority: self > groupmate > stranger.
    Verifies that friendly-intent targeting prefers self and group.
    """

    def create_script(self):
        pass

    def _caller(self, leader=None):
        caller = _make_actor(key="me", leader=leader)
        caller.search = MagicMock(side_effect=_search_returns_first)
        return caller

    def _make_pet(self, key="goblin", owner_key="me"):
        pet = _make_actor(key=key)
        pet.is_pet = True
        pet.owner_key = owner_key
        return pet

    def test_self_wins_over_groupmate(self):
        leader = object()
        caller = self._caller(leader=leader)
        caller.key = "goblin"
        groupmate = _make_actor(key="goblin", leader=leader)
        caller.location = SimpleNamespace(contents=[caller, groupmate])
        result = resolve_friendly_target_out_of_combat(caller, "goblin")
        self.assertIs(result, caller)

    def test_groupmate_wins_over_stranger(self):
        leader = object()
        caller = self._caller(leader=leader)
        groupmate = _make_actor(key="goblin", leader=leader)
        stranger = _make_actor(key="goblin")
        caller.location = SimpleNamespace(contents=[caller, stranger, groupmate])
        result = resolve_friendly_target_out_of_combat(caller, "goblin")
        self.assertIs(result, groupmate)

    def test_pet_classified_as_groupmate(self):
        caller = self._caller()
        pet = self._make_pet(key="goblin", owner_key=caller.key)
        stranger = _make_actor(key="goblin")
        caller.location = SimpleNamespace(contents=[caller, stranger, pet])
        result = resolve_friendly_target_out_of_combat(caller, "goblin")
        self.assertIs(result, pet)

    def test_stranger_matches_as_last_resort(self):
        caller = self._caller()
        stranger = _make_actor(key="goblin")
        caller.location = SimpleNamespace(contents=[caller, stranger])
        result = resolve_friendly_target_out_of_combat(caller, "goblin")
        self.assertIs(result, stranger)

    def test_no_match_returns_none(self):
        caller = self._caller()
        rat = _make_actor(key="rat")
        caller.location = SimpleNamespace(contents=[caller, rat])
        result = resolve_friendly_target_out_of_combat(caller, "goblin")
        self.assertIsNone(result)

    def test_no_location_returns_none(self):
        caller = self._caller()
        caller.location = None
        result = resolve_friendly_target_out_of_combat(caller, "goblin")
        self.assertIsNone(result)


class TestActorsInCombatThenNotInCombat(EvenniaTest):
    """Tests for actors_in_combat_then_not_in_combat target_type.

    Composite: finds in-combat actors first, falls back to idle actors.
    """

    def create_script(self):
        pass

    def _caller(self):
        caller = _make_actor(key="me")
        caller.search = MagicMock(side_effect=_search_returns_first)
        return caller

    def test_in_combat_actor_found_first(self):
        caller = self._caller()
        fighting = _make_actor(key="goblin", combat_side=1)
        idle = _make_actor(key="goblin", combat_side=None)
        caller.location = SimpleNamespace(contents=[caller, idle, fighting])
        target, _ = resolve_target(caller, "goblin", "actors_in_combat_then_not_in_combat")
        self.assertIs(target, fighting)

    def test_falls_back_to_idle_when_no_combatant_matches(self):
        caller = self._caller()
        idle = _make_actor(key="goblin", combat_side=None)
        caller.location = SimpleNamespace(contents=[caller, idle])
        target, _ = resolve_target(caller, "goblin", "actors_in_combat_then_not_in_combat")
        self.assertIs(target, idle)

    def test_no_match_returns_none(self):
        caller = self._caller()
        rat = _make_actor(key="rat", combat_side=1)
        caller.location = SimpleNamespace(contents=[caller, rat])
        target, _ = resolve_target(caller, "goblin", "actors_in_combat_then_not_in_combat")
        self.assertIsNone(target)

    def test_no_location_returns_none(self):
        caller = self._caller()
        caller.location = None
        target, _ = resolve_target(caller, "goblin", "actors_in_combat_then_not_in_combat")
        self.assertIsNone(target)

    def test_dead_actors_filtered_from_both_steps(self):
        caller = self._caller()
        dead_fighting = _make_actor(key="goblin", hp=0, combat_side=1)
        dead_idle = _make_actor(key="goblin", hp=0, combat_side=None)
        caller.location = SimpleNamespace(contents=[caller, dead_fighting, dead_idle])
        target, _ = resolve_target(caller, "goblin", "actors_in_combat_then_not_in_combat")
        self.assertIsNone(target)


class TestResolveTargetActorRouting(EvenniaTest):
    """Tests for resolve_target routing: self, none, actor_hostile, actor_friendly."""

    def create_script(self):
        pass

    def _caller(self, combat_side=None, leader=None):
        caller = _make_actor(key="me", combat_side=combat_side, leader=leader)
        caller.search = MagicMock(side_effect=_search_returns_first)
        caller.msg = MagicMock()
        return caller

    # ── self target_type ─────────────────────────────────────────

    def test_self_returns_caller(self):
        caller = self._caller()
        target, secondaries = resolve_target(caller, "", "self")
        self.assertIs(target, caller)
        self.assertEqual(secondaries, [])

    def test_self_ignores_target_str(self):
        caller = self._caller()
        target, _ = resolve_target(caller, "goblin", "self")
        self.assertIs(target, caller)

    # ── none target_type ─────────────────────────────────────────

    def test_none_returns_none(self):
        caller = self._caller()
        target, secondaries = resolve_target(caller, "", "none")
        self.assertIsNone(target)
        self.assertEqual(secondaries, [])

    # ── actor_hostile ────────────────────────────────────────────

    def test_actor_hostile_finds_enemy_in_combat(self):
        caller = self._caller(combat_side=1)
        goblin = _make_actor(key="goblin", combat_side=2)
        caller.location = SimpleNamespace(contents=[caller, goblin])
        target, _ = resolve_target(caller, "goblin", "actor_hostile")
        self.assertIs(target, goblin)

    def test_actor_hostile_finds_stranger_out_of_combat(self):
        caller = self._caller()
        goblin = _make_actor(key="goblin")
        caller.location = SimpleNamespace(contents=[caller, goblin])
        target, _ = resolve_target(caller, "goblin", "actor_hostile")
        self.assertIs(target, goblin)

    def test_actor_hostile_no_target_str_sends_error(self):
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[caller])
        target, _ = resolve_target(caller, "", "actor_hostile")
        self.assertIsNone(target)
        caller.msg.assert_called()

    def test_actor_hostile_no_match_sends_error(self):
        caller = self._caller()
        rat = _make_actor(key="rat")
        caller.location = SimpleNamespace(contents=[caller, rat])
        target, _ = resolve_target(caller, "goblin", "actor_hostile")
        self.assertIsNone(target)
        caller.msg.assert_called_with("There's no 'goblin' here.")

    def test_actor_hostile_returns_self_for_command_layer_rejection(self):
        """Self-targeting via 'me' keyword — resolver returns caller,
        command layer decides whether to reject."""
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[caller])
        target, _ = resolve_target(caller, "me", "actor_hostile")
        self.assertIs(target, caller)

    # ── actor_any ────────────────────────────────────────────────

    def test_actor_any_same_as_hostile(self):
        caller = self._caller()
        goblin = _make_actor(key="goblin")
        caller.location = SimpleNamespace(contents=[caller, goblin])
        target, _ = resolve_target(caller, "goblin", "actor_any")
        self.assertIs(target, goblin)

    # ── actor_friendly ───────────────────────────────────────────

    def test_actor_friendly_empty_target_defaults_to_self(self):
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[caller])
        target, _ = resolve_target(caller, "", "actor_friendly")
        self.assertIs(target, caller)

    def test_actor_friendly_finds_ally_in_combat(self):
        caller = self._caller(combat_side=1)
        ally = _make_actor(key="bob", combat_side=1)
        caller.location = SimpleNamespace(contents=[caller, ally])
        target, _ = resolve_target(caller, "bob", "actor_friendly")
        self.assertIs(target, ally)

    def test_actor_friendly_finds_groupmate_out_of_combat(self):
        leader = object()
        caller = self._caller(leader=leader)
        groupmate = _make_actor(key="bob", leader=leader)
        caller.location = SimpleNamespace(contents=[caller, groupmate])
        target, _ = resolve_target(caller, "bob", "actor_friendly")
        self.assertIs(target, groupmate)

    def test_actor_friendly_no_match_sends_error(self):
        caller = self._caller()
        rat = _make_actor(key="rat")
        caller.location = SimpleNamespace(contents=[caller, rat])
        target, _ = resolve_target(caller, "goblin", "actor_friendly")
        self.assertIsNone(target)
        caller.msg.assert_called_with("There's no 'goblin' here.")

    # ── unknown target_type ──────────────────────────────────────

    def test_unknown_target_type_sends_error(self):
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[caller])
        target, _ = resolve_target(caller, "goblin", "bogus_type")
        self.assertIsNone(target)
        caller.msg.assert_called_with("Unknown target type 'bogus_type'.")


class TestResolveTargetInventoryItems(EvenniaTest):
    """Tests for resolve_target items_inventory and items_equipped."""

    def create_script(self):
        pass

    def _caller(self):
        caller = MagicMock()
        caller.msg = MagicMock()
        caller.location = SimpleNamespace(contents=[])
        return caller

    # ── items_inventory ──────────────────────────────────────────

    def test_items_inventory_finds_item(self):
        sword = _make_item("sword")
        caller = self._caller()
        caller.contents = [sword]
        caller.search = MagicMock(return_value=sword)
        target, _ = resolve_target(caller, "sword", "items_inventory")
        self.assertIs(target, sword)

    def test_items_inventory_passes_exclude_worn(self):
        sword = _make_item("sword")
        caller = self._caller()
        caller.contents = [sword]
        caller.search = MagicMock(return_value=sword)
        resolve_target(caller, "sword", "items_inventory")
        _, kwargs = caller.search.call_args
        self.assertTrue(kwargs.get("exclude_worn"))

    def test_items_inventory_empty_returns_none(self):
        caller = self._caller()
        caller.contents = []
        target, _ = resolve_target(caller, "sword", "items_inventory")
        self.assertIsNone(target)

    def test_items_inventory_no_match_returns_none(self):
        sword = _make_item("sword")
        caller = self._caller()
        caller.contents = [sword]
        caller.search = MagicMock(return_value=None)
        target, _ = resolve_target(caller, "hammer", "items_inventory")
        self.assertIsNone(target)

    def test_items_inventory_passes_stacked(self):
        coin = _make_item("coin")
        caller = self._caller()
        caller.contents = [coin]
        caller.search = MagicMock(return_value=[coin])
        resolve_target(caller, "coin", "items_inventory", stacked=3)
        _, kwargs = caller.search.call_args
        self.assertEqual(kwargs.get("stacked"), 3)

    # ── items_equipped ───────────────────────────────────────────

    def test_items_equipped_finds_worn_item(self):
        helm = _make_item("helm")
        caller = self._caller()
        caller.contents = [helm]
        caller.search = MagicMock(return_value=helm)
        target, _ = resolve_target(caller, "helm", "items_equipped")
        self.assertIs(target, helm)

    def test_items_equipped_passes_only_worn(self):
        helm = _make_item("helm")
        caller = self._caller()
        caller.contents = [helm]
        caller.search = MagicMock(return_value=helm)
        resolve_target(caller, "helm", "items_equipped")
        _, kwargs = caller.search.call_args
        self.assertTrue(kwargs.get("only_worn"))

    def test_items_equipped_empty_returns_none(self):
        caller = self._caller()
        caller.contents = []
        target, _ = resolve_target(caller, "helm", "items_equipped")
        self.assertIsNone(target)


class TestResolveTargetRoomItems(EvenniaTest):
    """Tests for resolve_target room item target types."""

    def create_script(self):
        pass

    def _caller(self):
        caller = MagicMock()
        caller.msg = MagicMock()
        caller.contents = []
        return caller

    # ── items_room_all ───────────────────────────────────────────

    def test_items_room_all_finds_item(self):
        sword = _make_item("sword")
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[sword])
        caller.search = MagicMock(return_value=sword)
        target, _ = resolve_target(caller, "sword", "items_room_all")
        self.assertIs(target, sword)

    def test_items_room_all_includes_exits(self):
        exit_obj = _make_exit()
        exit_obj.key = "gate"
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[exit_obj])
        caller.search = MagicMock(return_value=exit_obj)
        target, _ = resolve_target(caller, "gate", "items_room_all")
        self.assertIs(target, exit_obj)

    def test_items_room_all_excludes_actors(self):
        actor = _make_character()
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[actor])
        caller.search = MagicMock(return_value=None)
        target, _ = resolve_target(caller, "bob", "items_room_all")
        self.assertIsNone(target)

    def test_items_room_all_no_location(self):
        caller = self._caller()
        caller.location = None
        target, _ = resolve_target(caller, "sword", "items_room_all")
        self.assertIsNone(target)

    # ── items_room_exits ─────────────────────────────────────────

    def test_items_room_exits_finds_exit(self):
        exit_obj = _make_exit()
        exit_obj.key = "gate"
        caller = self._caller()
        caller.location = MagicMock()
        caller.location.exits = [exit_obj]
        caller.search = MagicMock(return_value=exit_obj)
        target, _ = resolve_target(caller, "gate", "items_room_exits")
        self.assertIs(target, exit_obj)

    def test_items_room_exits_no_location(self):
        caller = self._caller()
        caller.location = None
        target, _ = resolve_target(caller, "gate", "items_room_exits")
        self.assertIsNone(target)

    def test_items_room_exits_empty(self):
        caller = self._caller()
        caller.location = MagicMock()
        caller.location.exits = []
        target, _ = resolve_target(caller, "gate", "items_room_exits")
        self.assertIsNone(target)

    # ── items_room_nonexit ───────────────────────────────────────

    def test_items_room_nonexit_finds_item(self):
        sword = _make_item("sword")
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[sword])
        caller.search = MagicMock(return_value=sword)
        target, _ = resolve_target(caller, "sword", "items_room_nonexit")
        self.assertIs(target, sword)

    def test_items_room_nonexit_excludes_exits(self):
        exit_obj = _make_exit()
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[exit_obj])
        caller.search = MagicMock(return_value=None)
        target, _ = resolve_target(caller, "gate", "items_room_nonexit")
        self.assertIsNone(target)

    def test_items_room_nonexit_excludes_actors(self):
        actor = _make_character()
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[actor])
        caller.search = MagicMock(return_value=None)
        target, _ = resolve_target(caller, "bob", "items_room_nonexit")
        self.assertIsNone(target)

    # ── items_room_gettable ──────────────────────────────────────

    def test_items_room_gettable_finds_gettable(self):
        sword = _make_gettable_item("sword")
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[sword])
        caller.search = MagicMock(return_value=sword)
        target, _ = resolve_target(caller, "sword", "items_room_gettable")
        self.assertIs(target, sword)

    def test_items_room_gettable_excludes_fixed(self):
        chest = _make_fixed_item("chest")
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[chest])
        caller.search = MagicMock(return_value=None)
        target, _ = resolve_target(caller, "chest", "items_room_gettable")
        self.assertIsNone(target)

    # ── items_room_fixed ─────────────────────────────────────────

    def test_items_room_fixed_finds_fixed(self):
        chest = _make_fixed_item("chest")
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[chest])
        caller.search = MagicMock(return_value=chest)
        target, _ = resolve_target(caller, "chest", "items_room_fixed")
        self.assertIs(target, chest)

    def test_items_room_fixed_excludes_gettable(self):
        sword = _make_gettable_item("sword")
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[sword])
        caller.search = MagicMock(return_value=None)
        target, _ = resolve_target(caller, "sword", "items_room_fixed")
        self.assertIsNone(target)

    def test_items_room_fixed_includes_exits(self):
        """Exits are fixed (get:false by default) — included in items_room_fixed."""
        exit_obj = _make_exit()
        exit_obj.key = "gate"
        # Exits don't have .access — they'll fail p_passes_lock("get")
        # which means NOT gettable = fixed. But _make_exit is a MagicMock
        # so .access returns a truthy MagicMock. Need explicit override.
        exit_obj.access = lambda c, access_type, **kw: access_type != "get"
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[exit_obj])
        caller.search = MagicMock(return_value=exit_obj)
        target, _ = resolve_target(caller, "gate", "items_room_fixed")
        self.assertIs(target, exit_obj)

    # ── items_room_fixed_nonexit ─────────────────────────────────

    def test_items_room_fixed_nonexit_finds_fixed(self):
        chest = _make_fixed_item("chest")
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[chest])
        caller.search = MagicMock(return_value=chest)
        target, _ = resolve_target(caller, "chest", "items_room_fixed_nonexit")
        self.assertIs(target, chest)

    def test_items_room_fixed_nonexit_excludes_exits(self):
        exit_obj = _make_exit()
        exit_obj.access = lambda c, access_type, **kw: access_type != "get"
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[exit_obj])
        caller.search = MagicMock(return_value=None)
        target, _ = resolve_target(caller, "gate", "items_room_fixed_nonexit")
        self.assertIsNone(target)

    def test_items_room_fixed_nonexit_excludes_gettable(self):
        sword = _make_gettable_item("sword")
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[sword])
        caller.search = MagicMock(return_value=None)
        target, _ = resolve_target(caller, "sword", "items_room_fixed_nonexit")
        self.assertIsNone(target)


class TestResolveTargetCompositeItems(EvenniaTest):
    """Tests for composite item target types (fallback chains)."""

    def create_script(self):
        pass

    def _caller(self):
        caller = MagicMock()
        caller.msg = MagicMock()
        return caller

    # ── items_room_all_then_inventory ────────────────────────────

    def test_room_all_then_inv_finds_in_room(self):
        sword = _make_item("sword")
        caller = self._caller()
        caller.contents = []
        caller.location = SimpleNamespace(contents=[sword])
        caller.search = MagicMock(return_value=sword)
        target, _ = resolve_target(caller, "sword", "items_room_all_then_inventory")
        self.assertIs(target, sword)

    def test_room_all_then_inv_falls_back_to_inventory(self):
        sword = _make_item("sword")
        caller = self._caller()
        caller.contents = [sword]
        caller.location = SimpleNamespace(contents=[])
        caller.search = MagicMock(return_value=sword)
        target, _ = resolve_target(caller, "sword", "items_room_all_then_inventory")
        self.assertIs(target, sword)

    def test_room_all_then_inv_room_wins_over_inventory(self):
        room_sword = _make_item("sword")
        inv_sword = _make_item("sword")
        caller = self._caller()
        caller.contents = [inv_sword]
        caller.location = SimpleNamespace(contents=[room_sword])
        caller.search = MagicMock(return_value=room_sword)
        target, _ = resolve_target(caller, "sword", "items_room_all_then_inventory")
        self.assertIs(target, room_sword)

    def test_room_all_then_inv_neither_returns_none(self):
        caller = self._caller()
        caller.contents = []
        caller.location = SimpleNamespace(contents=[])
        target, _ = resolve_target(caller, "sword", "items_room_all_then_inventory")
        self.assertIsNone(target)

    # ── items_inventory_then_room_all ────────────────────────────

    def test_inv_then_room_all_finds_in_inventory(self):
        sword = _make_item("sword")
        caller = self._caller()
        caller.contents = [sword]
        caller.location = SimpleNamespace(contents=[])
        caller.search = MagicMock(return_value=sword)
        target, _ = resolve_target(caller, "sword", "items_inventory_then_room_all")
        self.assertIs(target, sword)

    def test_inv_then_room_all_falls_back_to_room(self):
        sword = _make_item("sword")
        caller = self._caller()
        caller.contents = []
        caller.location = SimpleNamespace(contents=[sword])
        caller.search = MagicMock(return_value=sword)
        target, _ = resolve_target(caller, "sword", "items_inventory_then_room_all")
        self.assertIs(target, sword)

    def test_inv_then_room_all_inventory_wins(self):
        inv_sword = _make_item("sword")
        room_sword = _make_item("sword")
        caller = self._caller()
        caller.contents = [inv_sword]
        caller.location = SimpleNamespace(contents=[room_sword])
        caller.search = MagicMock(return_value=inv_sword)
        target, _ = resolve_target(caller, "sword", "items_inventory_then_room_all")
        self.assertIs(target, inv_sword)

    def test_inv_then_room_all_neither_returns_none(self):
        caller = self._caller()
        caller.contents = []
        caller.location = SimpleNamespace(contents=[])
        target, _ = resolve_target(caller, "sword", "items_inventory_then_room_all")
        self.assertIsNone(target)

    # ── items_inventory_then_room_nonexit ────────────────────────

    def test_inv_then_room_nonexit_finds_in_inventory(self):
        sword = _make_item("sword")
        caller = self._caller()
        caller.contents = [sword]
        caller.location = SimpleNamespace(contents=[])
        caller.search = MagicMock(return_value=sword)
        target, _ = resolve_target(caller, "sword", "items_inventory_then_room_nonexit")
        self.assertIs(target, sword)

    def test_inv_then_room_nonexit_falls_back_to_room(self):
        sword = _make_item("sword")
        caller = self._caller()
        caller.contents = []
        caller.location = SimpleNamespace(contents=[sword])
        caller.search = MagicMock(return_value=sword)
        target, _ = resolve_target(caller, "sword", "items_inventory_then_room_nonexit")
        self.assertIs(target, sword)

    def test_inv_then_room_nonexit_excludes_exits_from_room(self):
        exit_obj = _make_exit()
        caller = self._caller()
        caller.contents = []
        caller.location = SimpleNamespace(contents=[exit_obj])
        caller.search = MagicMock(return_value=None)
        target, _ = resolve_target(caller, "gate", "items_inventory_then_room_nonexit")
        self.assertIsNone(target)

    def test_inv_then_room_nonexit_neither_returns_none(self):
        caller = self._caller()
        caller.contents = []
        caller.location = SimpleNamespace(contents=[])
        target, _ = resolve_target(caller, "sword", "items_inventory_then_room_nonexit")
        self.assertIsNone(target)


class TestAoESecondaries(EvenniaTest):
    """Tests for AoE secondary target resolution via resolve_target aoe param.

    Tests _resolve_aoe_secondaries indirectly through the public API.
    All actors are at height 0 unless specified.
    """

    def create_script(self):
        pass

    def _make_aoe_actor(self, key="mob", hp=10, combat_side=None,
                        height=0, leader=None):
        actor = _make_actor(key=key, hp=hp, combat_side=combat_side,
                            leader=leader)
        actor.room_vertical_position = height
        return actor

    def _caller(self, combat_side=None, leader=None):
        caller = self._make_aoe_actor(
            key="caster", combat_side=combat_side, leader=leader,
        )
        caller.search = MagicMock(side_effect=_search_returns_first)
        caller.msg = MagicMock()
        return caller

    # ── unsafe: everyone at target's height, caster included ────

    def test_unsafe_includes_caster(self):
        caller = self._caller()
        target = self._make_aoe_actor(key="goblin")
        bystander = self._make_aoe_actor(key="rat")
        caller.location = SimpleNamespace(
            contents=[caller, target, bystander]
        )
        _, secondaries = resolve_target(
            caller, "goblin", "actor_hostile", aoe="unsafe",
        )
        self.assertIn(caller, secondaries)
        self.assertIn(bystander, secondaries)
        self.assertNotIn(target, secondaries)  # primary excluded

    def test_unsafe_excludes_different_height(self):
        caller = self._caller()
        target = self._make_aoe_actor(key="goblin", height=0)
        flying = self._make_aoe_actor(key="bird", height=1)
        caller.location = SimpleNamespace(
            contents=[caller, target, flying]
        )
        _, secondaries = resolve_target(
            caller, "goblin", "actor_hostile", aoe="unsafe",
        )
        self.assertNotIn(flying, secondaries)

    # ── unsafe_all_heights: everyone regardless of height ────────

    def test_unsafe_all_heights_includes_all(self):
        caller = self._caller()
        target = self._make_aoe_actor(key="goblin", height=0)
        flying = self._make_aoe_actor(key="bird", height=1)
        ground = self._make_aoe_actor(key="rat", height=0)
        caller.location = SimpleNamespace(
            contents=[caller, target, flying, ground]
        )
        _, secondaries = resolve_target(
            caller, "goblin", "actor_hostile", aoe="unsafe_all_heights",
        )
        self.assertIn(caller, secondaries)
        self.assertIn(flying, secondaries)
        self.assertIn(ground, secondaries)
        self.assertNotIn(target, secondaries)

    # ── unsafe_self: everyone at height except caster ────────────

    def test_unsafe_self_excludes_caster(self):
        caller = self._caller()
        target = self._make_aoe_actor(key="goblin")
        bystander = self._make_aoe_actor(key="rat")
        caller.location = SimpleNamespace(
            contents=[caller, target, bystander]
        )
        _, secondaries = resolve_target(
            caller, "goblin", "actor_hostile", aoe="unsafe_self",
        )
        self.assertNotIn(caller, secondaries)
        self.assertIn(bystander, secondaries)
        self.assertNotIn(target, secondaries)

    # ── safe: enemies only at target's height ────────────────────

    def test_safe_in_combat_only_enemies(self):
        caller = self._caller(combat_side=1)
        target = self._make_aoe_actor(key="goblin", combat_side=2)
        ally = self._make_aoe_actor(key="bob", combat_side=1)
        enemy2 = self._make_aoe_actor(key="orc", combat_side=2)
        caller.location = SimpleNamespace(
            contents=[caller, target, ally, enemy2]
        )
        _, secondaries = resolve_target(
            caller, "goblin", "actor_hostile", aoe="safe",
        )
        self.assertIn(enemy2, secondaries)
        self.assertNotIn(ally, secondaries)
        self.assertNotIn(caller, secondaries)
        self.assertNotIn(target, secondaries)

    def test_safe_out_of_combat_non_group_are_enemies(self):
        leader = object()
        caller = self._caller(leader=leader)
        target = self._make_aoe_actor(key="goblin")
        groupmate = self._make_aoe_actor(key="bob", leader=leader)
        stranger = self._make_aoe_actor(key="orc")
        caller.location = SimpleNamespace(
            contents=[caller, target, groupmate, stranger]
        )
        _, secondaries = resolve_target(
            caller, "goblin", "actor_hostile", aoe="safe",
        )
        self.assertIn(stranger, secondaries)
        self.assertNotIn(groupmate, secondaries)
        self.assertNotIn(caller, secondaries)

    # ── allies: allies at target's height, caster included ───────

    def test_allies_in_combat_only_allies(self):
        caller = self._caller(combat_side=1)
        target = self._make_aoe_actor(key="bob", combat_side=1)
        ally2 = self._make_aoe_actor(key="sue", combat_side=1)
        enemy = self._make_aoe_actor(key="goblin", combat_side=2)
        caller.location = SimpleNamespace(
            contents=[caller, target, ally2, enemy]
        )
        _, secondaries = resolve_target(
            caller, "bob", "actor_friendly", aoe="allies",
        )
        self.assertIn(caller, secondaries)
        self.assertIn(ally2, secondaries)
        self.assertNotIn(enemy, secondaries)
        self.assertNotIn(target, secondaries)

    # ── no AoE: secondaries always empty ─────────────────────────

    def test_no_aoe_returns_empty_secondaries(self):
        caller = self._caller()
        target = self._make_aoe_actor(key="goblin")
        bystander = self._make_aoe_actor(key="rat")
        caller.location = SimpleNamespace(
            contents=[caller, target, bystander]
        )
        _, secondaries = resolve_target(
            caller, "goblin", "actor_hostile",
        )
        self.assertEqual(secondaries, [])

    # ── no primary target: secondaries empty ─────────────────────

    def test_aoe_with_no_match_returns_empty(self):
        caller = self._caller()
        caller.location = SimpleNamespace(contents=[caller])
        target, secondaries = resolve_target(
            caller, "goblin", "actor_hostile", aoe="unsafe",
        )
        self.assertIsNone(target)
        self.assertEqual(secondaries, [])
