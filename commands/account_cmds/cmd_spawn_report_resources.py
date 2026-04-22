"""
Superuser command: show resource stock across all harvesting rooms.

Queries ObjectDB for objects tagged spawn_resources (the marker
RoomHarvesting applies at creation), then reads each room's
resource_count and spawn_resources_max to produce a per-district
fill report with a cross-zone by-resource roll-up.
"""

from evennia import Command


class CmdSpawnReportResources(Command):
    """
    Show resource stock in all harvesting rooms.

    Usage:
        spawn_report_resources

    Groups harvesting rooms by district and shows current count vs
    cap for each, with [FULL] and [DEPLETED] markers. Ends with a
    by-resource roll-up across all zones.
    """

    key = "spawn_report_resources"
    locks = "cmd:id(1)"
    help_category = "Economy"

    def func(self):
        from collections import defaultdict
        from evennia.objects.models import ObjectDB
        from blockchain.xrpl.currency_cache import get_resource_type
        from typeclasses.terrain.rooms.room_harvesting import RoomHarvesting

        rooms = [
            obj for obj in ObjectDB.objects.filter(
                db_tags__db_key="spawn_resources",
            ).distinct()
            if isinstance(obj, RoomHarvesting)
        ]

        if not rooms:
            self.msg("No harvesting rooms found.")
            return

        # district -> list of (room_key, resource_name, current, cap)
        by_district = defaultdict(list)
        # resource_name -> [total_current, total_cap]
        by_resource = defaultdict(lambda: [0, 0])

        for room in rooms:
            resource_id = room.db.resource_id
            current = room.db.resource_count or 0
            max_dict = room.db.spawn_resources_max or {}
            cap = max_dict.get(resource_id, max_dict.get(str(resource_id), 0))

            rt = get_resource_type(resource_id)
            resource_name = rt["name"] if rt else f"Resource #{resource_id}"

            district = room.tags.get(category="district") or "unknown"
            by_district[district].append((room.key, resource_name, current, cap))

            by_resource[resource_name][0] += current
            by_resource[resource_name][1] += cap

        self.msg("|w=== Resource Harvesting Report ===|n")

        grand_current = 0
        grand_cap = 0
        total_rooms = 0

        for district in sorted(by_district):
            entries = by_district[district]
            d_current = sum(e[2] for e in entries)
            d_cap = sum(e[3] for e in entries)
            grand_current += d_current
            grand_cap += d_cap
            total_rooms += len(entries)

            self.msg(
                f"\n|w{district}|n ({len(entries)} rooms, {d_current}/{d_cap}):"
            )
            for room_key, resource_name, current, cap in sorted(entries):
                pct = int(round(100 * current / cap)) if cap > 0 else 0
                marker = ""
                if cap > 0 and current >= cap:
                    marker = "  |g[FULL]|n"
                elif current == 0:
                    marker = "  |r[DEPLETED]|n"
                self.msg(
                    f"  {room_key:<30} {resource_name:<14} "
                    f"{current:>3} / {cap:<3} ({pct:>3}%){marker}"
                )

        grand_pct = int(round(100 * grand_current / grand_cap)) if grand_cap > 0 else 0
        self.msg(
            f"\n|wTotal:|n {grand_current} / {grand_cap} units "
            f"across {total_rooms} rooms ({grand_pct}% full)"
        )

        if by_resource:
            self.msg("\n|wBy resource:|n")
            for name in sorted(by_resource):
                cur, cap = by_resource[name]
                pct = int(round(100 * cur / cap)) if cap > 0 else 0
                self.msg(f"  {name:<14} {cur:>4} / {cap:<4} ({pct:>3}%)")
