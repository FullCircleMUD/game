"""
Tests for utils.skill_xp.award_skill_xp helper.

Covers the four guard branches:
- SKILL_XP_ENABLED toggle
- PvP-target block (target.is_pc)
- Non-positive amount short-circuit
- Normal grant delegates to caller.at_gain_experience_points

evennia test --settings settings tests.utils_tests.test_skill_xp
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from utils.skill_xp import award_skill_xp


class TestAwardSkillXP(TestCase):

    def setUp(self):
        self.caller = MagicMock()
        self.caller.at_gain_experience_points = MagicMock()

    def _enabled(self, value=True):
        return patch("utils.skill_xp.settings.SKILL_XP_ENABLED", value, create=True)

    def test_normal_grant_delegates_to_caller(self):
        with self._enabled(True):
            award_skill_xp(self.caller, 25)
        self.caller.at_gain_experience_points.assert_called_once_with(25)

    def test_disabled_setting_short_circuits(self):
        with self._enabled(False):
            award_skill_xp(self.caller, 25)
        self.caller.at_gain_experience_points.assert_not_called()

    def test_zero_amount_short_circuits(self):
        with self._enabled(True):
            award_skill_xp(self.caller, 0)
        self.caller.at_gain_experience_points.assert_not_called()

    def test_negative_amount_short_circuits(self):
        with self._enabled(True):
            award_skill_xp(self.caller, -10)
        self.caller.at_gain_experience_points.assert_not_called()

    def test_pc_target_blocks_pvp_grant(self):
        target = MagicMock()
        target.is_pc = True
        with self._enabled(True):
            award_skill_xp(self.caller, 25, target=target)
        self.caller.at_gain_experience_points.assert_not_called()

    def test_npc_target_does_not_block(self):
        target = MagicMock()
        target.is_pc = False
        with self._enabled(True):
            award_skill_xp(self.caller, 25, target=target)
        self.caller.at_gain_experience_points.assert_called_once_with(25)

    def test_target_without_is_pc_attr_does_not_block(self):
        # Bare object — no is_pc attribute → getattr default False → not blocked
        class _Target:
            pass
        with self._enabled(True):
            award_skill_xp(self.caller, 25, target=_Target())
        self.caller.at_gain_experience_points.assert_called_once_with(25)

    def test_no_target_does_not_block(self):
        with self._enabled(True):
            award_skill_xp(self.caller, 25, target=None)
        self.caller.at_gain_experience_points.assert_called_once_with(25)

    def test_disabled_takes_precedence_over_other_args(self):
        target = MagicMock()
        target.is_pc = False
        with self._enabled(False):
            award_skill_xp(self.caller, 100, target=target)
        self.caller.at_gain_experience_points.assert_not_called()

    def test_setting_missing_defaults_to_enabled(self):
        # If SKILL_XP_ENABLED isn't defined on settings at all, getattr default
        # is True → grant proceeds.
        with patch("utils.skill_xp.settings", new=MagicMock(spec=[])):
            award_skill_xp(self.caller, 25)
        self.caller.at_gain_experience_points.assert_called_once_with(25)
