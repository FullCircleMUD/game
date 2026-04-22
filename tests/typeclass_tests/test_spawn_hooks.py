"""
Tests for reusable post-spawn hooks (typeclasses.scripts.spawn_hooks).

evennia test --settings settings tests.typeclass_tests.test_spawn_hooks
"""

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from typeclasses.scripts.spawn_hooks import set_ai_idle


class TestSetAIIdle(EvenniaTest):
    """set_ai_idle flips a mob's AI state to 'idle'."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_set_ai_idle_sets_state(self):
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="House NPC",
            location=self.room1,
        )
        mob.ai.set_state("wander")
        self.assertEqual(mob.ai.get_state(), "wander")

        set_ai_idle(mob)
        self.assertEqual(mob.ai.get_state(), "idle")
