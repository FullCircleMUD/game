"""
Tests for the case command — scout a target's inventory before pickpocketing.

evennia test --settings settings tests.command_tests.test_cmd_case
"""

import time
from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.class_skill_cmdsets.class_skill_cmds.cmd_case import CmdCase
from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills

_ROOM = "typeclasses.terrain.rooms.room_base.RoomBase"
_CHAR = "typeclasses.actors.character.FCMCharacter"


def _set_subterfuge(char, mastery=MasteryLevel.BASIC):
    """Give a character subterfuge mastery."""
    if not char.db.class_skill_mastery_levels:
        char.db.class_skill_mastery_levels = {}
    char.db.class_skill_mastery_levels[skills.SUBTERFUGE.value] = {"mastery": mastery.value, "classes": ["Thief"]}


# ── Gate Checks ───────────────────────────────────────────────────

class TestCaseGates(EvenniaCommandTest):
    """Test case command gate checks."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_subterfuge(self.char1, MasteryLevel.BASIC)

    def test_no_args(self):
        self.call(CmdCase(), "", "Case who?")

    def test_self_target(self):
        self.call(CmdCase(), "Char", "You can't case yourself.")

    def test_unskilled_blocked(self):
        _set_subterfuge(self.char1, MasteryLevel.UNSKILLED)
        self.call(CmdCase(), "Char2", "You have no idea how to case")

    def test_in_combat_blocked(self):
        from combat.combat_handler import CombatHandler
        self.char1.scripts.add(CombatHandler, autostart=False)
        self.call(CmdCase(), "Char2", "You can't case someone while in combat!")

    def test_hidden_target_blocked(self):
        self.char2.add_condition(Condition.HIDDEN)
        self.call(CmdCase(), "Char2", "You can't see them well enough")


# ── Result Display ────────────────────────────────────────────────

class TestCaseResults(EvenniaCommandTest):
    """Test case command visibility rolls and output."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_subterfuge(self.char1, MasteryLevel.BASIC)
        self.char2.db.gold = 75
        self.char2.db.resources = {}

    @patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_case.random.randint")
    def test_gold_visible_vague_display(self, mock_roll):
        """When gold roll succeeds, show vague description not exact amount."""
        mock_roll.return_value = 1  # always succeeds (1 <= 50)
        result = self.call(CmdCase(), "Char2")
        self.assertIn("a decent purse of gold", result)
        self.assertNotIn("75", result)

    @patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_case.random.randint")
    def test_gold_hidden_high_roll(self, mock_roll):
        """When gold roll fails, gold not shown."""
        mock_roll.return_value = 100  # always fails (100 > 50)
        result = self.call(CmdCase(), "Char2")
        self.assertNotIn("gold", result.lower())
        self.assertNotIn("coins", result.lower())
        self.assertIn("can't make out", result)

    @patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_case.random.randint")
    def test_item_visible(self, mock_roll):
        """Items that pass the roll should be shown by name."""
        mock_roll.return_value = 1  # always succeeds
        item = create.create_object(
            "typeclasses.world_objects.base_world_item.WorldItem",
            key="steel sword",
            location=self.char2,
        )
        result = self.call(CmdCase(), "Char2")
        self.assertIn("steel sword", result)

    @patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_case.random.randint")
    def test_item_hidden(self, mock_roll):
        """Items that fail the roll should not be shown."""
        mock_roll.return_value = 100  # always fails
        item = create.create_object(
            "typeclasses.world_objects.base_world_item.WorldItem",
            key="steel sword",
            location=self.char2,
        )
        result = self.call(CmdCase(), "Char2")
        self.assertNotIn("steel sword", result)

    @patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_case.random.randint")
    def test_empty_inventory(self, mock_roll):
        """Target with nothing should show 'can't make out'."""
        self.char2.db.gold = 0
        mock_roll.return_value = 1
        result = self.call(CmdCase(), "Char2")
        self.assertIn("can't make out", result)

    @patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_case.random.randint")
    def test_resource_vague_display(self, mock_roll):
        """Resources should show type but not quantity."""
        mock_roll.return_value = 1
        self.char2.db.resources = {1: 50}  # 50 wheat
        result = self.call(CmdCase(), "Char2")
        self.assertIn("some", result.lower())
        self.assertNotIn("50", result)


# ── Caching ───────────────────────────────────────────────────────

class TestCaseCache(EvenniaCommandTest):
    """Test case result caching."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_subterfuge(self.char1, MasteryLevel.BASIC)
        self.char2.db.gold = 100
        self.char2.db.resources = {}

    @patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_case.random.randint")
    def test_cached_results_same(self, mock_roll):
        """Second case within 5 minutes should return same results."""
        mock_roll.return_value = 1  # everything visible
        self.call(CmdCase(), "Char2")

        # Change the roll — but cache should still show old results
        mock_roll.return_value = 100
        result = self.call(CmdCase(), "Char2")
        # Gold should still show because cached
        self.assertIn("gold", result.lower())

    @patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_case.random.randint")
    @patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_case.time.time")
    def test_expired_cache_rerolls(self, mock_time, mock_roll):
        """After 5 minutes, fresh rolls should be made."""
        now = 1000.0

        # First case — everything visible
        mock_time.return_value = now
        mock_roll.return_value = 1
        self.call(CmdCase(), "Char2")

        # 6 minutes later — cache expired, new roll fails
        mock_time.return_value = now + 360
        mock_roll.return_value = 100
        result = self.call(CmdCase(), "Char2")
        self.assertIn("can't make out", result)


# ── HIDDEN Interaction ────────────────────────────────────────────

class TestCaseHidden(EvenniaCommandTest):
    """Test that casing does not break HIDDEN."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_subterfuge(self.char1, MasteryLevel.BASIC)
        self.char2.db.gold = 50
        self.char2.db.resources = {}

    @patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_case.random.randint")
    def test_case_does_not_break_hidden(self, mock_roll):
        """Casing while HIDDEN should NOT break stealth."""
        mock_roll.return_value = 1
        self.char1.add_condition(Condition.HIDDEN)
        self.call(CmdCase(), "Char2")
        self.assertTrue(self.char1.has_condition(Condition.HIDDEN))
