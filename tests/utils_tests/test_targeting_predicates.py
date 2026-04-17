# FullCircleMUD/tests/utils_tests/test_targeting_predicates.py

# TO RUN THIS TEST:
# IN FullCircleMUD/src/game:
#   evennia test --settings settings.py tests.utils_tests.test_targeting_predicates

from types import SimpleNamespace
from unittest.mock import MagicMock

from evennia.objects.objects import DefaultCharacter, DefaultExit
from evennia.utils.test_resources import EvenniaTest

from utils.targeting.predicates import (
    p_can_see,
    p_different_height,
    p_height_visible_to,
    p_in_combat,
    p_is_character,
    p_living,
    p_not_actor,
    p_not_exit,
    p_passes_lock,
    p_same_height,
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

    def test_p_not_actor_false_for_fcmcharacter(self):
        # FCMCharacter inherits DefaultCharacter, so a PC is also an
        # actor. Locks in the inheritance relationship: p_not_actor
        # and p_is_character are NOT opposites — FCMCharacter passes
        # the positive character filter AND fails the negative actor
        # filter.
        from typeclasses.actors.character import FCMCharacter
        pc = MagicMock(spec=FCMCharacter)
        self.assertFalse(p_not_actor(pc, caller=None))

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

    def test_p_is_character_false_for_default_character(self):
        # Critical boundary test: an NPC or mob is a DefaultCharacter
        # but NOT an FCMCharacter. p_is_character must return False
        # for these or the give/whisper/trade commands would allow
        # targeting NPCs when they shouldn't. Locks the character /
        # actor vocabulary distinction in place.
        npc = MagicMock(spec=DefaultCharacter)
        self.assertFalse(p_is_character(npc, caller=None))

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

    # ── p_living ──────────────────────────────────────────────────

    def test_p_living_true_when_hp_positive(self):
        obj = SimpleNamespace(hp=10)
        self.assertTrue(p_living(obj, caller=None))

    def test_p_living_false_when_hp_zero(self):
        obj = SimpleNamespace(hp=0)
        self.assertFalse(p_living(obj, caller=None))

    def test_p_living_false_when_hp_none(self):
        # Items, exits, and anything without an hp attribute fail.
        obj = SimpleNamespace()
        self.assertFalse(p_living(obj, caller=None))

    def test_p_living_false_when_hp_negative(self):
        # Paranoid edge case — a combatant at negative hp from
        # overkill damage should still be excluded.
        obj = SimpleNamespace(hp=-5)
        self.assertFalse(p_living(obj, caller=None))

    # ── p_in_combat ───────────────────────────────────────────────

    def test_p_in_combat_true_when_handler_attached(self):
        # scripts.get returns a non-empty list when a combat_handler
        # is attached to the object.
        obj = SimpleNamespace(
            scripts=SimpleNamespace(get=lambda key: ["mock_handler"]),
        )
        self.assertTrue(p_in_combat(obj, caller=None))

    def test_p_in_combat_false_when_no_handler(self):
        # scripts.get returns an empty list when nothing is attached.
        obj = SimpleNamespace(
            scripts=SimpleNamespace(get=lambda key: []),
        )
        self.assertFalse(p_in_combat(obj, caller=None))

    def test_p_in_combat_false_when_no_scripts_attr(self):
        # Items, rooms, exits don't even have a scripts attribute.
        obj = SimpleNamespace()
        self.assertFalse(p_in_combat(obj, caller=None))

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

    # ── p_same_height ────────────────────────────────────────────

    def test_p_same_height_matches_same_position(self):
        caller = SimpleNamespace(room_vertical_position=2)
        obj = SimpleNamespace(room_vertical_position=2)
        pred = p_same_height(caller)
        self.assertTrue(pred(obj, caller))

    def test_p_same_height_rejects_different_position(self):
        caller = SimpleNamespace(room_vertical_position=0)
        obj = SimpleNamespace(room_vertical_position=2)
        pred = p_same_height(caller)
        self.assertFalse(pred(obj, caller))

    def test_p_same_height_defaults_to_zero(self):
        caller = SimpleNamespace()  # no room_vertical_position
        obj = SimpleNamespace()     # no room_vertical_position
        pred = p_same_height(caller)
        self.assertTrue(pred(obj, caller))  # both default to 0

    def test_p_same_height_default_vs_explicit_zero(self):
        caller = SimpleNamespace(room_vertical_position=0)
        obj = SimpleNamespace()  # defaults to 0
        pred = p_same_height(caller)
        self.assertTrue(pred(obj, caller))

    # ── p_different_height ───────────────────────────────────────

    def test_p_different_height_matches_different_position(self):
        caller = SimpleNamespace(room_vertical_position=0)
        obj = SimpleNamespace(room_vertical_position=2)
        pred = p_different_height(caller)
        self.assertTrue(pred(obj, caller))

    def test_p_different_height_rejects_same_position(self):
        caller = SimpleNamespace(room_vertical_position=2)
        obj = SimpleNamespace(room_vertical_position=2)
        pred = p_different_height(caller)
        self.assertFalse(pred(obj, caller))

    def test_p_different_height_defaults_to_zero(self):
        caller = SimpleNamespace()
        obj = SimpleNamespace()
        pred = p_different_height(caller)
        self.assertFalse(pred(obj, caller))  # both default to 0 = same

    # ── p_height_visible_to (barrier system) ─────────────────────

    def test_p_height_visible_to_true_when_no_mixin(self):
        obj = SimpleNamespace()
        self.assertTrue(p_height_visible_to(obj, caller=None))

    def test_p_height_visible_to_same_height_always_visible(self):
        room = SimpleNamespace(visibility_up_barrier=(1, "small"))
        obj = SimpleNamespace(
            room_vertical_position=1, size="tiny", location=room,
        )
        # is_height_visible_to is on HeightAwareMixin — test via predicate
        # which wraps it. For SimpleNamespace we need to attach the method.
        from typeclasses.mixins.height_aware_mixin import HeightAwareMixin
        obj.is_height_visible_to = HeightAwareMixin.is_height_visible_to.__get__(obj)
        looker = SimpleNamespace(room_vertical_position=1)
        self.assertTrue(p_height_visible_to(obj, looker))

    def test_p_height_visible_to_up_barrier_hides_small_obj(self):
        room = SimpleNamespace(visibility_up_barrier=(1, "small"))
        obj = SimpleNamespace(
            room_vertical_position=1, size="tiny", location=room,
        )
        from typeclasses.mixins.height_aware_mixin import HeightAwareMixin
        obj.is_height_visible_to = HeightAwareMixin.is_height_visible_to.__get__(obj)
        looker = SimpleNamespace(room_vertical_position=0)
        self.assertFalse(p_height_visible_to(obj, looker))

    def test_p_height_visible_to_up_barrier_large_obj_visible(self):
        room = SimpleNamespace(visibility_up_barrier=(1, "small"))
        obj = SimpleNamespace(
            room_vertical_position=1, size="large", location=room,
        )
        from typeclasses.mixins.height_aware_mixin import HeightAwareMixin
        obj.is_height_visible_to = HeightAwareMixin.is_height_visible_to.__get__(obj)
        looker = SimpleNamespace(room_vertical_position=0)
        self.assertTrue(p_height_visible_to(obj, looker))

    def test_p_height_visible_to_down_barrier_hides_small_obj(self):
        room = SimpleNamespace(
            visibility_up_barrier=None,
            visibility_down_barrier=(-1, "small"),
        )
        obj = SimpleNamespace(
            room_vertical_position=-2, size="small", location=room,
        )
        from typeclasses.mixins.height_aware_mixin import HeightAwareMixin
        obj.is_height_visible_to = HeightAwareMixin.is_height_visible_to.__get__(obj)
        looker = SimpleNamespace(room_vertical_position=0)
        self.assertFalse(p_height_visible_to(obj, looker))

    def test_p_height_visible_to_no_barrier_always_visible(self):
        room = SimpleNamespace()  # no barriers
        obj = SimpleNamespace(
            room_vertical_position=1, size="tiny", location=room,
        )
        from typeclasses.mixins.height_aware_mixin import HeightAwareMixin
        obj.is_height_visible_to = HeightAwareMixin.is_height_visible_to.__get__(obj)
        looker = SimpleNamespace(room_vertical_position=0)
        self.assertTrue(p_height_visible_to(obj, looker))

    def test_p_height_visible_to_no_location_always_visible(self):
        """Object not in a room (e.g. in inventory) — always visible."""
        obj = SimpleNamespace(
            room_vertical_position=1, size="tiny", location=None,
        )
        from typeclasses.mixins.height_aware_mixin import HeightAwareMixin
        obj.is_height_visible_to = HeightAwareMixin.is_height_visible_to.__get__(obj)
        looker = SimpleNamespace(room_vertical_position=0)
        self.assertTrue(p_height_visible_to(obj, looker))

    # ── p_can_see (composite) ────────────────────────────────────

    def test_p_can_see_true_when_both_pass(self):
        obj = SimpleNamespace()  # no hidden mixin, no height mixin
        self.assertTrue(p_can_see(obj, caller=None))

    def test_p_can_see_false_when_hidden(self):
        obj = SimpleNamespace(is_hidden_visible_to=lambda caller: False)
        self.assertFalse(p_can_see(obj, caller=None))

    def test_p_can_see_false_when_height_gated(self):
        room = SimpleNamespace(visibility_up_barrier=(1, "small"))
        obj = SimpleNamespace(
            room_vertical_position=1, size="tiny", location=room,
        )
        from typeclasses.mixins.height_aware_mixin import HeightAwareMixin
        obj.is_height_visible_to = HeightAwareMixin.is_height_visible_to.__get__(obj)
        looker = SimpleNamespace(room_vertical_position=0)
        self.assertFalse(p_can_see(obj, looker))
