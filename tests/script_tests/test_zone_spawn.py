"""
Tests for the ZoneSpawnScript mob population manager.

evennia test --settings settings tests.script_tests.test_zone_spawn
"""

import time
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from typeclasses.scripts.zone_spawn_script import ZoneSpawnScript


class TestZoneSpawnScript(EvenniaTest):
    """Test the zone spawn script population management."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # Create two rooms tagged as "test_area" mob_area
        self.room1 = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Test Room 1",
            nohome=True,
        )
        self.room1.tags.add("test_area", category="mob_area")

        self.room2 = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Test Room 2",
            nohome=True,
        )
        self.room2.tags.add("test_area", category="mob_area")

        # Standard spawn rule for tests
        self.rule = {
            "typeclass": "typeclasses.actors.mobs.rabbit.Rabbit",
            "key": "a rabbit",
            "area_tag": "test_area",
            "target": 3,
            "max_per_room": 2,
            "respawn_seconds": 30,
            "desc": "A test rabbit.",
        }

        # Create script manually (bypass JSON loading)
        self.script = create.create_script(
            ZoneSpawnScript,
            key="zone_spawn_test_zone",
            autostart=False,
        )
        self.script.db.zone_key = "test_zone"
        self.script.db.spawn_table = [self.rule]
        self.script.db.last_spawn_times = {}

    def tearDown(self):
        # Clean up mobs
        from evennia import ObjectDB
        for mob in ObjectDB.objects.filter(
            db_tags__db_key="test_zone",
            db_tags__db_category="spawn_zone",
        ):
            mob.delete()
        if self.script.pk:
            self.script.delete()
        super().tearDown()

    # ── Population counting ──────────────────────────────────────────

    def test_count_living_empty(self):
        """No mobs exist — count should be 0."""
        count = self.script._count_living(self.rule)
        self.assertEqual(count, 0)

    def test_count_living_after_spawn(self):
        """After spawning a mob, count should reflect it."""
        self.script._spawn_mob(self.rule, self.room1)
        count = self.script._count_living(self.rule)
        self.assertEqual(count, 1)

    # ── Spawning ─────────────────────────────────────────────────────

    def test_spawn_mob_creates_object(self):
        """_spawn_mob creates a mob in the target room."""
        self.script._spawn_mob(self.rule, self.room1)
        mobs = [
            obj for obj in self.room1.contents
            if obj.typeclass_path == self.rule["typeclass"]
        ]
        self.assertEqual(len(mobs), 1)
        self.assertEqual(mobs[0].key, "a rabbit")

    def test_spawn_mob_sets_area_tag(self):
        """Spawned mob gets the area_tag from the rule as a mob_area tag."""
        self.script._spawn_mob(self.rule, self.room1)
        mob = [
            obj for obj in self.room1.contents
            if obj.typeclass_path == self.rule["typeclass"]
        ][0]
        self.assertIn(
            "test_area",
            mob.tags.get(category="mob_area", return_list=True),
        )

    def test_spawn_mob_sets_desc(self):
        """Spawned mob gets the description from the rule."""
        self.script._spawn_mob(self.rule, self.room1)
        mob = [
            obj for obj in self.room1.contents
            if obj.typeclass_path == self.rule["typeclass"]
        ][0]
        self.assertEqual(mob.db.desc, "A test rabbit.")

    def test_spawn_mob_tagged_with_zone(self):
        """Spawned mob is tagged with the zone for population tracking."""
        self.script._spawn_mob(self.rule, self.room1)
        mob = [
            obj for obj in self.room1.contents
            if obj.typeclass_path == self.rule["typeclass"]
        ][0]
        self.assertIn(
            "test_zone",
            mob.tags.get(category="spawn_zone", return_list=True),
        )

    def test_spawn_mob_sets_extra_attrs(self):
        """Extra attrs from the rule are set on the mob."""
        rule = dict(self.rule, attrs={"den_room_tag": "wolves_den"})
        self.script._spawn_mob(rule, self.room1)
        mob = [
            obj for obj in self.room1.contents
            if obj.typeclass_path == rule["typeclass"]
        ][0]
        self.assertEqual(mob.den_room_tag, "wolves_den")

    # ── Populate (initial) ───────────────────────────────────────────

    def test_populate_spawns_to_target(self):
        """populate() spawns mobs up to the target count."""
        self.script.populate()
        count = self.script._count_living(self.rule)
        self.assertEqual(count, 3)

    def test_populate_respects_max_per_room(self):
        """populate() doesn't exceed max_per_room in any room."""
        self.script.populate()
        for room in [self.room1, self.room2]:
            room_mobs = [
                obj for obj in room.contents
                if obj.typeclass_path == self.rule["typeclass"]
            ]
            self.assertLessEqual(len(room_mobs), 2)

    def test_populate_idempotent(self):
        """Calling populate() twice doesn't double the mobs."""
        self.script.populate()
        self.script.populate()
        count = self.script._count_living(self.rule)
        self.assertEqual(count, 3)

    def test_populate_stamps_last_spawn_times(self):
        """populate() records a timestamp per rule it actually seeds.

        Operator tooling (e.g. the `services` command) uses last_spawn_times
        to tell a freshly-populated zone from a stalled one. Without this
        stamp, every just-reset zone would incorrectly look stalled.
        """
        before = time.time()
        self.script.populate()
        after = time.time()

        rule_id = self.script._rule_id(self.rule)
        self.assertIn(rule_id, self.script.db.last_spawn_times)
        self.assertGreaterEqual(self.script.db.last_spawn_times[rule_id], before)
        self.assertLessEqual(self.script.db.last_spawn_times[rule_id], after)

    def test_populate_skips_stamp_when_no_rooms(self):
        """Rules with no matching rooms remain unstamped — correctly stalled."""
        rule = dict(self.rule, area_tag="nonexistent_area")
        self.script.db.spawn_table = [rule]
        self.script.populate()
        self.assertEqual(self.script.db.last_spawn_times, {})

    # ── Room selection ───────────────────────────────────────────────

    def test_pick_spawn_room_returns_tagged_room(self):
        """_pick_spawn_room returns a room with the area_tag."""
        room = self.script._pick_spawn_room(self.rule)
        self.assertIn(room, [self.room1, self.room2])

    def test_pick_spawn_room_respects_max_per_room(self):
        """Room at max_per_room capacity is skipped."""
        # Fill room1 to capacity
        self.script._spawn_mob(self.rule, self.room1)
        self.script._spawn_mob(self.rule, self.room1)
        # Room1 is full (max_per_room=2), should pick room2
        room = self.script._pick_spawn_room(self.rule)
        self.assertEqual(room, self.room2)

    def test_pick_spawn_room_returns_none_when_all_full(self):
        """Returns None when all rooms are at max_per_room capacity."""
        # Fill both rooms
        self.script._spawn_mob(self.rule, self.room1)
        self.script._spawn_mob(self.rule, self.room1)
        self.script._spawn_mob(self.rule, self.room2)
        self.script._spawn_mob(self.rule, self.room2)
        room = self.script._pick_spawn_room(self.rule)
        self.assertIsNone(room)

    # ── Check rule (respawn cooldown) ────────────────────────────────

    def test_check_rule_spawns_when_below_target(self):
        """_check_rule spawns a mob when population is below target."""
        self.script._check_rule(self.rule)
        count = self.script._count_living(self.rule)
        self.assertEqual(count, 1)  # spawns one per tick

    def test_check_rule_skips_when_at_target(self):
        """_check_rule does nothing when population is at target."""
        self.script.populate()
        initial_count = self.script._count_living(self.rule)
        self.script._check_rule(self.rule)
        self.assertEqual(self.script._count_living(self.rule), initial_count)

    def test_check_rule_respects_cooldown(self):
        """_check_rule won't spawn if respawn_seconds hasn't elapsed."""
        # Spawn one — sets last_spawn_time
        self.script._check_rule(self.rule)
        self.assertEqual(self.script._count_living(self.rule), 1)

        # Immediately try again — should be blocked by cooldown
        self.script._check_rule(self.rule)
        self.assertEqual(self.script._count_living(self.rule), 1)

    @patch("typeclasses.scripts.zone_spawn_script.time")
    def test_check_rule_spawns_after_cooldown(self, mock_time):
        """_check_rule spawns after respawn_seconds has elapsed."""
        mock_time.time.return_value = 1000.0
        self.script._check_rule(self.rule)
        self.assertEqual(self.script._count_living(self.rule), 1)

        # Advance time past cooldown
        mock_time.time.return_value = 1031.0
        self.script._check_rule(self.rule)
        self.assertEqual(self.script._count_living(self.rule), 2)

    # ── at_repeat (full tick) ────────────────────────────────────────

    def test_at_repeat_processes_all_rules(self):
        """at_repeat processes every rule in the spawn table."""
        self.script.at_repeat()
        count = self.script._count_living(self.rule)
        self.assertGreaterEqual(count, 1)

    # ── Rule identity ────────────────────────────────────────────────

    def test_rule_id_unique_per_typeclass_area(self):
        """Rule ID is derived from typeclass + area_tag."""
        rule_id = self.script._rule_id(self.rule)
        self.assertIn("Rabbit", rule_id)
        self.assertIn("test_area", rule_id)

    def test_different_area_tags_different_ids(self):
        """Two rules with same typeclass but different area_tag get different IDs."""
        rule2 = dict(self.rule, area_tag="other_area")
        self.assertNotEqual(
            self.script._rule_id(self.rule),
            self.script._rule_id(rule2),
        )


class TestCombatMobDeath(EvenniaTest):
    """Test that common mob death deletes the object."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Test Room",
            nohome=True,
        )

    def test_common_mob_deleted_on_death(self):
        """Common mob (is_unique=False) is deleted on death."""
        mob = create.create_object(
            "typeclasses.actors.mobs.rabbit.Rabbit",
            key="a rabbit",
            location=self.room,
        )
        mob_id = mob.id
        mob.die(cause="test")

        from evennia import ObjectDB
        self.assertFalse(ObjectDB.objects.filter(id=mob_id).exists())

    def test_unique_mob_not_deleted_on_death(self):
        """Unique mob (is_unique=True) is NOT deleted — parks in limbo."""
        mob = create.create_object(
            "typeclasses.actors.mobs.rabbit.Rabbit",
            key="boss rabbit",
            location=self.room,
        )
        mob.is_unique = True
        mob_id = mob.id
        mob.die(cause="test")

        from evennia import ObjectDB
        self.assertTrue(ObjectDB.objects.filter(id=mob_id).exists())
        obj = ObjectDB.objects.get(id=mob_id)
        self.assertIsNone(obj.location)
