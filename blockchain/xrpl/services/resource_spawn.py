"""
Resource spawn service — hourly replenishment of RoomHarvesting nodes.

Calculates how much of each raw resource to spawn based on three factors:
1. Consumption rate (baseline) — what players are actually using (from SINK data)
2. AMM price modifier — spawn more when price is high, less when low
3. Circulating supply per player-hour — structural over/undersupply check

Then distributes the spawn amount across RoomHarvesting rooms weighted by
each room's spawn_rate_weight (1-5), capped at max_resource_count.

Distribution is drip-fed across the hour: each room receives its allocation
in evenly spaced ticks (min 5 minutes apart) via delay() calls rather than
a single batch dump.

Called hourly by ResourceSpawnScript.
"""

import logging
import math
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, F, ExpressionWrapper, DurationField
from django.db.models.functions import Coalesce
from django.utils import timezone
from evennia.utils.utils import delay

logger = logging.getLogger("evennia")

# Maximum number of drip ticks per hour (every 5 minutes).
MAX_TICKS_PER_HOUR = 12


class ResourceSpawnService:
    """Stateless service — all methods are static, called hourly."""

    @staticmethod
    def calculate_and_apply():
        """Main entry point. Called hourly by the script.

        1. Check there are players online (no spawn to empty server)
        2. Fetch all RoomHarvesting rooms once, group by resource_id
        3. Calculate player-hours over past 7 days
        4. For each configured resource:
           a. Get 24h avg consumption rate
           b. Calculate price modifier from AMM data
           c. Calculate supply-per-player-hour modifier
           d. spawn_amount = consumption × price_mod × supply_mod
           e. Calculate per-room allocations by weight
           f. Schedule drip-feed distribution across the hour
        """
        from blockchain.xrpl.models import EconomySnapshot

        from world.economy.resource_spawn_config import RESOURCE_SPAWN_CONFIG

        # Check someone is playing
        latest = EconomySnapshot.objects.order_by("-hour").first()
        if not latest or latest.players_online == 0:
            logger.info("ResourceSpawn: no players online, skipping")
            return

        # Single DB query — group all harvest rooms by resource_id
        rooms_by_resource = ResourceSpawnService._load_harvest_rooms()

        player_hours = ResourceSpawnService.get_player_hours_7d()
        summary = []

        for resource_id, config in RESOURCE_SPAWN_CONFIG.items():
            rooms = rooms_by_resource.get(resource_id, [])
            spawned = ResourceSpawnService._process_resource(
                resource_id, config, player_hours, rooms,
            )
            if spawned > 0:
                summary.append(f"r{resource_id}={spawned}")

        if summary:
            logger.info(f"ResourceSpawn: {', '.join(summary)}")
        else:
            logger.info("ResourceSpawn: no resources spawned this tick")

    @staticmethod
    def _load_harvest_rooms():
        """Fetch all RoomHarvesting rooms once, return {resource_id: [room]}.

        Single DB query instead of one per resource.
        """
        from evennia.objects.models import ObjectDB

        all_rooms = ObjectDB.objects.filter(
            db_typeclass_path__contains="RoomHarvesting",
        )
        by_resource = defaultdict(list)
        for room_obj in all_rooms:
            rid = room_obj.resource_id
            if rid is not None:
                by_resource[rid].append(room_obj)
        return by_resource

    @staticmethod
    def _process_resource(resource_id, config, player_hours, rooms):
        """Calculate and schedule drip-feed spawn for a single resource.

        Returns total amount allocated (will be distributed over the hour).
        """
        from blockchain.xrpl.currency_cache import get_currency_code

        currency_code = get_currency_code(resource_id)
        if not currency_code:
            return 0

        # Baseline: 24h rolling average consumption
        avg_consumption = ResourceSpawnService.get_avg_consumption_24h(
            currency_code,
        )
        if avg_consumption <= 0:
            # Cold start — no consumption data yet, use fallback
            base_rate = float(config["default_spawn_rate"])
        else:
            base_rate = float(avg_consumption)

        # Price modifier
        buy_price = ResourceSpawnService.get_latest_buy_price(currency_code)
        p_mod = ResourceSpawnService.price_modifier(buy_price, config)

        # Supply-per-player-hour modifier
        circulating = ResourceSpawnService.get_circulating_supply(
            currency_code,
        )
        s_mod = ResourceSpawnService.supply_modifier(
            circulating, player_hours, config,
        )

        # Combined spawn amount
        spawn_amount = base_rate * p_mod * s_mod
        spawn_int = max(0, round(spawn_amount))

        if spawn_int <= 0:
            return 0

        # Calculate per-room allocations, then drip-feed
        allocations = ResourceSpawnService.calculate_room_allocations(
            rooms, spawn_int, config["max_per_room"],
        )
        if not allocations:
            return 0

        total = sum(a for _, a in allocations)
        ResourceSpawnService.schedule_drip_feed(allocations)
        return total

    # ================================================================== #
    #  Data queries
    # ================================================================== #

    @staticmethod
    def get_player_hours_7d():
        """Sum total player-hours from PlayerSession over past 7 days.

        Open sessions (ended_at is NULL) use now() as the end time.
        Returns float hours.
        """
        from blockchain.xrpl.models import PlayerSession

        cutoff = timezone.now() - timedelta(days=7)
        now = timezone.now()

        sessions = PlayerSession.objects.filter(
            started_at__gte=cutoff,
        )

        total_seconds = Decimal(0)
        for session in sessions:
            end = session.ended_at or now
            # Clamp start to cutoff (session may have started before window)
            start = max(session.started_at, cutoff)
            delta = (end - start).total_seconds()
            if delta > 0:
                total_seconds += Decimal(str(delta))

        return float(total_seconds / 3600)

    @staticmethod
    def get_avg_consumption_24h(currency_code):
        """24-hour rolling average of consumed_1h from ResourceSnapshot.

        Returns Decimal (average hourly consumption over last 24 snapshots).
        """
        from blockchain.xrpl.models import ResourceSnapshot

        snapshots = (
            ResourceSnapshot.objects.filter(currency_code=currency_code)
            .order_by("-hour")[:24]
        )
        values = [s.consumed_1h for s in snapshots]
        if not values:
            return Decimal(0)
        return sum(values) / len(values)

    @staticmethod
    def get_latest_buy_price(currency_code):
        """Get the most recent AMM buy price for a resource.

        Returns Decimal or None if no AMM pool exists.
        """
        from blockchain.xrpl.models import ResourceSnapshot

        snapshot = (
            ResourceSnapshot.objects.filter(
                currency_code=currency_code,
                amm_buy_price__isnull=False,
            )
            .order_by("-hour")
            .first()
        )
        return snapshot.amm_buy_price if snapshot else None

    @staticmethod
    def get_circulating_supply(currency_code):
        """Get current circulating supply (CHARACTER + ACCOUNT).

        Returns Decimal.
        """
        from blockchain.xrpl.models import FungibleGameState

        result = (
            FungibleGameState.objects.filter(
                currency_code=currency_code,
                location__in=[
                    FungibleGameState.LOCATION_CHARACTER,
                    FungibleGameState.LOCATION_ACCOUNT,
                ],
            ).aggregate(total=Sum("balance"))["total"]
        )
        return result or Decimal(0)

    # ================================================================== #
    #  Modifier curves
    # ================================================================== #

    @staticmethod
    def price_modifier(buy_price, config):
        """Linear interpolation of price within target band.

        Two-segment curve with 1.0 at the midpoint:
          price <= low  → modifier_min
          price = mid   → 1.0
          price >= high → modifier_max

        Returns 1.0 if buy_price is None (no AMM pool).
        """
        if buy_price is None:
            return 1.0

        price = float(buy_price)
        low = float(config["target_price_low"])
        high = float(config["target_price_high"])
        mod_min = float(config["modifier_min"])
        mod_max = float(config["modifier_max"])
        midpoint = (low + high) / 2.0

        if price <= low:
            return mod_min
        elif price >= high:
            return mod_max
        elif price <= midpoint:
            t = (price - low) / (midpoint - low)
            return mod_min + t * (1.0 - mod_min)
        else:
            t = (price - midpoint) / (high - midpoint)
            return 1.0 + t * (mod_max - 1.0)

    @staticmethod
    def supply_modifier(circulating, player_hours_7d, config):
        """Compare circulating supply per player-hour against target.

        Inverted curve — high supply means REDUCE spawns:
          ratio = 0  → modifier_max (extreme undersupply, boost hard)
          ratio = 1  → 1.0 (on target)
          ratio >= 2 → modifier_min (oversupply, cut spawns)

        Returns 1.0 if player_hours_7d is zero (can't compute).
        """
        if player_hours_7d <= 0:
            return 1.0

        target = float(config["target_supply_per_ph"])
        if target <= 0:
            return 1.0

        actual_per_ph = float(circulating) / player_hours_7d
        ratio = actual_per_ph / target

        mod_min = float(config["modifier_min"])
        mod_max = float(config["modifier_max"])

        if ratio <= 0:
            return mod_max
        elif ratio >= 2.0:
            return mod_min
        elif ratio <= 1.0:
            # Undersupply: interpolate from modifier_max to 1.0
            return mod_max + ratio * (1.0 - mod_max)
        else:
            # Oversupply: interpolate from 1.0 to modifier_min
            t = ratio - 1.0
            return 1.0 + t * (mod_min - 1.0)

    # ================================================================== #
    #  Room allocation & drip-feed distribution
    # ================================================================== #

    @staticmethod
    def calculate_room_allocations(rooms, amount, max_per_room):
        """Calculate per-room spawn allocations by weight.

        Each room has a spawn_rate_weight (1-5). Allocation:
        1. Sum all weights for eligible rooms
        2. per_weight_unit = amount / total_weight
        3. Each room gets floor(weight × per_weight_unit)
        4. Remainder distributed 1-at-a-time, highest weight first
        5. Each room capped at max_resource_count

        Args:
            rooms: list of RoomHarvesting objects for this resource
            amount: total resources to allocate
            max_per_room: cap per room

        Returns list of (room_obj, allocation) tuples.
        """
        # Collect (room, weight, headroom) tuples
        candidates = []
        for room_obj in rooms:
            current = room_obj.resource_count or 0
            max_count = room_obj.max_resource_count
            headroom = max(0, max_count - current)
            if headroom <= 0:
                continue
            weight = max(1, min(5, room_obj.spawn_rate_weight))
            candidates.append((room_obj, weight, headroom))

        if not candidates:
            return []

        total_weight = sum(w for _, w, _ in candidates)
        if total_weight <= 0:
            return []

        per_weight = amount / total_weight

        # Phase 1: floor allocation
        allocations = []
        allocated_total = 0
        for room_obj, weight, headroom in candidates:
            raw = math.floor(weight * per_weight)
            capped = min(raw, headroom)
            allocations.append([room_obj, weight, headroom, capped])
            allocated_total += capped

        # Phase 2: distribute remainder, highest weight first
        remainder = amount - allocated_total
        if remainder > 0:
            allocations.sort(key=lambda x: x[1], reverse=True)
            while remainder > 0:
                distributed_any = False
                for alloc in allocations:
                    if remainder <= 0:
                        break
                    room_obj, weight, headroom, current_alloc = alloc
                    can_add = headroom - current_alloc
                    if can_add > 0:
                        alloc[3] += 1
                        remainder -= 1
                        distributed_any = True
                if not distributed_any:
                    break

        return [
            (room_obj, alloc)
            for room_obj, _w, _h, alloc in allocations
            if alloc > 0
        ]

    @staticmethod
    def schedule_drip_feed(allocations):
        """Schedule delayed distribution for each room across the hour.

        Each room gets its allocation spread over evenly spaced ticks,
        with a minimum interval of 5 minutes (max 12 ticks per hour).

        Room due 1  → 1 drop at minute 0
        Room due 4  → 1 drop every 15 min
        Room due 12 → 1 drop every 5 min
        Room due 30 → drops of 2-3 every 5 min
        """
        for room_obj, total in allocations:
            num_ticks = min(total, MAX_TICKS_PER_HOUR)
            interval = 3600.0 / num_ticks
            per_tick_base = total // num_ticks
            extra = total % num_ticks

            for i in range(num_ticks):
                drop = per_tick_base + (1 if i < extra else 0)
                delay_seconds = i * interval
                delay(delay_seconds, _apply_drip, room_obj, drop)

    @staticmethod
    def distribute_to_rooms(resource_id, amount, max_per_room):
        """Immediate distribution — used by POC command and tests.

        Calculates allocations and applies them all at once (no delay).
        Returns total amount actually added across all rooms.
        """
        rooms = ResourceSpawnService._load_harvest_rooms().get(
            resource_id, [],
        )
        allocations = ResourceSpawnService.calculate_room_allocations(
            rooms, amount, max_per_room,
        )
        total = 0
        for room_obj, alloc in allocations:
            room_obj.resource_count = (room_obj.resource_count or 0) + alloc
            total += alloc
        return total


def _apply_drip(room_obj, amount):
    """Callback for delayed drip-feed. Adds resources capped at max."""
    current = room_obj.resource_count or 0
    max_count = room_obj.max_resource_count
    headroom = max(0, max_count - current)
    actual = min(amount, headroom)
    if actual > 0:
        room_obj.resource_count = current + actual
