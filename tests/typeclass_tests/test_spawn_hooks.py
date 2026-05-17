"""
Tests for reusable post-spawn hooks — SUSPECTED DEAD, pending
confirmation before deletion.

`set_ai_idle` (the only function this module tested) is retired.
Its job is now done declaratively via `attrs: {ai_state: idle}` in
the fcm-mobs YAML rules, honoured by `CombatMob.start_ai()`. The
equivalent test for the new pattern would assert that a mob created
with `db.ai_state = "idle"` has `mob.ai.get_state() == "idle"` after
`start_ai()` runs — captured here as a TODO for the post-deletion
sweep, since `start_ai()` registers with `TICKER_HANDLER` which is
not safe to invoke from a unit test without further setup.
"""

# from evennia.utils import create
# from evennia.utils.test_resources import EvenniaTest
#
# from typeclasses.scripts.spawn_hooks import set_ai_idle
#
#
# class TestSetAIIdle(EvenniaTest):
#     """set_ai_idle flips a mob's AI state to 'idle'."""
#
#     room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
#
#     def create_script(self):
#         pass
#
#     def test_set_ai_idle_sets_state(self):
#         mob = create.create_object(
#             "typeclasses.actors.mob.CombatMob",
#             key="House NPC",
#             location=self.room1,
#         )
#         mob.ai.set_state("wander")
#         self.assertEqual(mob.ai.get_state(), "wander")
#
#         set_ai_idle(mob)
#         self.assertEqual(mob.ai.get_state(), "idle")
