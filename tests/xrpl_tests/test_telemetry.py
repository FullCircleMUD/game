"""
Tests for the economy telemetry system.

Covers:
- PlayerSession recording (start/end/stale cleanup)
- TelemetryService.take_snapshot() aggregation
- EconomySnapshot and ResourceSnapshot creation
- Velocity calculation from transfer logs
"""

from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase

from blockchain.xrpl.models import (
    CurrencyType,
    EconomySnapshot,
    FungibleGameState,
    FungibleTransferLog,
    PlayerSession,
    ResourceSnapshot,
)
from blockchain.xrpl.services.telemetry import TelemetryService


def _dt(year, month, day, hour, minute=0, second=0):
    """Helper to build a timezone-aware datetime."""
    return datetime(year, month, day, hour, minute, second, tzinfo=dt_timezone.utc)


# A fixed "now" for snapshot tests: 2026-03-19 14:30:00 UTC
# Bucket will be 14:00, hour_ago = 13:00
SNAP_NOW = _dt(2026, 3, 19, 14, 30, 0)
SNAP_BUCKET = _dt(2026, 3, 19, 14, 0, 0)


def _create_transfer_log(currency_code, from_wallet, to_wallet, amount,
                         transfer_type, timestamp):
    """Create a FungibleTransferLog with an explicit timestamp.

    auto_now_add prevents setting timestamp via create(), so we
    create the row then update the timestamp.
    """
    log = FungibleTransferLog.objects.create(
        currency_code=currency_code, from_wallet=from_wallet,
        to_wallet=to_wallet, amount=amount,
        transfer_type=transfer_type,
    )
    FungibleTransferLog.objects.filter(pk=log.pk).update(timestamp=timestamp)
    return log


class TestSessionTracking(TestCase):
    """Test PlayerSession start/end/stale cleanup."""

    databases = {"default", "xrpl"}

    def test_record_session_start(self):
        """record_session_start creates a PlayerSession row."""
        now = _dt(2026, 3, 19, 10, 0, 0)
        with patch("blockchain.xrpl.services.telemetry.timezone") as tz:
            tz.now.return_value = now
            TelemetryService.record_session_start(1, "TestChar")

        session = PlayerSession.objects.get()
        self.assertEqual(session.account_id, 1)
        self.assertEqual(session.character_key, "TestChar")
        self.assertEqual(session.started_at, now)
        self.assertIsNone(session.ended_at)

    def test_record_session_end(self):
        """record_session_end closes the most recent open session."""
        start = _dt(2026, 3, 19, 10, 0, 0)
        end = _dt(2026, 3, 19, 11, 0, 0)
        PlayerSession.objects.create(
            account_id=1, character_key="TestChar", started_at=start,
        )

        with patch("blockchain.xrpl.services.telemetry.timezone") as tz:
            tz.now.return_value = end
            TelemetryService.record_session_end(1, "TestChar")

        session = PlayerSession.objects.get()
        self.assertEqual(session.ended_at, end)

    def test_record_session_end_closes_most_recent(self):
        """If multiple open sessions exist, closes the most recent one."""
        PlayerSession.objects.create(
            account_id=1, character_key="TestChar",
            started_at=_dt(2026, 3, 19, 8, 0, 0),
        )
        PlayerSession.objects.create(
            account_id=1, character_key="TestChar",
            started_at=_dt(2026, 3, 19, 10, 0, 0),
        )

        with patch("blockchain.xrpl.services.telemetry.timezone") as tz:
            tz.now.return_value = _dt(2026, 3, 19, 11, 0, 0)
            TelemetryService.record_session_end(1, "TestChar")

        sessions = PlayerSession.objects.order_by("started_at")
        self.assertIsNone(sessions[0].ended_at)  # older stays open
        self.assertIsNotNone(sessions[1].ended_at)  # newer closed

    def test_close_stale_sessions(self):
        """close_stale_sessions closes all open sessions."""
        PlayerSession.objects.create(
            account_id=1, character_key="Char1",
            started_at=_dt(2026, 3, 19, 8, 0, 0),
        )
        PlayerSession.objects.create(
            account_id=2, character_key="Char2",
            started_at=_dt(2026, 3, 19, 9, 0, 0),
        )
        # Already closed session should not be re-closed
        PlayerSession.objects.create(
            account_id=3, character_key="Char3",
            started_at=_dt(2026, 3, 19, 7, 0, 0),
            ended_at=_dt(2026, 3, 19, 8, 0, 0),
        )

        with patch("blockchain.xrpl.services.telemetry.timezone") as tz:
            tz.now.return_value = _dt(2026, 3, 19, 12, 0, 0)
            TelemetryService.close_stale_sessions()

        self.assertEqual(
            PlayerSession.objects.filter(ended_at__isnull=True).count(), 0,
        )
        # The already-closed session should retain its original ended_at
        char3 = PlayerSession.objects.get(character_key="Char3")
        self.assertEqual(char3.ended_at, _dt(2026, 3, 19, 8, 0, 0))

    def test_session_end_no_open_session(self):
        """record_session_end is a no-op if no open session exists."""
        with patch("blockchain.xrpl.services.telemetry.timezone") as tz:
            tz.now.return_value = _dt(2026, 3, 19, 12, 0, 0)
            # Should not raise
            TelemetryService.record_session_end(999, "NoChar")

        self.assertEqual(PlayerSession.objects.count(), 0)


