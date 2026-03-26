"""
Tests for the ResourceSpawnService.

Covers:
    - price_modifier() curve
    - supply_modifier() curve
    - get_player_hours_7d() session query
    - get_avg_consumption_24h() snapshot query
    - calculate_room_allocations() weighted allocation
    - distribute_to_rooms() immediate distribution (convenience)
    - schedule_drip_feed() delayed distribution
    - calculate_and_apply() integration
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.utils import timezone
from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.services.resource_spawn import (
    ResourceSpawnService,
    _apply_drip,
    _apply_mob_drip,
    MAX_TICKS_PER_HOUR,
)


# Reusable config for tests
_TEST_CONFIG = {
    "target_price_low": 8,
    "target_price_high": 16,
    "target_supply_per_ph": 5.0,
    "default_spawn_rate": 10,
    "max_per_room": 20,
    "modifier_min": 0.25,
    "modifier_max": 2.0,
}


class TestPriceModifier(EvenniaTest):

    def create_script(self):
        pass

    def test_no_amm_returns_neutral(self):
        """No AMM pool (None price) → 1.0."""
        self.assertEqual(
            ResourceSpawnService.price_modifier(None, _TEST_CONFIG), 1.0,
        )

    def test_price_at_midpoint_returns_one(self):
        """Price at exact midpoint of band → 1.0."""
        midpoint = (_TEST_CONFIG["target_price_low"] + _TEST_CONFIG["target_price_high"]) / 2
        result = ResourceSpawnService.price_modifier(Decimal(str(midpoint)), _TEST_CONFIG)
        self.assertAlmostEqual(result, 1.0, places=5)

    def test_price_at_low_returns_min(self):
        """Price at or below low band → modifier_min."""
        result = ResourceSpawnService.price_modifier(
            Decimal("8"), _TEST_CONFIG,
        )
        self.assertAlmostEqual(result, _TEST_CONFIG["modifier_min"], places=5)

    def test_price_below_low_returns_min(self):
        """Price well below low band → clamped to modifier_min."""
        result = ResourceSpawnService.price_modifier(
            Decimal("1"), _TEST_CONFIG,
        )
        self.assertAlmostEqual(result, _TEST_CONFIG["modifier_min"], places=5)

    def test_price_at_high_returns_max(self):
        """Price at or above high band → modifier_max."""
        result = ResourceSpawnService.price_modifier(
            Decimal("16"), _TEST_CONFIG,
        )
        self.assertAlmostEqual(result, _TEST_CONFIG["modifier_max"], places=5)

    def test_price_above_high_returns_max(self):
        """Price well above high band → clamped to modifier_max."""
        result = ResourceSpawnService.price_modifier(
            Decimal("100"), _TEST_CONFIG,
        )
        self.assertAlmostEqual(result, _TEST_CONFIG["modifier_max"], places=5)

    def test_price_between_low_and_mid_interpolates(self):
        """Price between low and midpoint → between modifier_min and 1.0."""
        # low=8, mid=12, so 10 is halfway in lower segment
        result = ResourceSpawnService.price_modifier(
            Decimal("10"), _TEST_CONFIG,
        )
        self.assertGreater(result, _TEST_CONFIG["modifier_min"])
        self.assertLess(result, 1.0)

    def test_price_between_mid_and_high_interpolates(self):
        """Price between midpoint and high → between 1.0 and modifier_max."""
        # mid=12, high=16, so 14 is halfway in upper segment
        result = ResourceSpawnService.price_modifier(
            Decimal("14"), _TEST_CONFIG,
        )
        self.assertGreater(result, 1.0)
        self.assertLess(result, _TEST_CONFIG["modifier_max"])


class TestSupplyModifier(EvenniaTest):

    def create_script(self):
        pass

    def test_zero_player_hours_returns_neutral(self):
        """Can't compute per-PH supply with 0 hours → 1.0."""
        result = ResourceSpawnService.supply_modifier(
            Decimal("100"), 0, _TEST_CONFIG,
        )
        self.assertEqual(result, 1.0)

    def test_supply_on_target_returns_one(self):
        """Supply per PH exactly on target → 1.0."""
        # target_supply_per_ph=5, so 50 circulating / 10 hours = 5 per PH
        result = ResourceSpawnService.supply_modifier(
            Decimal("50"), 10.0, _TEST_CONFIG,
        )
        self.assertAlmostEqual(result, 1.0, places=5)

    def test_undersupply_boosts(self):
        """Supply per PH below target → modifier > 1.0."""
        # target=5, actual=2.5 per PH (ratio=0.5) → boost
        result = ResourceSpawnService.supply_modifier(
            Decimal("25"), 10.0, _TEST_CONFIG,
        )
        self.assertGreater(result, 1.0)

    def test_oversupply_cuts(self):
        """Supply per PH above target → modifier < 1.0."""
        # target=5, actual=7.5 per PH (ratio=1.5) → cut
        result = ResourceSpawnService.supply_modifier(
            Decimal("75"), 10.0, _TEST_CONFIG,
        )
        self.assertLess(result, 1.0)

    def test_extreme_oversupply_returns_min(self):
        """Supply per PH at 2× target or more → modifier_min."""
        # target=5, actual=10 per PH (ratio=2.0) → min
        result = ResourceSpawnService.supply_modifier(
            Decimal("100"), 10.0, _TEST_CONFIG,
        )
        self.assertAlmostEqual(result, _TEST_CONFIG["modifier_min"], places=5)

    def test_zero_supply_returns_max(self):
        """No circulating supply → modifier_max."""
        result = ResourceSpawnService.supply_modifier(
            Decimal("0"), 10.0, _TEST_CONFIG,
        )
        self.assertAlmostEqual(result, _TEST_CONFIG["modifier_max"], places=5)

    def test_zero_target_returns_neutral(self):
        """Zero target_supply_per_ph → 1.0 (avoid div-by-zero)."""
        config = {**_TEST_CONFIG, "target_supply_per_ph": 0}
        result = ResourceSpawnService.supply_modifier(
            Decimal("50"), 10.0, config,
        )
        self.assertEqual(result, 1.0)


