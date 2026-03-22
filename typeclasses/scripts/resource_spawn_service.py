"""
ResourceSpawnScript — global script that replenishes RoomHarvesting nodes hourly.

Ticks every hour (aligned with telemetry snapshots) and delegates to
ResourceSpawnService.calculate_and_apply() which reads economy data
and distributes resources across harvest rooms.
"""

from evennia import DefaultScript


# How often (real seconds) the spawn service runs.
TICK_INTERVAL_SECONDS = 3600  # 1 hour


class ResourceSpawnScript(DefaultScript):
    """
    Global persistent script for hourly resource replenishment.

    Created once via at_server_startstop._ensure_global_scripts().
    """

    def at_script_creation(self):
        self.key = "resource_spawn_service"
        self.desc = "Hourly resource replenishment based on economy data"
        self.interval = TICK_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = True
        self.repeats = 0  # repeat forever

    def at_repeat(self):
        """Calculate and apply resource spawns."""
        from blockchain.xrpl.services.resource_spawn import ResourceSpawnService

        ResourceSpawnService.calculate_and_apply()
