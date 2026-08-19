"""
Tests for StateMachineAIMixin and AIHandler — the state machine itself,
as distinct from the perception helpers covered in test_ai_perception.

Two things here are the fix for a real defect. A spawn rule's
`attrs: {ai_state: idle}` silently did nothing: the value was not backed
by an `AttributeProperty` so it never persisted, and nothing called
`start_ai()` on a spawner-created mob so the state was never read anyway.
Mobs spawned mid-session had no AI at all until the next restart adopted
them, which is why the symptom looked intermittent.

evennia test --settings settings tests.typeclass_tests.test_ai_state_machine
"""

from unittest.mock import patch

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from typeclasses.actors.ai_handler import AIHandler, StateMachineAIMixin

MOB = "typeclasses.actors.mob.CombatMob"


class AIStateMachineTest(EvenniaTest):
    """Shared fixture: one CombatMob in room1."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.mob = create.create_object(MOB, key="a test mob", location=self.room1)


class TestStatePersistence(AIStateMachineTest):
    """set_state / get_state round-trip through a categorised Attribute."""

    def test_default_state_is_idle(self):
        self.assertEqual(self.mob.ai.get_state(), "idle")

    def test_set_state_is_readable_back(self):
        self.mob.ai.set_state("wander")
        self.assertEqual(self.mob.ai.get_state(), "wander")

    def test_set_state_writes_the_categorised_attribute(self):
        # The category is load-bearing: AIHandler reads and writes
        # category="ai_state", so a value stored uncategorised would be a
        # different row that the handler never sees.
        self.mob.ai.set_state("retreating")
        self.assertEqual(
            self.mob.attributes.get("ai_state", category="ai_state"),
            "retreating",
        )

    def test_state_survives_a_fresh_handler(self):
        # AIHandler caches into _state at construction, so this is what
        # proves the value is really in the database and not just held on
        # the instance.
        self.mob.ai.set_state("wander")
        self.assertEqual(AIHandler(self.mob).get_state(), "wander")


class TestRunDispatch(AIStateMachineTest):
    """run() dispatches to ai_<state>() on the owning object."""

    def test_run_calls_the_matching_state_method(self):
        self.mob.ai.set_state("idle")
        with patch.object(type(self.mob), "ai_idle") as mocked:
            self.mob.ai.run()
        mocked.assert_called_once()

    def test_run_is_a_no_op_when_the_state_has_no_method(self):
        # getattr(..., None) means an unknown state is silently inert
        # rather than an error. Worth pinning: it is why a typo in a
        # spawn rule produces a mob that ticks forever doing nothing.
        self.mob.ai.set_state("no_such_state")
        self.mob.ai.run()  # must not raise

    def test_run_swallows_an_exception_from_the_state_method(self):
        # One broken mob must not take down the ticker for every other
        # mob sharing that interval.
        self.mob.ai.set_state("idle")
        with patch.object(type(self.mob), "ai_idle", side_effect=RuntimeError("boom")):
            self.mob.ai.run()  # must not raise


class TestAiStateDeclaration(AIStateMachineTest):
    """The AttributeProperty that makes a spawn rule's ai_state persist."""

    def test_ai_state_is_declared_as_an_attributeproperty(self):
        # evennia-mob-spawner applies rule attrs with setattr and checks
        # the MRO for an AttributeProperty via inspect.getattr_static.
        # Without this declaration the value silently fails to persist
        # and the library logs a WARN.
        import inspect

        descriptor = inspect.getattr_static(self.mob, "ai_state", None)
        self.assertIsInstance(descriptor, AttributeProperty)

    def test_declaration_category_matches_the_handler(self):
        # If these diverge, the rule writes one row and the handler reads
        # another, and the two never meet.
        import inspect

        descriptor = inspect.getattr_static(self.mob, "ai_state", None)
        self.assertEqual(descriptor._category, AIHandler.attribute_category)

    def test_setattr_persists_and_the_handler_sees_it(self):
        # The spawner's exact call shape.
        #
        # Deliberately NOT "idle": that is also AIHandler's fallback
        # default, so asserting on it would pass whether or not the value
        # persisted — the same vacuous-test trap that let this bug ship.
        setattr(self.mob, "ai_state", "retreating")
        self.assertEqual(AIHandler(self.mob).get_state(), "retreating")

    def test_reading_ai_state_does_not_create_the_attribute(self):
        # autocreate=False is load-bearing. With the default True, this
        # read would write the row, making start_ai()'s
        # attributes.has(...) guard true for every mob and retiring the
        # "wander" default entirely.
        self.mob.ai_state  # noqa: B018 — the read is the point
        self.assertFalse(
            self.mob.attributes.has("ai_state", category="ai_state")
        )


class TestPostSpawnHook(AIStateMachineTest):
    """ms_at_post_spawn — the duck-typed hook evennia-mob-spawner calls."""

    def test_hook_exists_on_a_spawned_mob(self):
        # The library calls it only if present; a rename here silently
        # returns us to mobs that never start their AI.
        self.assertTrue(callable(getattr(self.mob, "ms_at_post_spawn", None)))

    def test_hook_starts_the_ai(self):
        with patch.object(type(self.mob), "start_ai") as mocked:
            self.mob.ms_at_post_spawn()
        mocked.assert_called_once()

    def test_hook_calls_a_parent_hook_before_its_own_work(self):
        # Cooperative chaining: the library calls ms_at_post_spawn once,
        # so a mixin further along the MRO that also defines one must
        # still run. Order matters — the parent goes first.
        calls = []

        class Parent:
            def ms_at_post_spawn(self):
                calls.append("parent")

        class Child(StateMachineAIMixin, Parent):
            def start_ai(self):
                calls.append("own")

        Child().ms_at_post_spawn()
        self.assertEqual(calls, ["parent", "own"])

    def test_hook_does_not_raise_without_a_parent_hook(self):
        # object() has no ms_at_post_spawn, so an unguarded super() call
        # would raise at the end of the chain.
        class Lonely(StateMachineAIMixin):
            def start_ai(self):
                pass

        Lonely().ms_at_post_spawn()  # must not raise


class TestStartAiRespectsSpawnedState(AIStateMachineTest):
    """start_ai() defaults to wander but honours a rule-set state."""

    def test_start_ai_defaults_to_wander(self):
        with patch("typeclasses.actors.mob.TICKER_HANDLER"):
            self.mob.start_ai()
        self.assertEqual(self.mob.ai.get_state(), "wander")

    def test_start_ai_respects_a_preset_state(self):
        # The whole point of attrs: {ai_state: idle} — a stationary mob
        # must not be flipped to wander on startup.
        setattr(self.mob, "ai_state", "idle")
        with patch("typeclasses.actors.mob.TICKER_HANDLER"):
            self.mob.start_ai()
        self.assertEqual(self.mob.ai.get_state(), "idle")

    def test_start_ai_does_nothing_when_dead(self):
        self.mob.is_alive = False
        with patch("typeclasses.actors.mob.TICKER_HANDLER") as ticker:
            self.mob.start_ai()
        ticker.add.assert_not_called()

    def test_spawn_sequence_end_to_end(self):
        # The library's actual order: create, apply attrs, call the hook.
        mob = create.create_object(MOB, key="a spawned mob", location=self.room1)
        setattr(mob, "ai_state", "idle")
        with patch("typeclasses.actors.mob.TICKER_HANDLER") as ticker:
            mob.ms_at_post_spawn()

        self.assertEqual(mob.ai.get_state(), "idle")
        ticker.add.assert_called_once()
