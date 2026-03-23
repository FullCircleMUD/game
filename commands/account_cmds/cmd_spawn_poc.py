"""
Proof-of-concept command to test the resource spawn algorithm.

Hardwires input values and runs the spawn calculation against
real Millholm wheat rooms to verify distribution works end-to-end.

Usage (OOC, superuser only):
    spawnpoc            — run with default hardwired values
    spawnpoc reset      — reset all wheat room resource_count to 0
"""

from decimal import Decimal

from evennia import Command

from blockchain.xrpl.services.resource_spawn import ResourceSpawnService
from world.economy.resource_spawn_config import RESOURCE_SPAWN_CONFIG


# ── Hardwired test values ─────────────────────────────────────────────
STUB_CONSUMPTION_RATE = 20.0       # 20 wheat consumed per hour (avg)
STUB_BUY_PRICE = Decimal("12")    # midpoint of 8-15 target band
STUB_PLAYER_HOURS_7D = 50.0       # 50 player-hours over past week
STUB_CIRCULATING_SUPPLY = Decimal("200")  # 200 wheat in player hands
RESOURCE_ID = 1                    # Wheat


class CmdSpawnPoc(Command):
    """
    Test the resource spawn algorithm with hardwired values.

    Usage:
        spawnpoc        - run spawn calculation and distribute to wheat rooms
        spawnpoc reset  - reset all wheat room resource_count to 0
    """

    key = "spawnpoc"
    locks = "cmd:id(1) and is_ooc()"
    help_category = "Economy"

    def func(self):
        if self.args.strip().lower() == "reset":
            _reset_wheat_rooms(self.caller)
            return
        _run_spawn_poc(self.caller)


def _reset_wheat_rooms(caller):
    """Reset all wheat RoomHarvesting rooms to resource_count=0."""
    from evennia.objects.models import ObjectDB

    rooms = ObjectDB.objects.filter(
        db_typeclass_path__contains="RoomHarvesting",
    )

    count = 0
    for room in rooms:
        if room.resource_id != RESOURCE_ID:
            continue
        room.resource_count = 0
        count += 1

    caller.msg(f"|gReset {count} wheat rooms to resource_count=0.|n")


def _run_spawn_poc(caller):
    """Run the spawn algorithm with hardwired values and report results."""
    from evennia.objects.models import ObjectDB

    config = RESOURCE_SPAWN_CONFIG[RESOURCE_ID]

    # ── Show hardwired inputs ──
    caller.msg("|c=== Resource Spawn POC (Wheat) ===|n")
    caller.msg(f"|wConsumption rate (24h avg):|n {STUB_CONSUMPTION_RATE}/hr")
    caller.msg(f"|wAMM buy price:|n {STUB_BUY_PRICE} gold")
    caller.msg(f"|wPlayer-hours (7d):|n {STUB_PLAYER_HOURS_7D}")
    caller.msg(f"|wCirculating supply:|n {STUB_CIRCULATING_SUPPLY}")
    caller.msg(
        f"|wConfig:|n price band [{config['target_price_low']}-"
        f"{config['target_price_high']}], "
        f"target supply/ph={config['target_supply_per_ph']}, "
        f"mod range [{config['modifier_min']}-{config['modifier_max']}]"
    )

    # ── Calculate modifiers ──
    p_mod = ResourceSpawnService.price_modifier(STUB_BUY_PRICE, config)
    s_mod = ResourceSpawnService.supply_modifier(
        STUB_CIRCULATING_SUPPLY, STUB_PLAYER_HOURS_7D, config,
    )

    caller.msg("")
    caller.msg(f"|wPrice modifier:|n {p_mod:.3f}")
    caller.msg(f"|wSupply modifier:|n {s_mod:.3f}")

    # ── Calculate spawn amount ──
    spawn_amount = STUB_CONSUMPTION_RATE * p_mod * s_mod
    spawn_int = max(0, round(spawn_amount))

    caller.msg(
        f"|wSpawn amount:|n {STUB_CONSUMPTION_RATE} x {p_mod:.3f} x "
        f"{s_mod:.3f} = {spawn_amount:.2f} -> {spawn_int}"
    )

    if spawn_int <= 0:
        caller.msg("|yNo resources to spawn.|n")
        return

    # ── Show rooms BEFORE ──
    rooms = ObjectDB.objects.filter(
        db_typeclass_path__contains="RoomHarvesting",
    )
    wheat_rooms = []
    for room in rooms:
        if room.resource_id == RESOURCE_ID:
            wheat_rooms.append(room)

    caller.msg(f"\n|c--- Wheat Rooms ({len(wheat_rooms)} total) ---|n")
    caller.msg(f"  {'Room':<35} {'Weight':>6} {'Before':>6} {'Max':>6}")
    for room in sorted(wheat_rooms, key=lambda r: r.key):
        caller.msg(
            f"  {room.key:<35} {room.spawn_rate_weight:>6} "
            f"{room.resource_count or 0:>6} {room.max_resource_count:>6}"
        )

    # ── Distribute ──
    total_distributed = ResourceSpawnService.distribute_to_rooms(
        RESOURCE_ID, spawn_int, config["max_per_room"],
    )

    # ── Show rooms AFTER ──
    caller.msg(f"\n|c--- After Distribution ({total_distributed} distributed) ---|n")
    caller.msg(f"  {'Room':<35} {'Weight':>6} {'After':>6} {'Max':>6}")
    for room in sorted(wheat_rooms, key=lambda r: r.key):
        caller.msg(
            f"  {room.key:<35} {room.spawn_rate_weight:>6} "
            f"{room.resource_count or 0:>6} {room.max_resource_count:>6}"
        )

    caller.msg(f"\n|gDone. {total_distributed} wheat distributed to rooms.|n")
