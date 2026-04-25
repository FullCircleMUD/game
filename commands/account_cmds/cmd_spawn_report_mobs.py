"""
Superuser command: show mobs placed by the dynamic spawn system.

Filters ObjectDB for objects tagged with category="spawn_zone" (the marker
ZoneSpawnScript applies to every mob it creates). Static zone-built NPCs,
shopkeepers, trainers, pets, and summons lack this tag and are excluded.
"""

from evennia import Command


class CmdSpawnReportMobs(Command):
    """
    Show all mobs spawned by the dynamic spawn system.

    Usage:
        spawn_report_mobs

    Groups mobs by district (spawn_zone tag) with per-name counts.
    """

    key = "spawn_report_mobs"
    locks = "cmd:id(1)"
    help_category = "Economy"

    def func(self):
        from collections import defaultdict
        from evennia.objects.models import ObjectDB

        spawned = ObjectDB.objects.filter(
            db_tags__db_category="spawn_zone",
        ).exclude(
            db_location__isnull=True,
        ).distinct()

        if not spawned.exists():
            self.msg("No spawned mobs currently in the game world.")
            return

        by_district = defaultdict(lambda: defaultdict(int))

        for mob in spawned:
            district = mob.tags.get(category="spawn_zone") or "unknown"
            by_district[district][mob.key] += 1

        self.msg("|w=== Spawned Mob Report ===|n")

        grand_total = 0
        for district in sorted(by_district):
            counts = by_district[district]
            district_total = sum(counts.values())
            grand_total += district_total
            self.msg(f"\n|w{district}|n ({district_total} total):")
            for name, count in sorted(counts.items()):
                self.msg(f"  {name}: {count}")

        self.msg(f"\n|wTotal spawned:|n {grand_total}")
