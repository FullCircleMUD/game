"""
Reusable post-spawn hooks for ZoneSpawnScript JSON rules —
SUSPECTED DEAD, pending confirmation before deletion.

`set_ai_idle` was the only consumer-facing hook here. Its function
(parking a freshly-spawned mob in the idle AI state) is now
expressed declaratively per-rule via `attrs: {ai_state: idle}` in
the fcm-mobs YAML rules, honoured by `CombatMob.start_ai()` which
respects a pre-set `ai_state` attribute. No runtime hook is needed.
"""

# def set_ai_idle(mob):
#     """Post-spawn hook: park the mob in the idle AI state.
#
#     Use for stationary, non-combat NPCs that should not wander or
#     aggress. Generic CombatMobs default to 'wander' on start_ai(),
#     which moves them 30% of ticks — this hook keeps them in place.
#     """
#     mob.ai.set_state("idle")
