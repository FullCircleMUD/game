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
        from blockchain.xrpl.services.spawn.service import (
            get_spawn_service, set_spawn_service, SpawnService,
        )

        service = get_spawn_service()
        if not service:
            # Service singleton not set — create it on the fly
            from blockchain.xrpl.services.spawn.config import SPAWN_CONFIG
            service = SpawnService(SPAWN_CONFIG)
            set_spawn_service(service)
            self.msg("|y[Created SpawnService on the fly]|n")

        self.msg("|yRunning spawn cycle...|n")

        # Show budgets before distributing
        from blockchain.xrpl.currency_cache import get_resource_type
        for (item_type, type_key), cfg in service.config.items():
            calculator_name = cfg.get("calculator")
            if not calculator_name:
                continue
            calculator = service._calculators.get(calculator_name)
            if not calculator:
                continue
            try:
                budget = calculator.calculate(item_type, type_key)
            except Exception as e:
                self.msg(f"  |r{item_type}/{type_key}: ERROR {e}|n")
                continue
            # Resolve display name for resources
            name = type_key
            if item_type == "resource":
                rt = get_resource_type(type_key)
                name = rt["name"] if rt else f"id={type_key}"

            if item_type == "resource":
                from blockchain.xrpl.services.spawn.calculators.resource import ResourceCalculator
                avg = ResourceCalculator._get_avg_consumption(type_key)
                price = ResourceCalculator._get_latest_buy_price(type_key)
                p_mod = ResourceCalculator.price_modifier(price, cfg)
                base = max(float(cfg["default_spawn_rate"]), float(avg))
                low = cfg["target_price_low"]
                high = cfg["target_price_high"]
                price_str = f"{float(price):.2f}" if price is not None else "N/A"
                color = "" if budget > 0 else "|x"
                end = "" if budget > 0 else "|n"
                self.msg(
                    f"  {color}{name}: budget={budget} "
                    f"(base={base:.1f}, price={price_str} [{low}-{high}], "
                    f"p_mod={p_mod:.2f}){end}"
                )
            elif budget > 0:
                self.msg(f"  {item_type}/{type_key}: budget={budget}")

        service.run_hourly_cycle()
        self.msg("|gSpawn cycle complete.|n")
