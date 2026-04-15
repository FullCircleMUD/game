# FullCircleMUD/tests/utils_tests/test_targeting_predicates.py

# TO RUN THIS TEST:
# IN FullCircleMUD/src/game:
#   evennia test --settings settings.py tests.utils_tests.test_targeting_predicates

from types import SimpleNamespace
from unittest.mock import MagicMock

from evennia.objects.objects import DefaultCharacter, DefaultExit
from evennia.utils.test_resources import EvenniaTest

from utils.targeting.predicates import (
    p_not_caller,
    p_not_character,
    p_not_exit,
    p_passes_lock,
    p_visible_to,
)


class TestPredicates(EvenniaTest):
    """Unit tests for utils.targeting.predicates."""

    def create_script(self):
        # Skip EvenniaTest's default script creation — FCM has no
        # typeclasses.scripts.Script at that path and these tests
        # don't need any script fixture.
        pass

    # ── p_not_caller ──────────────────────────────────────────────

    def test_p_not_caller_true_when_different_obj(self):
        caller = SimpleNamespace()
        other = SimpleNamespace()
        self.assertTrue(p_not_caller(other, caller))

    def test_p_not_caller_false_when_same_obj(self):
        caller = SimpleNamespace()
        self.assertFalse(p_not_caller(caller, caller))

    # ── p_not_character ───────────────────────────────────────────

    def test_p_not_character_true_for_plain_object(self):
        obj = SimpleNamespace()
        self.assertTrue(p_not_character(obj, caller=None))

    def test_p_not_character_false_for_character(self):
        char = MagicMock(spec=DefaultCharacter)
        self.assertFalse(p_not_character(char, caller=None))

    # ── p_not_exit ────────────────────────────────────────────────

    def test_p_not_exit_true_for_plain_object(self):
        obj = SimpleNamespace()
        self.assertTrue(p_not_exit(obj, caller=None))

    def test_p_not_exit_false_for_exit(self):
        exit_obj = MagicMock(spec=DefaultExit)
        self.assertFalse(p_not_exit(exit_obj, caller=None))

    # ── p_visible_to ──────────────────────────────────────────────

    def test_p_visible_to_true_when_no_mixin(self):
        obj = SimpleNamespace()
        self.assertTrue(p_visible_to(obj, caller=None))

    def test_p_visible_to_true_when_mixin_returns_true(self):
        obj = SimpleNamespace(is_hidden_visible_to=lambda caller: True)
        self.assertTrue(p_visible_to(obj, caller=None))

    def test_p_visible_to_false_when_mixin_returns_false(self):
        obj = SimpleNamespace(is_hidden_visible_to=lambda caller: False)
        self.assertFalse(p_visible_to(obj, caller=None))

    # ── p_passes_lock ─────────────────────────────────────────────

    def test_p_passes_lock_true_when_access_returns_true(self):
        obj = SimpleNamespace(access=lambda caller, lock_type: True)
        pred = p_passes_lock("get")
        self.assertTrue(pred(obj, caller=None))

    def test_p_passes_lock_false_when_access_returns_false(self):
        obj = SimpleNamespace(access=lambda caller, lock_type: False)
        pred = p_passes_lock("get")
        self.assertFalse(pred(obj, caller=None))
