"""
Superuser command: show resource stock across all harvesting rooms.

Router-only cluster-wide report. The router runs ObjectDB unscoped, so it
is the only process that can see every shard's rooms at once — but that
also means it must never instantiate what it finds: doing so would pull
every shard's harvesting rooms into the router's process-wide idmapper,
the anti-pattern blockchain/xrpl/services/spawn/reader.py exists to avoid
on the write side. Every read here is a .values() projection instead;
nothing in this module calls .db on an instantiated room.
"""

from evennia import Command
from evennia_shards import ROLE_MONOLITH, ROLE_ROUTER, get_role

# Typeclass paths standing in for `isinstance(obj, RoomHarvesting)` — a
# .values() query has no notion of subclassing, so a future subclass must
# be added here explicitly to be picked up by the report.
HARVESTING_ROOM_TYPECLASSES = [
    "typeclasses.terrain.rooms.room_harvesting.RoomHarvesting",
]


def _room_attributes(room_pks, attr_names):
    """Return {pk: {attr_name: value}} for the named uncategorised attributes.

    Same shape as spawn/reader.py's _target_attributes() — missing
    attributes come back as None, matching what room.db.x yields for an
    attribute that was never set.
    """
    from evennia.objects.models import ObjectDB

    attrs = {pk: {name: None for name in attr_names} for pk in room_pks}
    if not room_pks:
        return attrs

    rows = ObjectDB.objects.filter(
        id__in=room_pks,
        db_attributes__db_key__in=attr_names,
        # Load-bearing: matches room.db.x semantics — without it a
        # same-named attribute in another category joins as an extra row.
        db_attributes__db_category__isnull=True,
    ).values_list("id", "db_attributes__db_key", "db_attributes__db_value")

    for pk, attr_name, value in rows:
        attrs.setdefault(pk, {})[attr_name] = value

    return attrs


class CmdSpawnReportResources(Command):
    """
    Show resource stock in all harvesting rooms.

    Usage:
        spawn_report_resources

    Groups harvesting rooms by district and shows current count vs
    cap for each, with [FULL] and [DEPLETED] markers. Ends with a
    by-resource roll-up across all zones.

    Router-only: a cluster-wide view is only available where ObjectDB
    runs unscoped. Never instantiates a room — see
    HARVESTING_ROOM_TYPECLASSES above.
    """

    key = "spawn_report_resources"
    locks = "cmd:id(1)"
    help_category = "Economy"

    def func(self):
        caller = self.caller
        if get_role() not in (ROLE_MONOLITH, ROLE_ROUTER):
            caller.msg("|rThis command can only be run OOC on the router.|n")
            return

        from collections import defaultdict
        from evennia.objects.models import ObjectDB
        from blockchain.xrpl.currency_cache import get_resource_type

        room_rows = list(
            ObjectDB.objects.filter(
                db_tags__db_key="spawn_resources",
                db_tags__db_category="spawn_resources",
                db_typeclass_path__in=HARVESTING_ROOM_TYPECLASSES,
            ).distinct().values_list("id", "db_key")
        )

        if not room_rows:
            self.msg("No harvesting rooms found.")
            return

        room_pks = [pk for pk, _key in room_rows]
        room_keys = dict(room_rows)

        district_rows = ObjectDB.objects.filter(
            id__in=room_pks,
            db_tags__db_category="district",
        ).values_list("id", "db_tags__db_key")
        districts = dict(district_rows)

        attrs = _room_attributes(
            room_pks, ("resource_id", "resource_count", "spawn_resources_max")
        )

        # district -> list of (room_key, resource_name, current, cap)
        by_district = defaultdict(list)
        # resource_name -> [total_current, total_cap]
        by_resource = defaultdict(lambda: [0, 0])

        for pk in room_pks:
            values = attrs[pk]
            resource_id = values.get("resource_id")
            current = values.get("resource_count") or 0
            max_dict = values.get("spawn_resources_max") or {}
            cap = max_dict.get(resource_id, max_dict.get(str(resource_id), 0))

            rt = get_resource_type(resource_id)
            resource_name = rt["name"] if rt else f"Resource #{resource_id}"

            district = districts.get(pk, "unknown")
            by_district[district].append((room_keys[pk], resource_name, current, cap))

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