class TestTakeSnapshot(TestCase):
    """Test TelemetryService.take_snapshot() aggregation."""

    databases = {"default", "xrpl"}

    def setUp(self):
        """Seed minimum data: gold currency type."""
        self.gold_code = settings.XRPL_GOLD_CURRENCY_CODE
        CurrencyType.objects.get_or_create(
            currency_code=self.gold_code,
            defaults={"name": "Gold", "unit": "coin", "is_gold": True},
        )

    @patch("blockchain.xrpl.services.telemetry._fetch_amm_prices", return_value={})
    @patch("blockchain.xrpl.services.telemetry.timezone")
    def test_creates_economy_snapshot(self, mock_tz, _mock_prices):
        """take_snapshot creates an EconomySnapshot row."""
        mock_tz.now.return_value = SNAP_NOW
        TelemetryService.take_snapshot()

        snap = EconomySnapshot.objects.get()
        self.assertEqual(snap.hour, SNAP_BUCKET)

    @patch("blockchain.xrpl.services.telemetry._fetch_amm_prices", return_value={})
    @patch("blockchain.xrpl.services.telemetry.timezone")
    def test_counts_online_players(self, mock_tz, _mock_prices):
        """Players with open sessions are counted as online."""
        mock_tz.now.return_value = SNAP_NOW
        # 2 players online (open sessions)
        PlayerSession.objects.create(
            account_id=1, character_key="A",
            started_at=_dt(2026, 3, 19, 14, 0, 0),
        )
        PlayerSession.objects.create(
            account_id=2, character_key="B",
            started_at=_dt(2026, 3, 19, 14, 15, 0),
        )
        # 1 player offline (closed session)
        PlayerSession.objects.create(
            account_id=3, character_key="C",
            started_at=_dt(2026, 3, 19, 13, 0, 0),
            ended_at=_dt(2026, 3, 19, 13, 30, 0),
        )

        TelemetryService.take_snapshot()

        snap = EconomySnapshot.objects.get()
        self.assertEqual(snap.players_online, 2)

    @patch("blockchain.xrpl.services.telemetry._fetch_amm_prices", return_value={})
    @patch("blockchain.xrpl.services.telemetry.timezone")
    def test_unique_players_windows(self, mock_tz, _mock_prices):
        """Unique player counts work across 1h/24h/7d windows."""
        mock_tz.now.return_value = SNAP_NOW
        # Player 1: active in past hour
        PlayerSession.objects.create(
            account_id=1, character_key="A",
            started_at=_dt(2026, 3, 19, 14, 0, 0),
        )
        # Player 2: active in past 24h (not past hour)
        PlayerSession.objects.create(
            account_id=2, character_key="B",
            started_at=_dt(2026, 3, 18, 20, 0, 0),
            ended_at=_dt(2026, 3, 18, 21, 0, 0),
        )
        # Player 3: active in past 7d (not past 24h)
        PlayerSession.objects.create(
            account_id=3, character_key="C",
            started_at=_dt(2026, 3, 15, 10, 0, 0),
            ended_at=_dt(2026, 3, 15, 11, 0, 0),
        )

        TelemetryService.take_snapshot()

        snap = EconomySnapshot.objects.get()
        self.assertEqual(snap.unique_players_1h, 1)
        self.assertEqual(snap.unique_players_24h, 2)
        self.assertEqual(snap.unique_players_7d, 3)

    @patch("blockchain.xrpl.services.telemetry._fetch_amm_prices", return_value={})
    @patch("blockchain.xrpl.services.telemetry.timezone")
    def test_gold_circulation(self, mock_tz, _mock_prices):
        """Gold in CHARACTER + ACCOUNT is counted as circulation."""
        mock_tz.now.return_value = SNAP_NOW

        FungibleGameState.objects.create(
            currency_code=self.gold_code,
            wallet_address="rPlayer1",
            location=FungibleGameState.LOCATION_CHARACTER,
            character_key="A",
            balance=Decimal("500"),
        )
        FungibleGameState.objects.create(
            currency_code=self.gold_code,
            wallet_address="rPlayer1",
            location=FungibleGameState.LOCATION_ACCOUNT,
            balance=Decimal("300"),
        )

        TelemetryService.take_snapshot()

        snap = EconomySnapshot.objects.get()
        self.assertEqual(snap.gold_circulation, Decimal("800"))
        # Reserve includes seed data — just check it's > 0
        self.assertGreater(snap.gold_reserve, Decimal("0"))

    @patch("blockchain.xrpl.services.telemetry._fetch_amm_prices", return_value={})
    @patch("blockchain.xrpl.services.telemetry.timezone")
    def test_gold_sinks_from_sink_balance(self, mock_tz, _mock_prices):
        """Gold sinks come from SINK balance in FungibleGameState."""
        mock_tz.now.return_value = SNAP_NOW
        FungibleGameState.objects.create(
            currency_code=self.gold_code,
            wallet_address=settings.XRPL_VAULT_ADDRESS,
            location=FungibleGameState.LOCATION_SINK,
            balance=Decimal("150"),
        )

        TelemetryService.take_snapshot()

        snap = EconomySnapshot.objects.get()
        self.assertEqual(snap.gold_sinks_1h, Decimal("150"))

    @patch("blockchain.xrpl.services.telemetry._fetch_amm_prices", return_value={})
    @patch("blockchain.xrpl.services.telemetry.timezone")
    def test_amm_trade_count(self, mock_tz, _mock_prices):
        """AMM trades in the past hour are counted."""
        mock_tz.now.return_value = SNAP_NOW
        in_window = _dt(2026, 3, 19, 14, 10, 0)
        _create_transfer_log(
            self.gold_code, "rPlayer", "rVault", Decimal("10"),
            "amm_buy", in_window,
        )
        _create_transfer_log(
            self.gold_code, "rVault", "rPlayer", Decimal("5"),
            "amm_sell", in_window,
        )

        TelemetryService.take_snapshot()

        snap = EconomySnapshot.objects.get()
        self.assertEqual(snap.amm_trades_1h, 2)

    @patch("blockchain.xrpl.services.telemetry._fetch_amm_prices", return_value={})
    @patch("blockchain.xrpl.services.telemetry.timezone")
    def test_chain_activity(self, mock_tz, _mock_prices):
        """Import/export counts from transfer logs."""
        mock_tz.now.return_value = SNAP_NOW
        in_window = _dt(2026, 3, 19, 14, 5, 0)
        _create_transfer_log(
            self.gold_code, "ONCHAIN", "rPlayer", Decimal("100"),
            "deposit_from_chain", in_window,
        )
        _create_transfer_log(
            self.gold_code, "rPlayer", "ONCHAIN", Decimal("50"),
            "withdraw_to_chain", in_window,
        )
        _create_transfer_log(
            self.gold_code, "rPlayer2", "ONCHAIN", Decimal("25"),
            "withdraw_to_chain", in_window,
        )

        TelemetryService.take_snapshot()

        snap = EconomySnapshot.objects.get()
        self.assertEqual(snap.imports_1h, 1)
        self.assertEqual(snap.exports_1h, 2)


