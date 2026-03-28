"""
Tests for TacticalDodgeMixin — random dodge during combat ticks.

evennia test --settings settings tests.typeclass_tests.test_tactical_dodge_mixin
"""

from unittest.mock import patch, MagicMock

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.mixins.mob_behaviours.tactical_dodge_mixin import TacticalDodgeMixin


class DodgeTestMob(TacticalDodgeMixin, AggressiveMob):
    """Test-only mob with tactical dodge."""
    dodge_chance = AttributeProperty(0.25)


class TestTacticalDodgeMixin(EvenniaTest):
    """Test at_combat_tick dodge behavior."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.mob = create.create_object(
            DodgeTestMob, key="a dodger", location=self.room1,
        )
        self.mob.is_alive = True
        self.mob.hp = 30

    @patch("random.random", return_value=0.1)
    def test_dodge_fires_when_below_chance(self, _mock_random):
        """Should execute dodge command when roll < dodge_chance."""
        self.mob.execute_cmd = MagicMock()
        self.mob.at_combat_tick(handler=MagicMock())
        self.mob.execute_cmd.assert_called_once_with("dodge")

    @patch("random.random", return_value=0.9)
    def test_no_dodge_above_chance(self, _mock_random):
        """Should not dodge when roll > dodge_chance."""
        self.mob.execute_cmd = MagicMock()
        self.mob.at_combat_tick(handler=MagicMock())
        self.mob.execute_cmd.assert_not_called()
