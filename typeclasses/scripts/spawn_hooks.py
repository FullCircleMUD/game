"""Reusable post-spawn hooks for ZoneSpawnScript JSON rules."""


def set_ai_idle(mob):
    """Post-spawn hook: park the mob in the idle AI state.

    Use for stationary, non-combat NPCs that should not wander or
    aggress. Generic CombatMobs default to 'wander' on start_ai(),
    which moves them 30% of ticks — this hook keeps them in place.
    """
    mob.ai.set_state("idle")
