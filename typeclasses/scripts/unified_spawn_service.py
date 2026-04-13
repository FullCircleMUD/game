"""
UnifiedSpawnScript — global script that drives the unified spawn system.

Ticks every hour and delegates to SpawnService.run_hourly_cycle()
which runs all calculators and distributors for every SPAWN_CONFIG entry.
"""

from evennia import DefaultScript
from twisted.internet import threads


# How often (real seconds) the spawn service runs.
# Runs last in the hourly pipeline: telemetry → saturation → spawn.
# All three pipeline scripts use the same 3600s interval. The 120-second
# offset behind telemetry is established once at cold boot by staggering
# the script creation moments — see at_server_startstop.py
# _ensure_pipeline_scripts(). Once created the offset is preserved
# indefinitely, with zero drift.
TICK_INTERVAL_SECONDS = 3600  # 1 hour


class UnifiedSpawnScript(DefaultScript):
    """
    Global persistent script for the unified item spawn system.

    Created once via at_server_startstop._ensure_global_scripts().
    """

    def at_script_creation(self):
        self.key = "unified_spawn_service"
        self.desc = "Unified hourly spawn system for resources, gold, and NFTs"
        self.interval = TICK_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = True
        self.repeats = 0  # repeat forever

    def at_start(self, **kwargs):
        """Register the SpawnService singleton when the script starts."""
        from blockchain.xrpl.services.spawn.config import SPAWN_CONFIG
        from blockchain.xrpl.services.spawn.service import SpawnService, set_spawn_service

        self._service = SpawnService(SPAWN_CONFIG)
        set_spawn_service(self._service)

    def at_repeat(self):
        """Run the full hourly spawn cycle in a background thread."""
        if hasattr(self, "_service"):
            threads.deferToThread(self._service.run_hourly_cycle)
