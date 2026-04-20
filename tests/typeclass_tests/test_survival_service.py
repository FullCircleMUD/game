"""
Tests for the SurvivalService script — periodic hunger decrement.

Verifies hunger level decrement, free pass tick, starving floor,
and skip logic for characters without valid hunger levels.

evennia test --settings settings tests.typeclass_tests.test_survival_service
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from enums.hunger_level import HungerLevel
from enums.thirst_level import ThirstLevel
from typeclasses.scripts.survival_service import SurvivalService


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class SurvivalServiceTestBase(EvenniaCommandTest):
    """Base class providing a character for survival service tests."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Create an unbound instance — don't call at_script_creation
        # (it tries to save to DB). We only test at_repeat() logic.
        self.service = SurvivalService.__new__(SurvivalService)

    def _run_tick(self, characters):
        """Run one survival tick with the given character list.
        Builds mock sessions that return each character as a puppet."""
        mock_sessions = []
        for char in characters:
            s = MagicMock()
            s.get_puppet.return_value = char
            mock_sessions.append(s)
        with patch("typeclasses.scripts.survival_service.SESSION_HANDLER") as mock_sh:
            mock_sh.get_sessions.return_value = mock_sessions
            self.service.at_repeat()


class TestHungerDecrement(SurvivalServiceTestBase):
    """Test hunger level decrement on at_repeat()."""

    def test_satisfied_to_nourished(self):
        """SATISFIED should decrement to NOURISHED (the new intermediate stage)."""
        self.char1.hunger_level = HungerLevel.SATISFIED
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hunger_level, HungerLevel.NOURISHED)

    def test_content_to_peckish(self):
        """CONTENT should decrement to PECKISH (the last no-penalty stage)."""
        self.char1.hunger_level = HungerLevel.CONTENT
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hunger_level, HungerLevel.PECKISH)

    def test_peckish_to_hungry(self):
        """PECKISH should decrement to HUNGRY (regen halts here)."""
        self.char1.hunger_level = HungerLevel.PECKISH
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hunger_level, HungerLevel.HUNGRY)

    def test_hungry_to_famished(self):
        """HUNGRY should decrement to FAMISHED."""
        self.char1.hunger_level = HungerLevel.HUNGRY
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hunger_level, HungerLevel.FAMISHED)

    def test_famished_to_starving(self):
        """FAMISHED should decrement to STARVING."""
        self.char1.hunger_level = HungerLevel.FAMISHED
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hunger_level, HungerLevel.STARVING)

    def test_full_progression(self):
        """Full decrement chain: FULL → SATISFIED → ... → STARVING (7 steps)."""
        self.char1.hunger_level = HungerLevel.FULL
        self.char1.hunger_free_pass_tick = False

        expected = [
            HungerLevel.SATISFIED,
            HungerLevel.NOURISHED,
            HungerLevel.CONTENT,
            HungerLevel.PECKISH,
            HungerLevel.HUNGRY,
            HungerLevel.FAMISHED,
            HungerLevel.STARVING,
        ]
        for expected_level in expected:
            self._run_tick([self.char1])
            self.assertEqual(self.char1.hunger_level, expected_level)


class TestHungerStarvingFloor(SurvivalServiceTestBase):
    """Test that STARVING characters stay at STARVING."""

    def test_starving_stays_starving(self):
        """STARVING should not decrement further."""
        self.char1.hunger_level = HungerLevel.STARVING
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hunger_level, HungerLevel.STARVING)

    def test_starving_after_multiple_ticks(self):
        """Multiple ticks at STARVING should not crash or change level."""
        self.char1.hunger_level = HungerLevel.STARVING
        for _ in range(3):
            self._run_tick([self.char1])
        self.assertEqual(self.char1.hunger_level, HungerLevel.STARVING)


class TestHungerFreePass(SurvivalServiceTestBase):
    """Test the free pass tick when character is FULL."""

    def test_full_with_free_pass_stays_full(self):
        """FULL with free_pass_tick=True should stay FULL (pass consumed)."""
        self.char1.hunger_level = HungerLevel.FULL
        self.char1.hunger_free_pass_tick = True
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hunger_level, HungerLevel.FULL)
        self.assertFalse(self.char1.hunger_free_pass_tick)

    def test_full_without_free_pass_decrements(self):
        """FULL without free_pass_tick should decrement to SATISFIED."""
        self.char1.hunger_level = HungerLevel.FULL
        self.char1.hunger_free_pass_tick = False
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hunger_level, HungerLevel.SATISFIED)

    def test_free_pass_only_works_once(self):
        """After free pass consumed, next tick should decrement."""
        self.char1.hunger_level = HungerLevel.FULL
        self.char1.hunger_free_pass_tick = True
        # First tick: consumes pass, stays FULL
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hunger_level, HungerLevel.FULL)
        # Second tick: no pass, decrements
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hunger_level, HungerLevel.SATISFIED)