class TestGetPlayerHours7d(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_no_sessions_returns_zero(self):
        """No sessions in past 7 days → 0."""
        result = ResourceSpawnService.get_player_hours_7d()
        self.assertEqual(result, 0.0)

    def test_single_closed_session(self):
        """One 2-hour session → 2.0."""
        from blockchain.xrpl.models import PlayerSession

        now = timezone.now()
        PlayerSession.objects.create(
            account_id=1,
            character_key="tester",
            started_at=now - timedelta(hours=2),
            ended_at=now,
        )
        result = ResourceSpawnService.get_player_hours_7d()
        self.assertAlmostEqual(result, 2.0, places=1)

    def test_open_session_uses_now(self):
        """Open session (no ended_at) uses now() as end."""
        from blockchain.xrpl.models import PlayerSession

        now = timezone.now()
        PlayerSession.objects.create(
            account_id=1,
            character_key="tester",
            started_at=now - timedelta(hours=3),
            ended_at=None,
        )
        result = ResourceSpawnService.get_player_hours_7d()
        self.assertAlmostEqual(result, 3.0, places=1)

    def test_old_sessions_excluded(self):
        """Sessions older than 7 days are not counted."""
        from blockchain.xrpl.models import PlayerSession

        now = timezone.now()
        PlayerSession.objects.create(
            account_id=1,
            character_key="tester",
            started_at=now - timedelta(days=10),
            ended_at=now - timedelta(days=9),
        )
        result = ResourceSpawnService.get_player_hours_7d()
        self.assertEqual(result, 0.0)

    def test_multiple_sessions_sum(self):
        """Multiple sessions add up correctly."""
        from blockchain.xrpl.models import PlayerSession

        now = timezone.now()
        PlayerSession.objects.create(
            account_id=1,
            character_key="char_a",
            started_at=now - timedelta(hours=5),
            ended_at=now - timedelta(hours=3),
        )
        PlayerSession.objects.create(
            account_id=2,
            character_key="char_b",
            started_at=now - timedelta(hours=4),
            ended_at=now - timedelta(hours=1),
        )
        # 2 + 3 = 5 hours
        result = ResourceSpawnService.get_player_hours_7d()
        self.assertAlmostEqual(result, 5.0, places=1)


class TestGetAvgConsumption24h(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_no_snapshots_returns_zero(self):
        """No snapshots → 0."""
        result = ResourceSpawnService.get_avg_consumption_24h("FCMWheat")
        self.assertEqual(result, Decimal(0))

    def test_single_snapshot(self):
        """One snapshot → that value."""
        from blockchain.xrpl.models import ResourceSnapshot

        ResourceSnapshot.objects.create(
            hour=timezone.now().replace(minute=0, second=0, microsecond=0),
            currency_code="FCMWheat",
            consumed_1h=Decimal("20"),
        )
        result = ResourceSpawnService.get_avg_consumption_24h("FCMWheat")
        self.assertEqual(result, Decimal("20"))

    def test_multiple_snapshots_averaged(self):
        """Multiple snapshots → average."""
        from blockchain.xrpl.models import ResourceSnapshot

        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        for i in range(4):
            ResourceSnapshot.objects.create(
                hour=now - timedelta(hours=i),
                currency_code="FCMWheat",
                consumed_1h=Decimal("10") * (i + 1),  # 10, 20, 30, 40
            )
        result = ResourceSpawnService.get_avg_consumption_24h("FCMWheat")
        self.assertEqual(result, Decimal("25"))  # (10+20+30+40)/4


class TestDistributeToRooms(EvenniaTest):

    def create_script(self):
        pass

    def _make_room(self, resource_id, weight=1, count=0, max_count=20):
        """Create a RoomHarvesting room for testing."""
        from evennia.utils.create import create_object

        room = create_object(
            "typeclasses.terrain.rooms.room_harvesting.RoomHarvesting",
            key=f"test_room_{resource_id}_{weight}",
        )
        room.resource_id = resource_id
        room.spawn_rate_weight = weight
        room.resource_count = count
        room.max_resource_count = max_count
        return room

    def test_even_distribution_equal_weights(self):
        """Equal weights → equal distribution."""
        r1 = self._make_room(1, weight=1)
        r2 = self._make_room(1, weight=1)

        total = ResourceSpawnService.distribute_to_rooms(1, 10, 20)

        self.assertEqual(total, 10)
        self.assertEqual(r1.resource_count, 5)
        self.assertEqual(r2.resource_count, 5)

    def test_weighted_distribution(self):
        """Higher weight → more resources."""
        r1 = self._make_room(1, weight=3)
        r2 = self._make_room(1, weight=1)

        total = ResourceSpawnService.distribute_to_rooms(1, 8, 20)

        self.assertEqual(total, 8)
        # weight 3 gets 6 (3/4 × 8), weight 1 gets 2 (1/4 × 8)
        self.assertEqual(r1.resource_count, 6)
        self.assertEqual(r2.resource_count, 2)

    def test_capped_at_max(self):
        """Rooms already at max get nothing."""
        r1 = self._make_room(1, weight=1, count=20, max_count=20)
        r2 = self._make_room(1, weight=1, count=0, max_count=20)

        total = ResourceSpawnService.distribute_to_rooms(1, 10, 20)

        self.assertEqual(r1.resource_count, 20)  # unchanged
        self.assertEqual(r2.resource_count, 10)  # gets everything

    def test_partial_cap(self):
        """Room near max gets only what fits."""
        r1 = self._make_room(1, weight=1, count=18, max_count=20)
        r2 = self._make_room(1, weight=1, count=0, max_count=20)

        total = ResourceSpawnService.distribute_to_rooms(1, 10, 20)

        self.assertLessEqual(r1.resource_count, 20)
        self.assertEqual(total, 10)

    def test_no_rooms_returns_zero(self):
        """No rooms for resource → 0 distributed."""
        total = ResourceSpawnService.distribute_to_rooms(999, 100, 20)
        self.assertEqual(total, 0)

    def test_remainder_goes_to_highest_weight(self):
        """Remainder distributed to highest-weight rooms first."""
        r1 = self._make_room(1, weight=5)
        r2 = self._make_room(1, weight=1)

        # 7 / total_weight(6) = 1.166... per weight
        # r1 floor: 5 * 1.166 = floor(5.83) = 5
        # r2 floor: 1 * 1.166 = floor(1.16) = 1
        # allocated = 6, remainder = 1 → goes to r1 (highest weight)
        total = ResourceSpawnService.distribute_to_rooms(1, 7, 20)

        self.assertEqual(total, 7)
        self.assertEqual(r1.resource_count, 6)  # 5 + 1 remainder
        self.assertEqual(r2.resource_count, 1)

    def test_only_affects_matching_resource(self):
        """Rooms for other resources are untouched."""
        r_wheat = self._make_room(1, weight=1)
        r_wood = self._make_room(6, weight=1)

        ResourceSpawnService.distribute_to_rooms(1, 10, 20)

        self.assertEqual(r_wheat.resource_count, 10)
        self.assertEqual(r_wood.resource_count, 0)


class TestCalculateRoomAllocations(EvenniaTest):

    def create_script(self):
        pass

    def _make_mock_room(self, weight=1, count=0, max_count=20):
        room = MagicMock()
        room.resource_count = count
        room.max_resource_count = max_count
        room.spawn_rate_weight = weight
        return room

    def test_equal_weights(self):
        """Equal weights → equal allocation."""
        r1 = self._make_mock_room(weight=1)
        r2 = self._make_mock_room(weight=1)

        allocs = ResourceSpawnService.calculate_room_allocations(
            [r1, r2], 10, 20,
        )
        by_room = {room: amt for room, amt in allocs}
        self.assertEqual(by_room[r1], 5)
        self.assertEqual(by_room[r2], 5)

    def test_weighted(self):
        """Higher weight → proportionally more."""
        r1 = self._make_mock_room(weight=3)
        r2 = self._make_mock_room(weight=1)

        allocs = ResourceSpawnService.calculate_room_allocations(
            [r1, r2], 8, 20,
        )
        by_room = {room: amt for room, amt in allocs}
        self.assertEqual(by_room[r1], 6)
        self.assertEqual(by_room[r2], 2)

    def test_capped_at_max(self):
        """Room at max excluded from allocation."""
        r1 = self._make_mock_room(weight=1, count=20, max_count=20)
        r2 = self._make_mock_room(weight=1)

        allocs = ResourceSpawnService.calculate_room_allocations(
            [r1, r2], 10, 20,
        )
        rooms_in_alloc = {room for room, _ in allocs}
        self.assertNotIn(r1, rooms_in_alloc)
        self.assertEqual(allocs[0][1], 10)

    def test_partial_cap(self):
        """Room near max gets only what fits, rest redistributed."""
        r1 = self._make_mock_room(weight=1, count=18, max_count=20)
        r2 = self._make_mock_room(weight=1)

        allocs = ResourceSpawnService.calculate_room_allocations(
            [r1, r2], 10, 20,
        )
        total = sum(a for _, a in allocs)
        self.assertEqual(total, 10)
        by_room = {room: amt for room, amt in allocs}
        self.assertLessEqual(by_room.get(r1, 0) + 18, 20)

    def test_empty_rooms_list(self):
        """No rooms → empty allocations."""
        allocs = ResourceSpawnService.calculate_room_allocations([], 100, 20)
        self.assertEqual(allocs, [])

    def test_remainder_to_highest_weight(self):
        """Remainder goes to highest-weight room first."""
        r1 = self._make_mock_room(weight=5)
        r2 = self._make_mock_room(weight=1)

        allocs = ResourceSpawnService.calculate_room_allocations(
            [r1, r2], 7, 20,
        )
        by_room = {room: amt for room, amt in allocs}
        self.assertEqual(by_room[r1], 6)
        self.assertEqual(by_room[r2], 1)


class TestScheduleDripFeed(EvenniaTest):

    def create_script(self):
        pass

    @patch("blockchain.xrpl.services.resource_spawn.delay")
    def test_single_unit_one_tick(self, mock_delay):
        """Room due 1 → single delay at 0 seconds."""
        room = MagicMock()
        ResourceSpawnService.schedule_drip_feed([(room, 1)])

        mock_delay.assert_called_once()
        delay_secs = mock_delay.call_args[0][0]
        self.assertAlmostEqual(delay_secs, 0.0)

    @patch("blockchain.xrpl.services.resource_spawn.delay")
    def test_four_units_four_ticks(self, mock_delay):
        """Room due 4 → 4 ticks, one every 15 min."""
        room = MagicMock()
        ResourceSpawnService.schedule_drip_feed([(room, 4)])

        self.assertEqual(mock_delay.call_count, 4)
        delays = [call[0][0] for call in mock_delay.call_args_list]
        self.assertAlmostEqual(delays[0], 0.0)
        self.assertAlmostEqual(delays[1], 900.0)   # 15 min
        self.assertAlmostEqual(delays[2], 1800.0)  # 30 min
        self.assertAlmostEqual(delays[3], 2700.0)  # 45 min

    @patch("blockchain.xrpl.services.resource_spawn.delay")
    def test_twelve_units_twelve_ticks(self, mock_delay):
        """Room due 12 → 12 ticks, one every 5 min."""
        room = MagicMock()
        ResourceSpawnService.schedule_drip_feed([(room, 12)])

        self.assertEqual(mock_delay.call_count, 12)
        delays = [call[0][0] for call in mock_delay.call_args_list]
        self.assertAlmostEqual(delays[1], 300.0)  # 5 min

    @patch("blockchain.xrpl.services.resource_spawn.delay")
    def test_thirty_units_capped_at_twelve_ticks(self, mock_delay):
        """Room due 30 → capped at 12 ticks, drops of 2-3."""
        room = MagicMock()
        ResourceSpawnService.schedule_drip_feed([(room, 30)])

        self.assertEqual(mock_delay.call_count, 12)
        # Verify total adds up to 30
        total = sum(call[0][3] for call in mock_delay.call_args_list)
        self.assertEqual(total, 30)

    @patch("blockchain.xrpl.services.resource_spawn.delay")
    def test_multiple_rooms_scheduled(self, mock_delay):
        """Multiple rooms each get their own delay schedule."""
        r1 = MagicMock()
        r2 = MagicMock()
        ResourceSpawnService.schedule_drip_feed([(r1, 2), (r2, 3)])

        # 2 ticks for r1 + 3 ticks for r2 = 5 total
        self.assertEqual(mock_delay.call_count, 5)


class TestApplyDrip(EvenniaTest):

    def create_script(self):
        pass

    def test_adds_resources(self):
        """Drip callback adds resources to room."""
        room = MagicMock()
        room.resource_count = 5
        room.max_resource_count = 20

        _apply_drip(room, 3)
        self.assertEqual(room.resource_count, 8)

    def test_capped_at_max(self):
        """Drip callback respects max_resource_count."""
        room = MagicMock()
        room.resource_count = 18
        room.max_resource_count = 20

        _apply_drip(room, 5)
        self.assertEqual(room.resource_count, 20)

    def test_already_full_no_change(self):
        """Room already at max → no change."""
        room = MagicMock()
        room.resource_count = 20
        room.max_resource_count = 20

        _apply_drip(room, 3)
        self.assertEqual(room.resource_count, 20)


class TestCalculateAndApply(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def _make_room(self, resource_id, weight=1, count=0, max_count=20):
        from evennia.utils.create import create_object

        room = create_object(
            "typeclasses.terrain.rooms.room_harvesting.RoomHarvesting",
            key=f"test_room_{resource_id}",
        )
        room.resource_id = resource_id
        room.spawn_rate_weight = weight
        room.resource_count = count
        room.max_resource_count = max_count
        return room

    def _create_economy_snapshot(self, players_online=5):
        from blockchain.xrpl.models import EconomySnapshot

        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        return EconomySnapshot.objects.create(
            hour=now,
            players_online=players_online,
        )

    def _create_player_session(self, hours_ago_start=5, hours_ago_end=3):
        from blockchain.xrpl.models import PlayerSession

        now = timezone.now()
        return PlayerSession.objects.create(
            account_id=1,
            character_key="tester",
            started_at=now - timedelta(hours=hours_ago_start),
            ended_at=now - timedelta(hours=hours_ago_end),
        )

    def test_no_currency_data_skips(self):
        """No CurrencyType data → nothing to spawn (no currency codes)."""
        room = self._make_room(1)

        ResourceSpawnService.calculate_and_apply()

        self.assertEqual(room.resource_count, 0)

    @patch("blockchain.xrpl.services.resource_spawn.delay")
    def test_cold_start_schedules_drip_feed(self, mock_delay):
        """No consumption data → uses default_spawn_rate, schedules drip."""
        from blockchain.xrpl.models import CurrencyType

        # Ensure CurrencyType exists for Wheat
        CurrencyType.objects.get_or_create(
            currency_code="FCMWheat",
            defaults={
                "resource_id": 1,
                "name": "Wheat",
                "unit": "bushels",
            },
        )

        self._create_economy_snapshot(players_online=5)
        self._create_player_session(hours_ago_start=5, hours_ago_end=3)
        self._make_room(1, weight=1, count=0, max_count=50)

        ResourceSpawnService.calculate_and_apply()

        # delay() should have been called to schedule drip-feed
        self.assertGreater(mock_delay.call_count, 0)
        # Verify total amount across all scheduled drips > 0
        total = sum(call[0][3] for call in mock_delay.call_args_list)
        self.assertGreater(total, 0)


# ================================================================== #
#  Mob Loot Spawn Tests
# ================================================================== #


class TestApplyMobDrip(EvenniaTest):
    """Tests for the _apply_mob_drip() callback."""

    def create_script(self):
        pass

    def _make_mock_mob(self, resource_id=8, current=0, max_amount=1,
                       alive=True, has_location=True):
        """Create a mock mob with loot_resources and FungibleInventoryMixin."""
        mob = MagicMock()
        mob.is_alive = alive
        mob.location = MagicMock() if has_location else None
        mob.loot_resources = {resource_id: max_amount}
        mob.get_resource = MagicMock(return_value=current)
        mob.receive_resource_from_reserve = MagicMock()
        return mob

    @patch.object(ResourceSpawnService, "_load_loot_mobs")
    def test_places_resource_on_eligible_mob(self, mock_load):
        """Single eligible mob gets 1 resource."""
        mob = self._make_mock_mob()
        mock_load.return_value = [mob]
        bank = [0]

        _apply_mob_drip(8, 1, bank, False)

        mob.receive_resource_from_reserve.assert_called_once_with(8, 1)
        self.assertEqual(bank[0], 0)

    @patch.object(ResourceSpawnService, "_load_loot_mobs")
    def test_skips_dead_mobs(self, mock_load):
        """Dead mobs are not eligible for loot."""
        dead_mob = self._make_mock_mob(alive=False)
        live_mob = self._make_mock_mob()
        mock_load.return_value = [dead_mob, live_mob]
        bank = [0]

        _apply_mob_drip(8, 1, bank, False)

        dead_mob.receive_resource_from_reserve.assert_not_called()
        live_mob.receive_resource_from_reserve.assert_called_once_with(8, 1)

    @patch.object(ResourceSpawnService, "_load_loot_mobs")
    def test_skips_full_mobs(self, mock_load):
        """Mobs already at their loot cap are skipped."""
        full_mob = self._make_mock_mob(current=1, max_amount=1)
        empty_mob = self._make_mock_mob(current=0, max_amount=1)
        mock_load.return_value = [full_mob, empty_mob]
        bank = [0]

        _apply_mob_drip(8, 1, bank, False)

        full_mob.receive_resource_from_reserve.assert_not_called()
        empty_mob.receive_resource_from_reserve.assert_called_once_with(8, 1)

    @patch.object(ResourceSpawnService, "_load_loot_mobs")
    def test_budget_exceeds_eligible_banks_surplus(self, mock_load):
        """When budget > eligible mobs, surplus is banked."""
        mob = self._make_mock_mob(current=0, max_amount=1)
        mock_load.return_value = [mob]
        bank = [0]

        _apply_mob_drip(8, 5, bank, False)

        mob.receive_resource_from_reserve.assert_called_once_with(8, 1)
        self.assertEqual(bank[0], 4)

    @patch.object(ResourceSpawnService, "_load_loot_mobs")
    def test_final_tick_drops_surplus(self, mock_load):
        """On final tick, surplus is dropped (not banked)."""
        mock_load.return_value = []  # no mobs
        bank = [3]

        _apply_mob_drip(8, 2, bank, True)

        self.assertEqual(bank[0], 0)

    @patch.object(ResourceSpawnService, "_load_loot_mobs")
    def test_no_mobs_banks_for_next_tick(self, mock_load):
        """No eligible mobs on non-final tick → bank budget."""
        mock_load.return_value = []
        bank = [0]

        _apply_mob_drip(8, 5, bank, False)

        self.assertEqual(bank[0], 5)

    @patch.object(ResourceSpawnService, "_load_loot_mobs")
    def test_bank_carries_forward(self, mock_load):
        """Banked surplus from previous tick is added to current budget."""
        mob = self._make_mock_mob(current=0, max_amount=1)
        mock_load.return_value = [mob]
        bank = [3]  # carried from previous tick

        _apply_mob_drip(8, 2, bank, False)

        # Total budget = 2 + 3 = 5, but only 1 mob with headroom 1
        mob.receive_resource_from_reserve.assert_called_once_with(8, 1)
        self.assertEqual(bank[0], 4)

    @patch.object(ResourceSpawnService, "_load_loot_mobs")
    def test_more_mobs_than_budget_random_selection(self, mock_load):
        """When more eligible mobs than budget, a random subset is chosen."""
        mobs = [self._make_mock_mob() for _ in range(5)]
        mock_load.return_value = mobs
        bank = [0]

        _apply_mob_drip(8, 2, bank, False)

        # Exactly 2 mobs should have received resources
        called = sum(
            1 for m in mobs
            if m.receive_resource_from_reserve.called
        )
        self.assertEqual(called, 2)
        self.assertEqual(bank[0], 0)

    @patch.object(ResourceSpawnService, "_load_loot_mobs")
    def test_zero_budget_is_noop(self, mock_load):
        """Zero budget with empty bank → no queries, no placement."""
        bank = [0]

        _apply_mob_drip(8, 0, bank, False)

        mock_load.assert_not_called()


class TestScheduleMobDripFeed(EvenniaTest):

    def create_script(self):
        pass

    @patch("blockchain.xrpl.services.resource_spawn.delay")
    def test_single_unit_one_tick(self, mock_delay):
        """1 unit → single tick at 0 seconds."""
        ResourceSpawnService.schedule_mob_drip_feed(8, 1)

        self.assertEqual(mock_delay.call_count, 1)
        args = mock_delay.call_args[0]
        self.assertAlmostEqual(args[0], 0.0)  # delay_seconds
        self.assertEqual(args[1], _apply_mob_drip)  # callback
        self.assertEqual(args[2], 8)   # resource_id
        self.assertEqual(args[3], 1)   # amount
        self.assertTrue(args[5])       # is_final (only tick)

    @patch("blockchain.xrpl.services.resource_spawn.delay")
    def test_four_units_four_ticks(self, mock_delay):
        """4 units → 4 ticks at 15 min intervals."""
        ResourceSpawnService.schedule_mob_drip_feed(8, 4)

        self.assertEqual(mock_delay.call_count, 4)
        delays = [call[0][0] for call in mock_delay.call_args_list]
        self.assertAlmostEqual(delays[0], 0.0)
        self.assertAlmostEqual(delays[1], 900.0)
        self.assertAlmostEqual(delays[2], 1800.0)
        self.assertAlmostEqual(delays[3], 2700.0)

    @patch("blockchain.xrpl.services.resource_spawn.delay")
    def test_capped_at_twelve_ticks(self, mock_delay):
        """30 units → capped at 12 ticks, total amounts sum correctly."""
        ResourceSpawnService.schedule_mob_drip_feed(8, 30)

        self.assertEqual(mock_delay.call_count, 12)
        total = sum(call[0][3] for call in mock_delay.call_args_list)
        self.assertEqual(total, 30)

    @patch("blockchain.xrpl.services.resource_spawn.delay")
    def test_bank_shared_across_ticks(self, mock_delay):
        """All ticks share the same bank list object."""
        ResourceSpawnService.schedule_mob_drip_feed(8, 3)

        banks = [call[0][4] for call in mock_delay.call_args_list]
        # All should be the same list object
        for b in banks:
            self.assertIs(b, banks[0])

    @patch("blockchain.xrpl.services.resource_spawn.delay")
    def test_final_flag_only_on_last_tick(self, mock_delay):
        """Only the last tick has is_final=True."""
        ResourceSpawnService.schedule_mob_drip_feed(8, 5)

        finals = [call[0][5] for call in mock_delay.call_args_list]
        self.assertEqual(finals, [False, False, False, False, True])


class TestProcessResourceBudgetSplit(EvenniaTest):
    """Tests that _process_resource() splits budget between rooms and mobs."""

    def create_script(self):
        pass

    @patch("blockchain.xrpl.services.resource_spawn.delay")
    @patch.object(ResourceSpawnService, "get_circulating_supply",
                  return_value=Decimal("0"))
    @patch.object(ResourceSpawnService, "get_latest_buy_price",
                  return_value=None)
    @patch.object(ResourceSpawnService, "get_avg_consumption_24h",
                  return_value=Decimal("0"))
    @patch("blockchain.xrpl.currency_cache.get_currency_code",
           return_value="FCMHide")
    def test_mob_share_1_sends_all_to_mobs(self, mock_cc, mock_cons,
                                            mock_price, mock_supply,
                                            mock_delay):
        """mob_share=1.0 → all budget goes to mob drip-feed, none to rooms."""
        mob_config = {8: {"mob_share": 1.0}}
        config = _TEST_CONFIG.copy()

        with patch(
            "world.economy.resource_spawn_config.MOB_RESOURCE_SPAWN_CONFIG",
            mob_config,
        ):
            result = ResourceSpawnService._process_resource(
                8, config, 10.0, [],
            )

        # Should have scheduled mob drip (delay called with _apply_mob_drip)
        mob_drip_calls = [
            c for c in mock_delay.call_args_list
            if c[0][1] is _apply_mob_drip
        ]
        self.assertGreater(len(mob_drip_calls), 0)

        # No room drip calls (no _apply_drip calls)
        room_drip_calls = [
            c for c in mock_delay.call_args_list
            if c[0][1] is _apply_drip
        ]
        self.assertEqual(len(room_drip_calls), 0)

    @patch("blockchain.xrpl.services.resource_spawn.delay")
    @patch.object(ResourceSpawnService, "get_circulating_supply",
                  return_value=Decimal("0"))
    @patch.object(ResourceSpawnService, "get_latest_buy_price",
                  return_value=None)
    @patch.object(ResourceSpawnService, "get_avg_consumption_24h",
                  return_value=Decimal("0"))
    @patch("blockchain.xrpl.currency_cache.get_currency_code",
           return_value="FCMWheat")
    def test_no_mob_config_sends_all_to_rooms(self, mock_cc, mock_cons,
                                               mock_price, mock_supply,
                                               mock_delay):
        """No MOB_RESOURCE_SPAWN_CONFIG entry → all to rooms (backward compat)."""
        room = MagicMock()
        room.resource_count = 0
        room.max_resource_count = 50
        room.spawn_rate_weight = 1

        with patch(
            "world.economy.resource_spawn_config.MOB_RESOURCE_SPAWN_CONFIG",
            {},
        ):
            result = ResourceSpawnService._process_resource(
                1, _TEST_CONFIG, 10.0, [room],
            )

        # Should have scheduled room drips only
        room_drip_calls = [
            c for c in mock_delay.call_args_list
            if len(c[0]) >= 3 and c[0][1] is _apply_drip
        ]
        self.assertGreater(len(room_drip_calls), 0)

        # No mob drip calls
        mob_drip_calls = [
            c for c in mock_delay.call_args_list
            if len(c[0]) >= 3 and c[0][1] is _apply_mob_drip
        ]
        self.assertEqual(len(mob_drip_calls), 0)
