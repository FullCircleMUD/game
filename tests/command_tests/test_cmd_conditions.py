"""
Tests for CmdConditions — verifies the command lists active named effects
and condition flags, with durations and stack counts.
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_conditions import CmdConditions, _duration
from enums.condition import Condition


class TestCmdConditions(EvenniaCommandTest):
    """Test the conditions command output."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_nothing_active(self):
        """A clean character is told nothing is affecting them."""
        self.call(CmdConditions(), "", "Nothing is affecting you.")

    def test_condition_listed(self):
        """A raw condition flag appears under Conditions."""
        self.char1.add_condition(Condition.BLINDED)
        self.call(CmdConditions(), "", "Conditions:\n  Blinded")

    def test_stacked_condition_shows_count(self):
        """Two sources holding the same flag show a count."""
        self.char1.add_condition(Condition.DARKVISION)
        self.char1.add_condition(Condition.DARKVISION)
        self.call(CmdConditions(), "", "Conditions:\n  Darkvision (x2)")

    def test_combat_round_effect_shows_rounds(self):
        """A rounds-based effect reports how many rounds are left."""
        self.char1.apply_stunned(2)
        self.call(CmdConditions(), "", "Effects:\n  Stunned — 2 rounds")

    def test_single_round_is_singular(self):
        """One round reads 'round', not 'rounds'."""
        self.char1.apply_stunned(1)
        self.call(CmdConditions(), "", "Effects:\n  Stunned — 1 round")


class _FakeCaller:
    """Stub with a fixed remaining time, so duration text is deterministic."""

    def __init__(self, remaining):
        self.remaining = remaining

    def get_effect_remaining_seconds(self, key):
        return self.remaining


class TestDurationText(EvenniaCommandTest):
    """Test the seconds/minutes split, away from live timer drift."""

    def create_script(self):
        pass

    def test_long_effect_reads_in_minutes(self):
        """A minute or more reports whole minutes, rounded down."""
        record = {"duration_type": "seconds"}
        self.assertEqual(
            _duration(_FakeCaller(330), "invisible", record), "5 minutes"
        )

    def test_one_minute_is_singular(self):
        """Exactly a minute reads 'minute', not 'minutes'."""
        record = {"duration_type": "seconds"}
        self.assertEqual(
            _duration(_FakeCaller(60), "invisible", record), "1 minute"
        )

    def test_short_effect_reads_in_seconds(self):
        """Under a minute still reports seconds."""
        record = {"duration_type": "seconds"}
        self.assertEqual(
            _duration(_FakeCaller(30), "invisible", record), "30 seconds"
        )
