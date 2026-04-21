"""
ZoneSpawnScript — persistent zone-level mob population manager.

Reads a JSON file of spawn rules and maintains target mob populations
for static zones. Each rule defines a mob type, area tag, target count,
and respawn timing. The script ticks every 15 seconds and spawns
replacements when population drops below target.

One script instance per zone. Common mobs are deleted on death —
the script handles all respawning via fresh object creation.

Usage (from world builder):
    ZoneSpawnScript.create_for_zone("millholm_farms")
"""

import json
import os
import random
import time

from evennia import ObjectDB
from evennia.scripts.scripts import DefaultScript
from evennia.utils import create, logger


class ZoneSpawnScript(DefaultScript):
    """
    Repeating script that audits mob populations and spawns replacements.

    Attributes:
        db.zone_key (str): Zone identifier (matches JSON filename).
        db.spawn_table (list[dict]): Parsed spawn rules from JSON.
        db.last_spawn_times (dict): Rule ID → timestamp of last spawn.
    """

    def at_script_creation(self):
        self.key = f"zone_spawn_{self.db.zone_key or 'unknown'}"
        self.desc = f"Mob spawn controller for {self.db.zone_key}"
        self.interval = 15
        self.persistent = True
        self.start_delay = True

        if not self.db.last_spawn_times:
            self.db.last_spawn_times = {}

    # ================================================================== #
    #  Tick — audit and spawn
    # ================================================================== #

    def at_repeat(self):
        """Iterate over spawn rules and spawn replacements as needed."""
        spawn_table = self.db.spawn_table
        if not spawn_table:
            return

        for rule in spawn_table:
            self._check_rule(rule)

    def _check_rule(self, rule):
        """Check one spawn rule and spawn a mob if needed."""
        rule_id = self._rule_id(rule)
        target = rule.get("target", 0)
        if target <= 0:
            return

        # Count living mobs for this rule
        living = self._count_living(rule)
        if living >= target:
            return

        # Check respawn cooldown
        respawn_seconds = rule.get("respawn_seconds", 60)
        last_spawn = self.db.last_spawn_times.get(rule_id, 0)
        now = time.time()
        if now - last_spawn < respawn_seconds:
            return

        # Find a valid room to spawn in
        room = self._pick_spawn_room(rule)
        if not room:
            return

        # Spawn the mob
        self._spawn_mob(rule, room)
        last_spawn_times = dict(self.db.last_spawn_times)
        last_spawn_times[rule_id] = now
        self.db.last_spawn_times = last_spawn_times

    # ================================================================== #
    #  Population counting
    # ================================================================== #

    def _count_living(self, rule):
        """Count living mobs matching a spawn rule (typeclass + area_tag)."""
        return ObjectDB.objects.filter(
            db_typeclass_path=rule["typeclass"],
            db_tags__db_key=self.db.zone_key,
            db_tags__db_category="spawn_zone",
        ).filter(
            db_tags__db_key=rule["area_tag"],
            db_tags__db_category="mob_area",
        ).exclude(
            db_location__isnull=True,
        ).count()

    # ================================================================== #
    #  Room selection
    # ================================================================== #

    def _pick_spawn_room(self, rule):
        """Pick a random room from the area_tag pool, respecting max_per_room."""
        area_tag = rule["area_tag"]
        max_per_room = rule.get("max_per_room", 0)
        typeclass = rule["typeclass"]

        rooms = list(
            ObjectDB.objects.filter(
                db_tags__db_key=area_tag,
                db_tags__db_category="mob_area",
                db_typeclass_path__contains="rooms.",
            )
        )
        if not rooms:
            return None

        random.shuffle(rooms)

        if not max_per_room:
            return rooms[0]

        # Filter rooms that aren't full
        for room in rooms:
            mob_count = ObjectDB.objects.filter(
                db_typeclass_path=typeclass,
                db_location=room,
                db_tags__db_key=area_tag,
                db_tags__db_category="mob_area",
            ).count()
            if mob_count < max_per_room:
                return room

        return None  # all rooms full

    # ================================================================== #
    #  Spawning
    # ================================================================== #

    def _spawn_mob(self, rule, room):
        """Create a single mob from a spawn rule."""
        mob = create.create_object(
            rule["typeclass"],
            key=rule["key"],
            location=room,
        )

        # Set area tag (used by AI for wander containment + population counting)
        mob.tags.add(rule["area_tag"], category="mob_area")

        # Set description
        if rule.get("desc"):
            mob.db.desc = rule["desc"]

        # Set extra attributes
        for attr_name, attr_val in rule.get("attrs", {}).items():
            setattr(mob, attr_name, attr_val)

        # Sync spawn tags — attrs may have overridden the typeclass default
        # loot_resources, loot_gold_max, or scroll/recipe slots, so re-check
        # and ensure spawn tags are current.
        loot_res = getattr(mob, "loot_resources", None) or {}
        if loot_res:
            if not mob.tags.get("spawn_resources", category="spawn_resources"):
                mob.tags.add("spawn_resources", category="spawn_resources")
            mob.db.spawn_resources_max = dict(loot_res)

        gold_max = getattr(mob, "loot_gold_max", 0) or 0
        if gold_max > 0:
            if not mob.tags.get("spawn_gold", category="spawn_gold"):
                mob.tags.add("spawn_gold", category="spawn_gold")
            mob.db.spawn_gold_max = gold_max

        scrolls_max = getattr(mob, "spawn_scrolls_max", None) or {}
        if scrolls_max:
            if not mob.tags.get("spawn_scrolls", category="spawn_scrolls"):
                mob.tags.add("spawn_scrolls", category="spawn_scrolls")
            mob.db.spawn_scrolls_max = dict(scrolls_max)

        recipes_max = getattr(mob, "spawn_recipes_max", None) or {}
        if recipes_max:
            if not mob.tags.get("spawn_recipes", category="spawn_recipes"):
                mob.tags.add("spawn_recipes", category="spawn_recipes")
            mob.db.spawn_recipes_max = dict(recipes_max)

        # Tag for population tracking
        mob.tags.add(self.db.zone_key, category="spawn_zone")

        # Start AI
        if hasattr(mob, "start_ai"):
            mob.start_ai()

    # ================================================================== #
    #  Helpers
    # ================================================================== #

    @staticmethod
    def _rule_id(rule):
        """Derive a unique ID for a spawn rule."""
        return f"{rule['typeclass']}:{rule['area_tag']}"

    def populate(self):
        """
        Initial population — spawn all mobs up to target immediately,
        bypassing respawn cooldowns.

        Stamps last_spawn_times so operator tooling (e.g. `services`) can
        tell a freshly-seeded zone from a genuinely stalled one. A rule is
        stamped if it is at target (either already satisfied or brought to
        target by this call). The only case left unstamped is
        `needed > 0 and placed == 0` — the script tried to spawn but no
        matching room exists, which is the exact failure mode the STALLED
        flag is meant to surface.
        """
        spawn_table = self.db.spawn_table
        if not spawn_table:
            return

        now = time.time()
        last_spawn_times = dict(self.db.last_spawn_times or {})

        for rule in spawn_table:
            target = rule.get("target", 0)
            living = self._count_living(rule)
            needed = target - living
            placed = 0

            for _ in range(needed):
                room = self._pick_spawn_room(rule)
                if not room:
                    break
                self._spawn_mob(rule, room)
                placed += 1

            # Stamp unless we tried to spawn and failed (genuinely stalled)
            if not (needed > 0 and placed == 0):
                last_spawn_times[self._rule_id(rule)] = now

        self.db.last_spawn_times = last_spawn_times

    # ================================================================== #
    #  Factory
    # ================================================================== #

    @classmethod
    def create_for_zone(cls, zone_key):
        """
        Create (or retrieve) a ZoneSpawnScript for the given zone.

        Reads spawn rules from world/spawns/<zone_key>.json.
        If the script already exists, reloads the JSON config.

        Args:
            zone_key (str): Zone identifier matching a JSON filename.

        Returns:
            ZoneSpawnScript: The created or updated script.
        """
        # Load JSON
        json_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "world", "spawns", f"{zone_key}.json",
        )
        json_path = os.path.normpath(json_path)

        try:
            with open(json_path, "r") as f:
                spawn_table = json.load(f)
        except FileNotFoundError:
            logger.log_err(f"ZoneSpawnScript: {json_path} not found.")
            return None
        except json.JSONDecodeError as e:
            logger.log_err(f"ZoneSpawnScript: Invalid JSON in {json_path}: {e}")
            return None

        # Check for existing script
        script_key = f"zone_spawn_{zone_key}"
        existing = cls.objects.filter(db_key=script_key).first()

        if existing:
            # Update config (allows hot-reloading JSON)
            existing.db.spawn_table = spawn_table
            logger.log_info(f"ZoneSpawnScript: Reloaded {zone_key} ({len(spawn_table)} rules)")
            return existing

        # Create new script
        script = create.create_script(
            cls,
            key=script_key,
            autostart=False,
        )
        script.db.zone_key = zone_key
        script.db.spawn_table = spawn_table
        script.db.last_spawn_times = {}
        script.start()

        logger.log_info(f"ZoneSpawnScript: Created {zone_key} ({len(spawn_table)} rules)")

        # Initial population
        script.populate()

        return script
