"""
Tests that each of the 11 global scripts actually calls
record_repeat()/record_work()/record_heartbeat() at the right point in
its own at_repeat() — the residual gap left after
test_heartbeat_script.py (which only tests the mixin in isolation).

Pattern: call the real ScriptClass.at_repeat(self) as an unbound method
against a MagicMock(spec=ScriptClass) standing in for self, with the
three heartbeat methods explicitly rebound to the REAL HeartbeatMixin
implementations (not auto-mocked) and a real SimpleNamespace for .ndb
so the timestamp writes are actually observable. Every other
attribute/method access on self is auto-mocked by the spec, and every
free function at_repeat() calls (SESSION_HANDLER, get_season(),
reallocate_sinks(), etc.) is patched at its own source module — the
same local-import patching convention used throughout this test
session. This mirrors the existing MagicMock(spec=...) + unbound-call
pattern already used in e.g. test_season_service.py, just adding real
heartbeat plumbing on top.

evennia test --settings settings tests.script_tests.test_heartbeat_call_sites
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from typeclasses.scripts.heartbeat_script import HeartbeatMixin


def _fake_self(script_cls, **ndb_attrs):
    """A MagicMock(spec=script_cls) with real heartbeat methods and a
    real (non-mock) .ndb namespace, so record_*() writes are observable."""
    service = MagicMock(spec=script_cls)
    service.ndb = SimpleNamespace(**ndb_attrs)
    service.record_repeat = lambda: HeartbeatMixin.record_repeat(service)
    service.record_work = lambda: HeartbeatMixin.record_work(service)
    service.record_heartbeat = lambda: HeartbeatMixin.record_heartbeat(service)
    return service


def _has_heartbeat(service):
    return hasattr(service.ndb, "last_repeat") and hasattr(service.ndb, "last_work")


# ══════════════════════════════════════════════════════════════════════════
#  "Every tick is real work" bucket — record_heartbeat() unconditionally
# ══════════════════════════════════════════════════════════════════════════

class TestRegenerationServiceHeartbeat(TestCase):

    @patch("typeclasses.scripts.regeneration_service.SESSION_HANDLER")
    def test_record_heartbeat_fires(self, mock_handler):
        from typeclasses.scripts.regeneration_service import RegenerationService

        mock_handler.get_sessions.return_value = []
        service = _fake_self(RegenerationService, tick_count=0)

        RegenerationService.at_repeat(service)

        self.assertTrue(_has_heartbeat(service))
        self.assertEqual(service.ndb.last_repeat, service.ndb.last_work)


class TestSurvivalServiceHeartbeat(TestCase):

    @patch("typeclasses.scripts.survival_service.SESSION_HANDLER")
    def test_record_heartbeat_fires(self, mock_handler):
        from typeclasses.scripts.survival_service import SurvivalService

        mock_handler.get_sessions.return_value = []
        service = _fake_self(SurvivalService)

        SurvivalService.at_repeat(service)

        self.assertTrue(_has_heartbeat(service))
        self.assertEqual(service.ndb.last_repeat, service.ndb.last_work)


class TestDayNightServiceHeartbeat(TestCase):

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_record_heartbeat_fires(self, mock_phase):
        from enums.time_of_day import TimeOfDay
        from typeclasses.scripts.day_night_service import DayNightService

        mock_phase.return_value = TimeOfDay.DAY
        service = _fake_self(DayNightService, last_phase=TimeOfDay.DAY)

        DayNightService.at_repeat(service)

        self.assertTrue(_has_heartbeat(service))
        self.assertEqual(service.ndb.last_repeat, service.ndb.last_work)


class TestSeasonServiceHeartbeat(TestCase):

    @patch("typeclasses.scripts.season_service.get_season")
    def test_record_heartbeat_fires(self, mock_season):
        from enums.season import Season
        from typeclasses.scripts.season_service import SeasonService

        mock_season.return_value = Season.SUMMER
        service = _fake_self(SeasonService, last_season=Season.SUMMER)

        SeasonService.at_repeat(service)

        self.assertTrue(_has_heartbeat(service))
        self.assertEqual(service.ndb.last_repeat, service.ndb.last_work)


class TestWeatherServiceHeartbeat(TestCase):

    def test_record_heartbeat_fires_on_empty_zones(self):
        """No connected players in any zone — the early-return branch,
        which still calls record_heartbeat() before returning."""
        from typeclasses.scripts.weather_service import WeatherService

        service = _fake_self(WeatherService)
        service._get_zone_characters.return_value = {}

        WeatherService.at_repeat(service)

        self.assertTrue(_has_heartbeat(service))
        self.assertEqual(service.ndb.last_repeat, service.ndb.last_work)


class TestReallocationServiceHeartbeat(TestCase):

    @patch("blockchain.xrpl.services.reallocation.reallocate_sinks")
    def test_record_heartbeat_fires(self, mock_reallocate):
        from typeclasses.scripts.reallocation_service import ReallocationServiceScript

        service = _fake_self(ReallocationServiceScript)

        ReallocationServiceScript.at_repeat(service)

        mock_reallocate.assert_called_once()
        self.assertTrue(_has_heartbeat(service))
        self.assertEqual(service.ndb.last_repeat, service.ndb.last_work)


class TestCosignerKeepAliveHeartbeat(TestCase):

    @patch("typeclasses.scripts.cosigner_keepalive_service.SESSIONS")
    def test_record_heartbeat_fires_on_no_sessions(self, mock_sessions):
        """No one connected — the early-return branch, which still
        calls record_heartbeat() before returning."""
        from typeclasses.scripts.cosigner_keepalive_service import CosignerKeepAliveScript

        mock_sessions.get_sessions.return_value = []
        service = _fake_self(CosignerKeepAliveScript)

        CosignerKeepAliveScript.at_repeat(service)

        self.assertTrue(_has_heartbeat(service))
        self.assertEqual(service.ndb.last_repeat, service.ndb.last_work)

    @patch("blockchain.xrpl.cosigner_ping.warm_cosigner")
    @patch("typeclasses.scripts.cosigner_keepalive_service.SESSIONS")
    def test_record_heartbeat_fires_when_sessions_connected(self, mock_sessions, mock_warm):
        from typeclasses.scripts.cosigner_keepalive_service import CosignerKeepAliveScript

        mock_sessions.get_sessions.return_value = [MagicMock()]
        service = _fake_self(CosignerKeepAliveScript)

        CosignerKeepAliveScript.at_repeat(service)

        mock_warm.assert_called_once()
        self.assertTrue(_has_heartbeat(service))
        self.assertEqual(service.ndb.last_repeat, service.ndb.last_work)


# ══════════════════════════════════════════════════════════════════════════
#  "Fast sub-sample of a slower cadence" bucket — record_repeat() always,
#  record_work() only when the wall-clock/day gate is open
# ══════════════════════════════════════════════════════════════════════════

class TestTelemetryAggregatorHeartbeat(TestCase):

    @patch("typeclasses.scripts.telemetry_service.defer_to_db_thread")
    @patch("typeclasses.scripts.telemetry_service.datetime")
    def test_off_slot_minute_records_repeat_only(self, mock_datetime, _mock_defer):
        import datetime as real_datetime
        from typeclasses.scripts.telemetry_service import TelemetryAggregatorScript

        mock_datetime.now.return_value = real_datetime.datetime(
            2026, 1, 1, 12, 30, tzinfo=real_datetime.timezone.utc,
        )
        service = _fake_self(TelemetryAggregatorScript)

        TelemetryAggregatorScript.at_repeat(service)

        self.assertTrue(hasattr(service.ndb, "last_repeat"))
        self.assertFalse(hasattr(service.ndb, "last_work"))

    @patch("typeclasses.scripts.telemetry_service.defer_to_db_thread")
    @patch("typeclasses.scripts.telemetry_service.datetime")
    def test_on_slot_minute_records_work_too(self, mock_datetime, mock_defer):
        import datetime as real_datetime
        from typeclasses.scripts.telemetry_service import TelemetryAggregatorScript

        mock_datetime.now.return_value = real_datetime.datetime(
            2026, 1, 1, 12, 0, tzinfo=real_datetime.timezone.utc,
        )
        service = _fake_self(TelemetryAggregatorScript)
        service.db.last_run_hour = None  # unequal to this hour's bucket

        TelemetryAggregatorScript.at_repeat(service)

        mock_defer.assert_called_once()
        self.assertTrue(hasattr(service.ndb, "last_repeat"))
        self.assertTrue(hasattr(service.ndb, "last_work"))


class TestNftSaturationHeartbeat(TestCase):

    @patch("typeclasses.scripts.nft_saturation_service.defer_to_db_thread")
    @patch("typeclasses.scripts.nft_saturation_service.datetime")
    def test_off_slot_minute_records_repeat_only(self, mock_datetime, _mock_defer):
        import datetime as real_datetime
        from typeclasses.scripts.nft_saturation_service import NFTSaturationScript

        mock_datetime.now.return_value = real_datetime.datetime(
            2026, 1, 1, 12, 30, tzinfo=real_datetime.timezone.utc,
        )
        service = _fake_self(NFTSaturationScript)

        NFTSaturationScript.at_repeat(service)

        self.assertTrue(hasattr(service.ndb, "last_repeat"))
        self.assertFalse(hasattr(service.ndb, "last_work"))

    @patch("typeclasses.scripts.nft_saturation_service.defer_to_db_thread")
    @patch("typeclasses.scripts.nft_saturation_service.datetime")
    def test_on_slot_minute_records_work_too(self, mock_datetime, mock_defer):
        import datetime as real_datetime
        from typeclasses.scripts.nft_saturation_service import NFTSaturationScript

        mock_datetime.now.return_value = real_datetime.datetime(
            2026, 1, 1, 12, 5, tzinfo=real_datetime.timezone.utc,
        )
        service = _fake_self(NFTSaturationScript)
        service.db.last_run_hour = None

        NFTSaturationScript.at_repeat(service)

        mock_defer.assert_called_once()
        self.assertTrue(hasattr(service.ndb, "last_repeat"))
        self.assertTrue(hasattr(service.ndb, "last_work"))


class TestUnifiedSpawnHeartbeat(TestCase):

    @patch("typeclasses.scripts.unified_spawn_service.defer_to_db_thread")
    @patch("typeclasses.scripts.unified_spawn_service.datetime")
    def test_off_slot_minute_records_repeat_only(self, mock_datetime, _mock_defer):
        import datetime as real_datetime
        from typeclasses.scripts.unified_spawn_service import UnifiedSpawnScript

        mock_datetime.now.return_value = real_datetime.datetime(
            2026, 1, 1, 12, 30, tzinfo=real_datetime.timezone.utc,
        )
        service = _fake_self(UnifiedSpawnScript)

        UnifiedSpawnScript.at_repeat(service)

        self.assertTrue(hasattr(service.ndb, "last_repeat"))
        self.assertFalse(hasattr(service.ndb, "last_work"))

    @patch("typeclasses.scripts.unified_spawn_service.defer_to_db_thread")
    @patch("typeclasses.scripts.unified_spawn_service.datetime")
    def test_on_slot_minute_without_service_records_repeat_only(self, mock_datetime, _mock_defer):
        """hasattr(self, '_service') is False until at_start() runs —
        the gate must stay closed even at the right minute."""
        import datetime as real_datetime
        from typeclasses.scripts.unified_spawn_service import UnifiedSpawnScript

        mock_datetime.now.return_value = real_datetime.datetime(
            2026, 1, 1, 12, 10, tzinfo=real_datetime.timezone.utc,
        )
        service = _fake_self(UnifiedSpawnScript)
        service.db.last_run_hour = None

        UnifiedSpawnScript.at_repeat(service)

        self.assertTrue(hasattr(service.ndb, "last_repeat"))
        self.assertFalse(hasattr(service.ndb, "last_work"))

    @patch("typeclasses.scripts.unified_spawn_service.defer_to_db_thread")
    @patch("typeclasses.scripts.unified_spawn_service.datetime")
    def test_on_slot_minute_with_service_records_work_too(self, mock_datetime, mock_defer):
        import datetime as real_datetime
        from typeclasses.scripts.unified_spawn_service import UnifiedSpawnScript

        mock_datetime.now.return_value = real_datetime.datetime(
            2026, 1, 1, 12, 10, tzinfo=real_datetime.timezone.utc,
        )
        service = _fake_self(UnifiedSpawnScript)
        service.db.last_run_hour = None
        service._service = MagicMock()

        UnifiedSpawnScript.at_repeat(service)

        mock_defer.assert_called_once()
        self.assertTrue(hasattr(service.ndb, "last_repeat"))
        self.assertTrue(hasattr(service.ndb, "last_work"))


class TestDurabilityDecayHeartbeat(TestCase):

    @patch("typeclasses.scripts.durability_decay_service.SESSION_HANDLER")
    @patch("typeclasses.scripts.durability_decay_service.get_game_day_number")
    def test_same_game_day_records_repeat_only(self, mock_day, _mock_handler):
        from typeclasses.scripts.durability_decay_service import DurabilityDecayService

        mock_day.return_value = 100
        service = _fake_self(DurabilityDecayService, last_game_day=100)

        DurabilityDecayService.at_repeat(service)

        self.assertTrue(hasattr(service.ndb, "last_repeat"))
        self.assertFalse(hasattr(service.ndb, "last_work"))

    @patch("typeclasses.scripts.durability_decay_service.delay")
    @patch("typeclasses.scripts.durability_decay_service.SESSION_HANDLER")
    @patch("typeclasses.scripts.durability_decay_service.get_game_day_number")
    def test_new_game_day_records_work_too(self, mock_day, mock_handler, _mock_delay):
        from typeclasses.scripts.durability_decay_service import DurabilityDecayService

        mock_day.return_value = 101
        mock_handler.get_sessions.return_value = []
        service = _fake_self(DurabilityDecayService, last_game_day=100)

        DurabilityDecayService.at_repeat(service)

        self.assertTrue(hasattr(service.ndb, "last_repeat"))
        self.assertTrue(hasattr(service.ndb, "last_work"))
        self.assertEqual(service.ndb.last_game_day, 101)
