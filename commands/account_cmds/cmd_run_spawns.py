"""
Superuser command: trigger a full unified spawn cycle out of cycle.

The spawn system normally runs once per hour. This command forces an
immediate cycle so resources, gold, and knowledge items are distributed
to their targets (rooms, mobs, containers).
"""

from evennia import Command


class CmdRunSpawns(Command):
    """
    Force a full spawn cycle now.

    Usage:
        run_spawns

    Triggers the hourly unified spawn cycle immediately. Distributes
    resources, gold, and knowledge items (scrolls/recipes) to all
    tagged targets in the game world.
    """

    key = "run_spawns"
    locks = "cmd:id(1)"
    help_category = "System"

    def func(self):
        from blockchain.xrpl.services.spawn.service import get_spawn_service

        service = get_spawn_service()
        if not service:
            self.msg(
                "|rSpawn service not running. "
                "Ensure UnifiedSpawnScript is active.|n"
            )
            return

        self.msg("|yRunning spawn cycle...|n")

        # Show budgets before distributing
        for (item_type, type_key), cfg in service.config.items():
            calculator_name = cfg.get("calculator")
            if not calculator_name:
                continue
            calculator = service._calculators.get(calculator_name)
            if not calculator:
                continue
            try:
                budget = calculator.calculate(item_type, type_key)
            except Exception:
                budget = 0
            if budget > 0:
                self.msg(f"  {item_type}/{type_key}: budget={budget}")

        service.run_hourly_cycle()
        self.msg("|gSpawn cycle complete.|n")
