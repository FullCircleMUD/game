# FullCircleMUD/tests/utils_tests/test_targeting_helpers.py

# TO RUN THIS TEST:
# IN FullCircleMUD/src/game:
#   evennia test --settings settings.py tests.utils_tests.test_targeting_helpers

from types import SimpleNamespace
from unittest.mock import MagicMock

from evennia.objects.objects import DefaultCharacter, DefaultExit
from evennia.utils.test_resources import EvenniaTest

from utils.targeting.helpers import resolve_item_in_source


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


class TestResolveItemInSource(EvenniaTest):
    """Unit tests for utils.targeting.helpers.resolve_item_in_source."""

    def create_script(self):
        # Skip EvenniaTest's default script creation — FCM has no
        # typeclasses.scripts.Script at that path and these tests
        # don't need any script fixture.
        pass

    # ── Source edge cases ─────────────────────────────────────────

    def test_source_is_none_returns_none(self):
        caller = _make_caller()
        result = resolve_item_in_source(caller, None, "sword")
        self.assertIsNone(result)
        caller.search.assert_not_called()

    def test_source_without_contents_returns_none(self):
        caller = _make_caller()
        source = SimpleNamespace()  # no .contents attribute
        result = resolve_item_in_source(caller, source, "sword")
        self.assertIsNone(result)
        caller.search.assert_not_called()

    def test_source_with_empty_contents_returns_none(self):
        caller = _make_caller()
        source = SimpleNamespace(contents=[])
        result = resolve_item_in_source(caller, source, "sword")
        self.assertIsNone(result)
        caller.search.assert_not_called()

    # ── Happy path ────────────────────────────────────────────────

    def test_matching_item_returned(self):
        sword = _make_item("sword")
        caller = _make_caller(search_return=sword)
        source = SimpleNamespace(contents=[sword])
        result = resolve_item_in_source(caller, source, "sword")
        self.assertIs(result, sword)

    # ── Filter exclusions ─────────────────────────────────────────

    def test_character_excluded_from_candidates(self):
        character = _make_character()
        caller = _make_caller()
        source = SimpleNamespace(contents=[character])
        result = resolve_item_in_source(caller, source, "anything")
        self.assertIsNone(result)
        caller.search.assert_not_called()

    def test_exit_excluded_from_candidates(self):
        exit_obj = _make_exit()
        caller = _make_caller()
        source = SimpleNamespace(contents=[exit_obj])
        result = resolve_item_in_source(caller, source, "anything")
        self.assertIsNone(result)
        caller.search.assert_not_called()

    def test_hidden_item_excluded_when_mixin_returns_false(self):
        hidden = _make_hidden_item(visible=False)
        caller = _make_caller()
        source = SimpleNamespace(contents=[hidden])
        result = resolve_item_in_source(caller, source, "anything")
        self.assertIsNone(result)
        caller.search.assert_not_called()

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
