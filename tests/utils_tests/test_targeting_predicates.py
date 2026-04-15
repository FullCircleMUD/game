# FullCircleMUD/tests/utils_tests/test_targeting_predicates.py

# TO RUN THIS TEST:
# IN FullCircleMUD/src/game:
#   evennia test --settings settings.py tests.utils_tests.test_targeting_predicates

from types import SimpleNamespace
from unittest.mock import MagicMock

from evennia.objects.objects import DefaultCharacter, DefaultExit
from evennia.utils.test_resources import EvenniaTest

from utils.targeting.predicates import (
    p_is_character,
    p_not_actor,
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

    # ── p_not_actor ───────────────────────────────────────────────

    def test_p_not_actor_true_for_plain_object(self):
        obj = SimpleNamespace()
        self.assertTrue(p_not_actor(obj, caller=None))

    def test_p_not_actor_false_for_default_character(self):
        # Any DefaultCharacter subclass is an actor — PCs, NPCs, mobs,
        # pets, mounts all inherit from DefaultCharacter.
        char = MagicMock(spec=DefaultCharacter)
        self.assertFalse(p_not_actor(char, caller=None))

    # ── p_is_character ────────────────────────────────────────────

    def test_p_is_character_false_for_plain_object(self):
        obj = SimpleNamespace()
        self.assertFalse(p_is_character(obj, caller=None))

    def test_p_is_character_true_for_fcmcharacter(self):
        # p_is_character matches FCMCharacter specifically — the
        # player-character class, not the generic DefaultCharacter.
        from typeclasses.actors.character import FCMCharacter
        pc = MagicMock(spec=FCMCharacter)
        self.assertTrue(p_is_character(pc, caller=None))

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

    # ── p_is_container ────────────────────────────────────────────

    def test_p_is_container_true_when_is_container_true(self):
        obj = SimpleNamespace(is_container=True)
        from utils.targeting.predicates import p_is_container
        self.assertTrue(p_is_container(obj, caller=None))

    def test_p_is_container_false_when_attr_missing(self):
        obj = SimpleNamespace()
        from utils.targeting.predicates import p_is_container
        self.assertFalse(p_is_container(obj, caller=None))

    # ── p_passes_lock ─────────────────────────────────────────────

    def test_p_passes_lock_true_when_access_returns_true(self):
        obj = SimpleNamespace(access=lambda caller, lock_type: True)
        pred = p_passes_lock("get")
        self.assertTrue(pred(obj, caller=None))

    def test_p_passes_lock_false_when_access_returns_false(self):
        obj = SimpleNamespace(access=lambda caller, lock_type: False)
        pred = p_passes_lock("get")
        self.assertFalse(pred(obj, caller=None))
