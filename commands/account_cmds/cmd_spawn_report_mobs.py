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

    Groups mobs by district (spawn_zone tag), then splits each district
    into Commodity and Boss subsections with per-name counts.
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

        # district -> {"commodity": {name: count}, "boss": {name: count}}
        by_district = defaultdict(lambda: {"commodity": defaultdict(int), "boss": defaultdict(int)})

        for mob in spawned:
            district = mob.tags.get(category="spawn_zone") or "unknown"
            kind = "boss" if mob.attributes.get("is_unique") else "commodity"
            by_district[district][kind][mob.key] += 1

        self.msg("|w=== Spawned Mob Report ===|n")

        grand_total = 0
        for district in sorted(by_district):
            groups = by_district[district]
            district_total = sum(groups["commodity"].values()) + sum(groups["boss"].values())
            grand_total += district_total
            self.msg(f"\n|w{district}|n ({district_total} total):")

            if groups["commodity"]:
                self.msg("  |wCommodity:|n")
                for name, count in sorted(groups["commodity"].items()):
                    self.msg(f"    {name}: {count}")

            if groups["boss"]:
                self.msg("  |wBoss:|n")
                for name, count in sorted(groups["boss"].items()):
                    self.msg(f"    {name}: {count}")

        self.msg(f"\n|wTotal spawned:|n {grand_total}")