class TestResourceSnapshot(TestCase):
    """Test per-resource snapshot creation."""

    databases = {"default", "xrpl"}

    def setUp(self):
        """Seed currencies."""
        self.gold_code = settings.XRPL_GOLD_CURRENCY_CODE
        CurrencyType.objects.get_or_create(
            currency_code=self.gold_code,
            defaults={"name": "Gold", "unit": "coin", "is_gold": True},
        )
        CurrencyType.objects.get_or_create(
            currency_code="FCMWheat",
            defaults={"name": "Wheat", "unit": "bushel", "resource_id": 1},
        )
        self.vault = settings.XRPL_VAULT_ADDRESS

    @patch("blockchain.xrpl.services.telemetry._fetch_amm_prices", return_value={})
    @patch("blockchain.xrpl.services.telemetry.timezone")
    def test_creates_resource_snapshots(self, mock_tz, _mock_prices):
        """take_snapshot creates ResourceSnapshot rows for each currency."""
        mock_tz.now.return_value = SNAP_NOW
        TelemetryService.take_snapshot()

        # One per CurrencyType (seed data has 37: gold + 36 resources)
        ct_count = CurrencyType.objects.count()
        self.assertEqual(ResourceSnapshot.objects.count(), ct_count)
        # Spot-check our test currencies exist
        self.assertTrue(ResourceSnapshot.objects.filter(currency_code="FCMWheat").exists())
        self.assertTrue(ResourceSnapshot.objects.filter(currency_code=self.gold_code).exists())

    @patch("blockchain.xrpl.services.telemetry._fetch_amm_prices", return_value={})
    @patch("blockchain.xrpl.services.telemetry.timezone")
    def test_resource_circulation(self, mock_tz, _mock_prices):
        """Resource snapshot captures circulation by location."""
        mock_tz.now.return_value = SNAP_NOW

        FungibleGameState.objects.create(
            currency_code="FCMWheat", wallet_address="rPlayer1",
            location=FungibleGameState.LOCATION_CHARACTER,
            character_key="A", balance=Decimal("50"),
        )
        FungibleGameState.objects.create(
            currency_code="FCMWheat", wallet_address="rPlayer1",
            location=FungibleGameState.LOCATION_ACCOUNT,
            balance=Decimal("30"),
        )

        TelemetryService.take_snapshot()

        snap = ResourceSnapshot.objects.get(currency_code="FCMWheat")
        self.assertEqual(snap.in_character, Decimal("50"))
        self.assertEqual(snap.in_account, Decimal("30"))
        # Reserve includes seed data — just check it's present
        self.assertGreaterEqual(snap.in_reserve, Decimal("0"))
        self.assertEqual(snap.in_spawned, Decimal("0"))

    @patch("blockchain.xrpl.services.telemetry._fetch_amm_prices", return_value={})
    @patch("blockchain.xrpl.services.telemetry.timezone")
    def test_resource_velocity(self, mock_tz, _mock_prices):
        """Resource velocity is computed from transfer logs."""
        mock_tz.now.return_value = SNAP_NOW
        in_window = _dt(2026, 3, 19, 14, 10, 0)

        # Produced: craft_output
        _create_transfer_log(
            "FCMWheat", self.vault, "rPlayer", Decimal("20"),
            "craft_output", in_window,
        )
        # Consumed: craft_input
        _create_transfer_log(
            "FCMWheat", "rPlayer", self.vault, Decimal("10"),
            "craft_input", in_window,
        )
        # Traded: amm_buy
        _create_transfer_log(
            "FCMWheat", self.vault, "rPlayer", Decimal("5"),
            "amm_buy", in_window,
        )
        # Exported
        _create_transfer_log(
            "FCMWheat", "rPlayer", "ONCHAIN", Decimal("3"),
            "withdraw_to_chain", in_window,
        )

        TelemetryService.take_snapshot()

        snap = ResourceSnapshot.objects.get(currency_code="FCMWheat")
        self.assertEqual(snap.produced_1h, Decimal("20"))
        self.assertEqual(snap.consumed_1h, Decimal("10"))
        self.assertEqual(snap.traded_1h, Decimal("5"))
        self.assertEqual(snap.exported_1h, Decimal("3"))
        self.assertEqual(snap.imported_1h, Decimal("0"))

    @patch("blockchain.xrpl.services.telemetry.timezone")
    def test_amm_prices_populated(self, mock_tz):
        """AMM prices are populated when available."""
        mock_tz.now.return_value = SNAP_NOW
        mock_prices = {
            "FCMWheat": {"buy_1": Decimal("2"), "sell_1": Decimal("1")},
        }

        with patch(
            "blockchain.xrpl.services.telemetry._fetch_amm_prices",
            return_value=mock_prices,
        ):
            TelemetryService.take_snapshot()

        snap = ResourceSnapshot.objects.get(currency_code="FCMWheat")
        self.assertEqual(snap.amm_buy_price, Decimal("2"))
        self.assertEqual(snap.amm_sell_price, Decimal("1"))

    @patch("blockchain.xrpl.services.telemetry._fetch_amm_prices", return_value={})
    @patch("blockchain.xrpl.services.telemetry.timezone")
    def test_amm_prices_null_when_unavailable(self, mock_tz, _mock_prices):
        """AMM prices are null when pool doesn't exist."""
        mock_tz.now.return_value = SNAP_NOW
        TelemetryService.take_snapshot()

        snap = ResourceSnapshot.objects.get(currency_code="FCMWheat")
        self.assertIsNone(snap.amm_buy_price)
        self.assertIsNone(snap.amm_sell_price)

    @patch("blockchain.xrpl.services.telemetry._fetch_amm_prices", return_value={})
    @patch("blockchain.xrpl.services.telemetry.timezone")
    def test_snapshot_idempotent(self, mock_tz, _mock_prices):
        """Running take_snapshot twice in the same hour updates, not duplicates."""
        mock_tz.now.return_value = SNAP_NOW
        TelemetryService.take_snapshot()
        TelemetryService.take_snapshot()

        self.assertEqual(EconomySnapshot.objects.count(), 1)
        self.assertEqual(
            ResourceSnapshot.objects.filter(currency_code="FCMWheat").count(), 1,
        )
