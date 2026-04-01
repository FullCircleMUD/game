"""
Superuser command: trigger a full unified spawn cycle out of cycle.

The spawn system normally runs once per hour. This command forces an
immediate cycle so resources, gold, and knowledge items are distributed
to their targets (rooms, mobs, containers).

Runs in a background thread so the game stays responsive.
"""

from evennia import Command
from twisted.internet import threads


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
    help_category = "Economy"

    def func(self):
        caller = self

        def _run():
            """Heavy work — runs in a thread pool."""
            from blockchain.xrpl.services.spawn.service import (
                get_spawn_service, set_spawn_service, SpawnService,
            )

            service = get_spawn_service()
            if not service:
                from blockchain.xrpl.services.spawn.config import SPAWN_CONFIG
                service = SpawnService(SPAWN_CONFIG)
                set_spawn_service(service)
                caller.msg("|y[Created SpawnService on the fly]|n")

            # Show budgets before distributing
            from blockchain.xrpl.currency_cache import get_resource_type
            from blockchain.xrpl.services.spawn.calculators.resource import ResourceCalculator
            from blockchain.xrpl.services.spawn.calculators.knowledge import KnowledgeCalculator

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
                    caller.msg(f"  |r{item_type}/{type_key}: ERROR {e}|n")
                    continue

                # Fixed-width name column (30 chars, truncated if needed)
                W = 30

                if item_type == "resource":
                    rt = get_resource_type(type_key)
                    name = (rt["name"] if rt else f"id={type_key}")[:W].ljust(W)
                    avg = ResourceCalculator._get_avg_consumption(type_key)
                    price = ResourceCalculator._get_latest_buy_price(type_key)
                    p_mod = ResourceCalculator.price_modifier(price, cfg)
                    base = max(float(cfg["default_spawn_rate"]), float(avg))
                    low = cfg["target_price_low"]
                    high = cfg["target_price_high"]
                    price_str = f"{float(price):.2f}" if price is not None else "N/A"
                    color = "" if budget > 0 else "|x"
                    end = "" if budget > 0 else "|n"
                    caller.msg(
                        f"  {color}{name} budget={budget} "
                        f"(base={base:.1f}, price={price_str} [{low}-{high}], "
                        f"p_mod={p_mod:.2f}){end}"
                    )
                elif item_type == "knowledge":
                    tier = cfg.get("tier", "?")
                    snapshot = KnowledgeCalculator._get_snapshot(type_key)
                    if snapshot:
                        elig = snapshot.eligible_players
                        known = snapshot.known_by
                        unlearned = snapshot.unlearned_copies
                        sat_str = f"{snapshot.saturation:.0%}"
                        gap_str = f"gap={elig}-{known}-{unlearned}={budget}"
                    else:
                        sat_str = "no data"
                        gap_str = f"gap=?"
                    kind = "scroll" if str(type_key).startswith("scroll_") else "recipe"
                    display_name = str(type_key).replace("scroll_", "").replace("recipe_", "").replace("_", " ").title()
                    label = f"[{kind}] {display_name}"[:W].ljust(W)
                    color = "" if budget > 0 else "|x"
                    end = "" if budget > 0 else "|n"
                    caller.msg(
                        f"  {color}{label} budget={budget} "
                        f"({gap_str}, sat={sat_str}, tier={tier}){end}"
                    )
                elif budget > 0:
                    label = f"{item_type}/{type_key}"[:W].ljust(W)
                    caller.msg(f"  {label} budget={budget}")

            service.run_hourly_cycle()
            return True

        self.msg("|yRunning spawn cycle...|n")
        d = threads.deferToThread(_run)
        d.addCallback(lambda _: self.msg("|gSpawn cycle complete.|n"))
        d.addErrback(
            lambda f: self.msg(f"|rSpawn cycle failed: {f.getErrorMessage()}|n")
        )
