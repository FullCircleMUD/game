"""Tests for Phase 2 — unified spawn tags, attributes, and script registration.

evennia test --settings settings tests.spawn_tests.test_phase2_integration
"""

from unittest.mock import patch, MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestRoomHarvestingSpawnTags(EvenniaTest):
    """RoomHarvesting gets spawn_resources tag and spawn_resources_max on creation."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room = create.create_object(
            "typeclasses.terrain.rooms.room_harvesting.RoomHarvesting",
            key="Iron Mine",
        )

    def test_has_spawn_resources_tag(self):
        """RoomHarvesting should have spawn_resources tag."""
        tags = self.room.tags.get(category="spawn_resources", return_list=True)
        self.assertIn("spawn_resources", tags)

    def test_spawn_resources_max_set(self):
        """spawn_resources_max should map resource_id → capacity."""
        max_dict = self.room.db.spawn_resources_max
        self.assertIsNotNone(max_dict)
        # Default resource_id=1, default capacity=20
        self.assertEqual(max_dict, {1: 20})

    def test_spawn_resources_max_custom_values(self):
        """Custom spawn_resources_max can be set directly (e.g. by zone builder)."""
        room = create.create_object(
            "typeclasses.terrain.rooms.room_harvesting.RoomHarvesting",
            key="Silver Mine",
        )
        # Override spawn_resources_max directly (as zone builders will do)
        room.db.spawn_resources_max = {30: 10}
        self.assertEqual(room.db.spawn_resources_max, {30: 10})


class TestCombatMobSpawnTags(EvenniaTest):
    """CombatMob gets spawn_resources tag when it has loot_resources."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Forest",
        )

    def test_wolf_has_spawn_resources_tag(self):
        """Wolf (loot_resources={8:1}) should have spawn_resources tag."""
        wolf = create.create_object(
            "typeclasses.actors.mobs.wolf.Wolf",
            key="a grey wolf",
            location=self.room,
        )
        tags = wolf.tags.get(category="spawn_resources", return_list=True)
        self.assertIn("spawn_resources", tags)

    def test_wolf_spawn_resources_max(self):
        """Wolf's spawn_resources_max should match loot_resources."""
        wolf = create.create_object(
            "typeclasses.actors.mobs.wolf.Wolf",
            key="a grey wolf",
            location=self.room,
        )
        max_dict = wolf.db.spawn_resources_max
        self.assertIsNotNone(max_dict)
        self.assertEqual(max_dict, {8: 1})

    def test_mob_without_loot_no_tag(self):
        """CombatMob with empty loot_resources should NOT get spawn_resources tag."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a ghost",
            location=self.room,
        )
        tags = mob.tags.get(category="spawn_resources", return_list=True)
        self.assertNotIn("spawn_resources", tags)

    def test_mob_without_loot_no_max_attr(self):
        """CombatMob with empty loot_resources should NOT have spawn_resources_max."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a ghost",
            location=self.room,
        )
        self.assertIsNone(mob.db.spawn_resources_max)


class TestUnifiedSpawnScript(EvenniaTest):
    """UnifiedSpawnScript creates and registers SpawnService singleton."""

    def create_script(self):
        pass

    def test_script_registers_service(self):
        """at_start() should set the module-level singleton."""
        from blockchain.xrpl.services.spawn.service import get_spawn_service, set_spawn_service

        # Clear any existing singleton
        set_spawn_service(None)

        script = create.create_script(
            "typeclasses.scripts.unified_spawn_service.UnifiedSpawnScript",
            key="unified_spawn_service",
        )
        # at_start is called by create_script; check singleton
        service = get_spawn_service()
        self.assertIsNotNone(service)

        # Cleanup
        script.delete()
        set_spawn_service(None)

    def test_script_properties(self):
        """Script should have correct interval and persistence settings."""
        from typeclasses.scripts.unified_spawn_service import TICK_INTERVAL_SECONDS

        script = create.create_script(
            "typeclasses.scripts.unified_spawn_service.UnifiedSpawnScript",
            key="unified_spawn_service",
        )
        self.assertEqual(script.interval, TICK_INTERVAL_SECONDS)
        self.assertTrue(script.persistent)

        # Cleanup
        script.delete()

    @patch("typeclasses.scripts.unified_spawn_service.datetime")
    @patch("typeclasses.scripts.unified_spawn_service.threads.deferToThread")
    def test_at_repeat_fires_on_slot_minute(self, mock_defer, mock_datetime):
        """at_repeat() should defer run_hourly_cycle() when the slot minute hits."""
        from datetime import datetime as real_datetime, timezone
        from typeclasses.scripts.unified_spawn_service import SLOT_MINUTE

        # Freeze time at HH:SLOT — the script should fire.
        mock_datetime.now.return_value = real_datetime(
            2026, 4, 21, 14, SLOT_MINUTE, 0, tzinfo=timezone.utc
        )

        script = create.create_script(
            "typeclasses.scripts.unified_spawn_service.UnifiedSpawnScript",
            key="unified_spawn_service",
        )
        script.at_repeat()
        mock_defer.assert_called_once_with(script._service.run_hourly_cycle)

        # Cleanup
        script.delete()

    @patch("typeclasses.scripts.unified_spawn_service.datetime")
    @patch("typeclasses.scripts.unified_spawn_service.threads.deferToThread")
    def test_at_repeat_skips_outside_slot_minute(self, mock_defer, mock_datetime):
        """at_repeat() should no-op when the current minute is not the slot minute."""
        from datetime import datetime as real_datetime, timezone
        from typeclasses.scripts.unified_spawn_service import SLOT_MINUTE

        # Freeze time one minute off from the slot — must not fire.
        off_minute = (SLOT_MINUTE + 1) % 60
        mock_datetime.now.return_value = real_datetime(
            2026, 4, 21, 14, off_minute, 0, tzinfo=timezone.utc
        )

        script = create.create_script(
            "typeclasses.scripts.unified_spawn_service.UnifiedSpawnScript",
            key="unified_spawn_service",
        )
        script.at_repeat()
        mock_defer.assert_not_called()

        # Cleanup
        script.delete()

    @patch("typeclasses.scripts.unified_spawn_service.datetime")
    @patch("typeclasses.scripts.unified_spawn_service.threads.deferToThread")
    def test_at_repeat_double_fire_guard(self, mock_defer, mock_datetime):
        """Second at_repeat() within the same hour must not double-fire."""
        from datetime import datetime as real_datetime, timezone
        from typeclasses.scripts.unified_spawn_service import SLOT_MINUTE

        mock_datetime.now.return_value = real_datetime(
            2026, 4, 21, 14, SLOT_MINUTE, 0, tzinfo=timezone.utc
        )

        script = create.create_script(
            "typeclasses.scripts.unified_spawn_service.UnifiedSpawnScript",
            key="unified_spawn_service",
        )
        script.at_repeat()
        script.at_repeat()  # same hour, same slot — should be skipped
        self.assertEqual(mock_defer.call_count, 1)

        # Cleanup
        script.delete()