# (TestSurvivalServiceTicksBoth — see end of file for the canonical version)


class TestHungerSkipLogic(SurvivalServiceTestBase):
    """Test that invalid characters are skipped."""

    def test_skip_non_hunger_level(self):
        """Characters with non-HungerLevel hunger_level should be skipped."""
        self.char1.hunger_level = "not a hunger level"
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hunger_level, "not a hunger level")

    def test_skip_no_hunger_attr(self):
        """Characters without hunger_level attribute should be skipped."""
        obj = MagicMock(spec=["msg", "has_account", "account"])
        obj.has_account = True
        obj.account = MagicMock(is_superuser=False)
        self._run_tick([obj])
        # No crash = success

    def test_skip_unpuppeted_character(self):
        """Unpuppeted characters (quit but account logged in) should be skipped."""
        self.char1.hunger_level = HungerLevel.SATISFIED
        # Session exists but get_puppet() returns None (no puppeted character)
        mock_session = MagicMock()
        mock_session.get_puppet.return_value = None
        with patch("typeclasses.scripts.survival_service.SESSION_HANDLER") as mock_sh:
            mock_sh.get_sessions.return_value = [mock_session]
            self.service.at_repeat()
        self.assertEqual(self.char1.hunger_level, HungerLevel.SATISFIED)


# ── Thirst Tick Tests ───────────────────────────────────────────────────

class TestThirstDecrement(SurvivalServiceTestBase):
    """Verify the thirst meter decrements one stage per tick."""

    def test_refreshed_to_hydrated(self):
        self.char1.thirst_level = ThirstLevel.REFRESHED
        self.char1.thirst_free_pass_tick = False
        self._run_tick([self.char1])
        self.assertEqual(self.char1.thirst_level, ThirstLevel.HYDRATED)

    def test_aware_to_dry(self):
        self.char1.thirst_level = ThirstLevel.AWARE
        self._run_tick([self.char1])
        self.assertEqual(self.char1.thirst_level, ThirstLevel.DRY)

    def test_full_progression_to_critical(self):
        self.char1.thirst_level = ThirstLevel.REFRESHED
        self.char1.thirst_free_pass_tick = False
        # 11 decrements take us from REFRESHED(12) to CRITICAL(1)
        for _ in range(11):
            self._run_tick([self.char1])
        self.assertEqual(self.char1.thirst_level, ThirstLevel.CRITICAL)


class TestThirstCriticalFloor(SurvivalServiceTestBase):
    """CRITICAL is the floor — death lands via RegenerationService, not here."""

    def test_critical_stays_critical(self):
        self.char1.thirst_level = ThirstLevel.CRITICAL
        self._run_tick([self.char1])
        self.assertEqual(self.char1.thirst_level, ThirstLevel.CRITICAL)

    def test_critical_after_multiple_ticks(self):
        self.char1.thirst_level = ThirstLevel.CRITICAL
        for _ in range(3):
            self._run_tick([self.char1])
        self.assertEqual(self.char1.thirst_level, ThirstLevel.CRITICAL)


class TestThirstFreePass(SurvivalServiceTestBase):
    """Free-pass-on-REFRESHED prevents the immediate-decrement edge case."""

    def test_refreshed_with_free_pass_stays_refreshed(self):
        self.char1.thirst_level = ThirstLevel.REFRESHED
        self.char1.thirst_free_pass_tick = True
        self._run_tick([self.char1])
        self.assertEqual(self.char1.thirst_level, ThirstLevel.REFRESHED)
        self.assertFalse(self.char1.thirst_free_pass_tick)

    def test_refreshed_without_free_pass_decrements(self):
        self.char1.thirst_level = ThirstLevel.REFRESHED
        self.char1.thirst_free_pass_tick = False
        self._run_tick([self.char1])
        self.assertEqual(self.char1.thirst_level, ThirstLevel.HYDRATED)

    def test_free_pass_only_works_once(self):
        self.char1.thirst_level = ThirstLevel.REFRESHED
        self.char1.thirst_free_pass_tick = True
        self._run_tick([self.char1])
        self.assertEqual(self.char1.thirst_level, ThirstLevel.REFRESHED)
        self._run_tick([self.char1])
        self.assertEqual(self.char1.thirst_level, ThirstLevel.HYDRATED)


class TestSurvivalServiceTicksBoth(SurvivalServiceTestBase):
    """A single survival tick should decrement BOTH meters in one pass."""

    def test_one_tick_decrements_both_meters(self):
        self.char1.hunger_level = HungerLevel.SATISFIED
        self.char1.thirst_level = ThirstLevel.HYDRATED
        self.char1.hunger_free_pass_tick = False
        self.char1.thirst_free_pass_tick = False

        self._run_tick([self.char1])

        self.assertEqual(self.char1.hunger_level, HungerLevel.NOURISHED)
        self.assertEqual(self.char1.thirst_level, ThirstLevel.QUENCHED)
